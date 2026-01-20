from telegram import Update, InlineKeyboardButton
from telegram.ext import CallbackContext
import logging

from user_data import UserDataManager
from weather_api import get_weather, get_forecast, get_daily_forecast, get_extended_data
from keyboards import create_weather_keyboard, create_forecast_keyboard
from utils import normalize_city_name

logger = logging.getLogger(__name__)

async def get_weather_for_region(update: Update, context: CallbackContext):
    """Получить погоду для региона пользователя"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    region = UserDataManager.get_user_region(context, user_id)

    if region == 'Moscow':
        # Регион не установлен
        await handle_region_not_set(update, context)
        return
    
    # Получаем настройки пользователя
    features = UserDataManager.get_user_features(context, user_id)
    timezone = UserDataManager.get_user_timezone(context, user_id)
    pressure_unit = UserDataManager.get_user_pressure_unit(context, user_id)
    
    # Получаем погоду для региона
    weather_info, weather_text = get_weather(
        region,
        lang,
        features,
        timezone,
        pressure_unit=pressure_unit
    )
    
    if weather_info:
        city_name = weather_info['city']
        country = weather_info.get('country', '')
        favs_dict = UserDataManager.get_user_favorites_dict(context, user_id)
        
        from user_data import make_favorite_key
        fav_key = make_favorite_key(city_name, country)
        city_in_favorites = fav_key in favs_dict

        keyboard = create_weather_keyboard(
            city_name,
            city_in_favorites,
            lang,
            show_forecast=True,
            is_current_region=True,
            lat=weather_info.get('lat'),
            lon=weather_info.get('lon'),
            country=country
        )

        await update.message.reply_text(weather_text, reply_markup=keyboard)
    else:
        if lang == 'rus':
            await update.message.reply_text(f"❌ Не удалось получить погоду для региона {region}")
        else:
            await update.message.reply_text(f"❌ Failed to get weather for region {region}")

async def handle_region_not_set(update: Update, context: CallbackContext):
    """Обработка случая, когда регион не установлен"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    context.user_data['setting_region'] = True

    if lang == 'rus':
        text = "📍 Регион не установлен\n\n"
        text += "Для начала установите свой регион, чтобы получать актуальную погоду.\n\n"
        text += "Выберите способ:"
    else:
        text = "📍 Region not set\n\n"
        text += "First set your region to get actual weather.\n\n"
        text += "Choose method:"
    
    from keyboards import create_region_setup_keyboard
    keyboard = create_region_setup_keyboard(lang)
    
    await update.message.reply_text(text, reply_markup=keyboard)

async def week_forecast(update: Update, context: CallbackContext, city_name: str = None):
    """Показать недельный прогноз"""
    from handlers.callbacks import button_callback
    from telegram import CallbackQuery
    
    # Создаем фиктивный callback query для использования существующей логики
    if hasattr(update, 'callback_query'):
        query = update.callback_query
    else:
        # Если это не callback, вызываем как будто это был callback
        class FakeCallback:
            def __init__(self, user_id, message, data):
                self.from_user = type('obj', (object,), {'id': user_id})()
                self.message = message
                self.data = data
            
            async def answer(self):
                pass
        
        fake_update = Update(
            update.update_id,
            callback_query=FakeCallback(
                update.effective_user.id,
                update.message,
                f"week_forecast:{city_name}"
            )
        )
        await button_callback(fake_update, context)
        return
    
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    if not city_name:
        region = UserDataManager.get_user_region(context, user_id)
        city_name = region

    if lang == 'rus':
        text = f"⏳ Загружаю прогноз погоды для города {city_name}..."
    else:
        text = f"⏳ Loading weather forecast for {city_name}..."

    await query.edit_message_text(text)

    city_name_api, forecast_list, error = get_forecast(city_name, lang)

    if error:
        await query.message.reply_text(error)
        return

    if not forecast_list:
        error_msg = "❌ Не удалось получить прогноз." if lang == 'rus' else "❌ Failed to get forecast."
        await query.message.reply_text(error_msg)
        return

    context.user_data['forecast_data'] = {
        'city': city_name_api,
        'forecast_list': forecast_list
    }

    if lang == 'rus':
        text = f"📅 Прогноз погоды в городе {city_name_api}\n\nВыберите день:"
    else:
        text = f"📅 Weather forecast in {city_name_api}\n\nChoose day:"

    keyboard = create_forecast_keyboard(lang, city_name_api)
    await query.message.reply_text(text, reply_markup=keyboard)

async def week_forecast_by_coordinates(update: Update, context: CallbackContext, lat: float, lon: float,
                                       city_name: str):
    """Показать недельный прогноз по координатам"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    if lang == 'rus':
        text = f"⏳ Загружаю прогноз погоды для координат {lat:.4f}, {lon:.4f}..."
    else:
        text = f"⏳ Loading weather forecast for coordinates {lat:.4f}, {lon:.4f}..."

    await query.edit_message_text(text)

    url = 'https://api.openweathermap.org/data/2.5/forecast'
    from config import WEATHER_TOKEN
    params = {
        'lat': lat,
        'lon': lon,
        'appid': WEATHER_TOKEN,
        'units': 'metric',
        'lang': 'ru' if lang == 'rus' else 'en',
        'cnt': 40
    }

    try:
        import requests
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            error_msg = "❌ Не удалось получить прогноз." if lang == 'rus' else "❌ Failed to get forecast."
            await query.message.reply_text(error_msg)
            return

        data = response.json()
        city_name_api = data['city']['name']
        forecast_list = data['list']

        context.user_data['forecast_data'] = {
            'city': city_name_api,
            'forecast_list': forecast_list
        }

        if lang == 'rus':
            text = f"📅 Прогноз погоды в городе {city_name_api}\n\nВыберите день:"
        else:
            text = f"📅 Weather forecast in {city_name_api}\n\nChoose day:"

        keyboard = create_forecast_keyboard(lang, city_name_api)
        await query.message.reply_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка week_forecast_by_coordinates: {e}")
        error_msg = "❌ Ошибка получения прогноза." if lang == 'rus' else "❌ Error getting forecast."
        await query.message.reply_text(error_msg)

async def show_day_forecast(update: Update, context: CallbackContext, city_name: str, day_offset: int):
    """Показать прогноз на конкретный день"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    forecast_data = context.user_data.get('forecast_data')

    if not forecast_data:
        if lang == 'rus':
            await query.answer("❌ Данные прогноза не найдены")
        else:
            await query.answer("❌ Forecast data not found")
        return

    forecast_list = forecast_data['forecast_list']
    day_forecast = get_daily_forecast(forecast_list, day_offset)

    if not day_forecast:
        if lang == 'rus':
            await query.answer("❌ Нет данных для этого дня")
        else:
            await query.answer("❌ No data for this day")
        return

    if lang == 'rus':
        text = f"📅 Прогноз на {day_forecast['date'].strftime('%d.%m.%Y')}\n\n"
        text += f"🌡 Температура: {day_forecast['temp_day']:.1f}°C\n"
        text += f"📊 Мин/Макс: {day_forecast['temp_min']:.1f}°C / {day_forecast['temp_max']:.1f}°C\n"
        text += f"🤔 Ощущается как: {day_forecast['feels_like']:.1f}°C\n"
        text += f"📖 Описание: {day_forecast['description']}\n"
        text += f"💧 Влажность: {day_forecast['humidity']}%\n"
        text += f"🔽 Давление: {day_forecast['pressure']} гПа\n"
        text += f"💨 Скорость ветра: {day_forecast['wind_speed']} м/с"
    else:
        text = f"📅 Forecast for {day_forecast['date'].strftime('%d.%m.%Y')}\n\n"
        text += f"🌡 Temperature: {day_forecast['temp_day']:.1f}°C\n"
        text += f"📊 Min/Max: {day_forecast['temp_min']:.1f}°C / {day_forecast['temp_max']:.1f}°C\n"
        text += f"🤔 Feels like: {day_forecast['feels_like']:.1f}°C\n"
        text += f"📖 Description: {day_forecast['description']}\n"
        text += f"💧 Humidity: {day_forecast['humidity']}%\n"
        text += f"🔽 Pressure: {day_forecast['pressure']} hPa\n"
        text += f"💨 Wind speed: {day_forecast['wind_speed']} m/s"

    keyboard = [[InlineKeyboardButton("◀️ К выбору дней" if lang == 'rus' else "◀️ Back to days",
                                      callback_data=f"week_forecast:{city_name}")]]
    from telegram import InlineKeyboardMarkup
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup)