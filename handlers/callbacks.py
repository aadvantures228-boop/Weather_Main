import logging
import urllib.parse
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
from telegram import Update

from user_data import UserDataManager
from keyboards import (
    create_language_keyboard, create_timezone_keyboard, create_region_setup_keyboard,
    create_pressure_settings_keyboard, create_extra_features_keyboard,
    create_weather_keyboard, create_location_keyboard, create_notification_time_keyboard,
    get_main_menu_keyboard
)
from weather_api import get_weather, get_weather_by_coordinates, get_extended_data
from handlers.favorites import favorites, handle_favorite_weather, add_favorite, remove_favorite, clear_favorites
from handlers.notifications import notification_settings, show_my_notifications, add_notification_step1, add_notification_step2
from handlers.history import history_menu, handle_history_city, clear_history
from handlers.weather import week_forecast, week_forecast_by_coordinates, show_day_forecast
from handlers.commands import settings
from utils import get_utc_offset

logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: CallbackContext):
    """Основной обработчик callback-запросов"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    logger.info(f"User {user_id} pressed button with data: {data}")

    # Обработка запросов погоды
    if data.startswith("weather"):
        await handle_weather_callback(update, context, data)
        return
    
    # Добавление в избранное
    elif data.startswith("add_favorite:"):
        _, city_country = data.split(":", 1)
        city_name, country = city_country.rsplit(":", 1) if ":" in city_country else (city_country, "")
        await add_favorite(update, context, city_name, country)
        return
    
    # Удаление из избранного
    elif data.startswith("remove_favorite:"):
        _, city_country = data.split(":", 1)
        city_name, country = city_country.rsplit(":", 1) if ":" in city_country else (city_country, "")
        await remove_favorite(update, context, city_name, country)
        return
    
    # Погода для города из избранного
    elif data.startswith("fav_"):
        city_name = data.replace("fav_", "")
        await handle_favorite_weather(update, context, city_name)
        return
    
    # Назад к избранному
    elif data == "favorites_back":
        await favorites(update, context)
        return
    
    # Дополнительные функции
    elif data == "extra_features":
        await extra_features_menu(update, context)
        return
    
    # Переключение функций
    elif data.startswith("toggle_"):
        feature = data.replace("toggle_", "")
        UserDataManager.toggle_user_feature(context, user_id, feature)
        await extra_features_menu(update, context)
        return
    
    # История
    elif data.startswith("history_"):
        city_name = data.replace("history_", "")
        await handle_history_city(update, context, city_name)
        return
    
    elif data == "clear_history":
        await clear_history(update, context)
        return
    
    # Главное меню
    elif data == "main_menu":
        await return_to_main_menu(update, context)
        return
    
    # Уведомления
    elif data == "my_notifications":
        await show_my_notifications(update, context)
        return
    
    elif data == "add_notification_step1":
        await add_notification_step1(update, context)
        return
    
    elif data == "disable_all_notifications":
        UserDataManager.disable_all_notifications(context, user_id)
        await show_my_notifications(update, context)
        return
    
    # Поделиться погодой
    elif data.startswith("share_weather:"):
        await share_weather(update, context, data)
        return
    
    # Дополнительные данные
    elif data.startswith("extra_data:"):
        await handle_extra_data(update, context, data)
        return
    
    # Прогноз на неделю
    elif data.startswith("week_forecast:"):
        await handle_week_forecast(update, context, data)
        return
    
    # Подтверждение региона
    elif data.startswith("confirm_region:"):
        await handle_confirm_region(update, context, data)
        return
    
    elif data.startswith("confirm_region_yes:"):
        await handle_confirm_region_yes(update, context, data)
        return
    
    elif data == "region_cancel":
        if lang == "rus":
            await query.edit_message_text("❌ Установка региона отменена")
        else:
            await query.edit_message_text("❌ Region setup cancelled")
        return
    
    # Настройки языка
    elif data == "language":
        await language_menu(update, context)
        return
    
    elif data.startswith("lang_"):
        await handle_language_change(update, context, data)
        return
    
    # Назад в настройки
    elif data == "settings_back":
        await settings(update, context)
        return
    
    # Изменение региона
    elif data == "change_region":
        await change_region_menu(update, context)
        return
    
    elif data == "region_back":
        await change_region_menu(update, context)
        return
    
    elif data == "autodetect_region":
        await autodetect_region(update, context)
        return
    
    elif data == "autodetect_location_request":
        await autodetect_region(update, context)
        return
    
    elif data == "manual_set_region":
        await manual_set_region(update, context)
        return
    
    # Изменение часового пояса
    elif data == "change_timezone":
        await change_timezone_menu(update, context)
        return
    
    elif data.startswith("tz_user_"):
        await handle_timezone_change(update, context, data)
        return
    
    elif data == "manual_timezone_number":
        await manual_timezone_number(update, context)
        return
    
    # Управление уведомлениями
    elif data == "tz_add_my":
        await handle_tz_add_my(update, context)
        return
    
    elif data == "tz_add_list":
        await tz_add_list(update, context)
        return
    
    elif data.startswith("tz_add_"):
        await handle_tz_add(update, context, data)
        return
    
    elif data == "manual_time_add":
        await manual_time_add(update, context)
        return
    
    elif data.startswith("time_add_"):
        await handle_time_add(update, context, data)
        return
    
    elif data.startswith("edit_notification_"):
        await edit_notification(update, context, data)
        return
    
    elif data.startswith("delete_notification_"):
        await delete_notification(update, context, data)
        return
    
    # Настройки давления
    elif data == "pressure_settings":
        await pressure_settings_menu(update, context)
        return
    
    elif data in ("pressure_mm", "pressure_hpa"):
        await handle_pressure_change(update, context, data)
        return
    
    # Прогноз на день
    elif data.startswith("day_forecast_"):
        await handle_day_forecast(update, context, data)
        return
    
    # Очистка избранного
    elif data == "clear_favorites":
        await clear_favorites(update, context)
        return
    
    # Партнеры
    elif data == "partners":
        await partners_menu(update, context)
        return
    
    else:
        logger.warning(f"Unknown callback data: {data}")
        if lang == 'rus':
            await query.answer("⚠️ Неизвестная команда")
        else:
            await query.answer("⚠️ Unknown command")

async def handle_weather_callback(update: Update, context: CallbackContext, data: str):
    """Обработка запроса погоды"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    parts = data.split(":", 1)[1]
    if "|" in parts:
        city_name, coords = parts.split("|", 1)
        lat, lon = map(float, coords.split(",", 1))
        
        features = UserDataManager.get_user_features(context, user_id)
        timezone = UserDataManager.get_user_timezone(context, user_id)
        pressure_unit = UserDataManager.get_user_pressure_unit(context, user_id)
        
        weather_info, weather_text = get_weather_by_coordinates(
            lat,
            lon,
            lang,
            features,
            timezone,
            pressure_unit=pressure_unit
        )
    else:
        city_name = parts
        features = UserDataManager.get_user_features(context, user_id)
        timezone = UserDataManager.get_user_timezone(context, user_id)
        pressure_unit = UserDataManager.get_user_pressure_unit(context, user_id)
        
        weather_info, weather_text = get_weather(
            city_name,
            lang,
            features,
            timezone,
            pressure_unit=pressure_unit
        )

    if weather_info:
        actual_city = weather_info["city"]
        country = weather_info.get("country", "")
        favorites_dict = UserDataManager.get_user_favorites_dict(context, user_id)
        
        from user_data import make_favorite_key
        fav_key = make_favorite_key(actual_city, country)
        city_in_favorites = fav_key in favorites_dict
        current_region = UserDataManager.get_user_region(context, user_id)
        is_current_region = (actual_city.lower() == current_region.lower())

        keyboard = create_weather_keyboard(
            actual_city,
            city_in_favorites,
            lang,
            show_forecast=True,
            is_current_region=is_current_region,
            lat=weather_info.get("lat"),
            lon=weather_info.get("lon"),
            country=country,
        )
        await query.edit_message_text(weather_text, reply_markup=keyboard)
    else:
        await query.edit_message_text(
            weather_text or ("❌ Не удалось получить погоду." if lang == "rus" else "❌ Failed to get weather.")
        )

async def extra_features_menu(update: Update, context: CallbackContext):
    """Меню дополнительных функций"""
    query = update.callback_query if hasattr(update, 'callback_query') else None
    user_id = update.effective_user.id if update.message else query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    features = UserDataManager.get_user_features(context, user_id)
    
    if lang == 'rus':
        text = "⚙️ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ\n\n"
        text += "Включайте и отключайте дополнительные данные в сводке о погоде:"
    else:
        text = "⚙️ EXTRA FEATURES\n\n"
        text += "Enable and disable additional data in weather report:"
    
    keyboard = create_extra_features_keyboard(lang, features)
    
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)

async def return_to_main_menu(update: Update, context: CallbackContext):
    """Вернуться в главное меню"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    context.user_data.clear()
    
    keyboard = get_main_menu_keyboard(lang)
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if lang == 'rus':
        await query.edit_message_text("Главное меню", reply_markup=reply_markup)
    else:
        await query.edit_message_text("Main menu", reply_markup=reply_markup)

async def share_weather(update: Update, context: CallbackContext, data: str):
    """Поделиться погодой"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    payload = data.split(":", 1)[1]
    if "|" in payload:
        city_name, coords = payload.split("|", 1)
        lat, lon = map(float, coords.split(",", 1))
        features = UserDataManager.get_user_features(context, user_id)
        timezone = UserDataManager.get_user_timezone(context, user_id)
        weather_info, weather_text = get_weather_by_coordinates(
            lat,
            lon,
            lang,
            features,
            timezone,
        )
    else:
        city_name = payload
        features = UserDataManager.get_user_features(context, user_id)
        timezone = UserDataManager.get_user_timezone(context, user_id)
        weather_info, weather_text = get_weather(
            city_name,
            lang,
            features,
            timezone,
        )

    if not weather_info:
        await query.answer("❌ Ошибка получения погоды" if lang == "rus" else "❌ Error getting weather")
        return

    if lang == "rus":
        share_text = weather_text + "\n\n@Weather_worldmap_bot - узнай свою погоду!"
        button_text = "📤 Поделиться в Telegram"
    else:
        share_text = weather_text + "\n\n@Weather_worldmap_bot - check your weather!"
        button_text = "📤 Share in Telegram"

    encoded = urllib.parse.quote(share_text)
    url = f"https://t.me/share/url?url={encoded}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=url)]])
    await query.message.reply_text(share_text, reply_markup=kb)

async def handle_extra_data(update: Update, context: CallbackContext, data: str):
    """Обработка запроса дополнительных данных"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    payload = data.split(":", 1)[1]
    
    # payload: city|lat,lon  или просто city
    if "|" in payload:
        city_name, coords = payload.split("|", 1)
        try:
            lat, lon = map(float, coords.split(",", 1))
        except ValueError:
            lat = lon = None
    else:
        city_name = payload
        lat = lon = None

    features = UserDataManager.get_user_features(context, user_id)
    timezone = UserDataManager.get_user_timezone(context, user_id)

    # Для extra_data нам не нужны координаты, только название города
    success, extra_text, extended_data = get_extended_data(
        city_name,  # Передаем только название города
        lang,
        features,
        timezone,
    )

    if success:
        # Оставляем кнопку «Показать погоду» для этого же города
        if lat is not None and lon is not None:
            weather_callback = f"weather:{city_name}|{lat},{lon}"
        else:
            weather_callback = f"weather:{city_name}"
            
        kb = [[InlineKeyboardButton(
            "🌤 Показать погоду" if lang == "rus" else "🌤 Show weather",
            callback_data=weather_callback
        )]]
        await query.edit_message_text(extra_text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await query.edit_message_text(extra_text)

async def handle_week_forecast(update: Update, context: CallbackContext, data: str):
    """Обработка запроса недельного прогноза"""
    payload = data.split(":", 1)[1]
    if "|" in payload:
        city_name, coords = payload.split("|", 1)
        lat, lon = map(float, coords.split(",", 1))
        await week_forecast_by_coordinates(update, context, lat, lon, city_name)
    else:
        city_name = payload
        await week_forecast(update, context, city_name)

async def handle_confirm_region(update: Update, context: CallbackContext, data: str):
    """Подтверждение установки региона"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    _, city_coords = data.split(":", 1)
    city_name, coords = city_coords.rsplit(":", 1)
    lat, lon = map(float, coords.split(","))

    # Подтверждение региона
    kb = [[
        InlineKeyboardButton("✅ Да" if lang == "rus" else "✅ Yes",
                             callback_data=f"confirm_region_yes:{city_name}:{lat},{lon}"),
        InlineKeyboardButton("❌ Нет" if lang == "rus" else "❌ No",
                             callback_data="region_cancel")
    ]]
    text = f"Установить {city_name} вашим регионом?" if lang == "rus" else f"Set {city_name} as your region?"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def handle_confirm_region_yes(update: Update, context: CallbackContext, data: str):
    """Подтверждение установки региона - да"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    parts = data.replace("confirm_region_yes:", "").split(":")
    city_name = parts[0]
    if len(parts) > 1:
        coords = parts[1]

    UserDataManager.set_user_region(context, user_id, city_name)
    await query.answer(
        "✅ Регион установлен!" if lang == "rus" else "✅ Region set!"
    )

    # Показываем погоду с is_current_region=True
    features = UserDataManager.get_user_features(context, user_id)
    timezone = UserDataManager.get_user_timezone(context, user_id)
    pressure_unit = UserDataManager.get_user_pressure_unit(context, user_id)
    
    weather_info, weather_text = get_weather(
        city_name,
        lang,
        features,
        timezone,
        pressure_unit=pressure_unit
    )

    if weather_info:
        actual_city = weather_info["city"]
        country = weather_info.get("country", "")
        favorites_dict = UserDataManager.get_user_favorites_dict(context, user_id)
        
        from user_data import make_favorite_key
        fav_key = make_favorite_key(actual_city, country)
        city_in_favorites = fav_key in favorites_dict

        keyboard = create_weather_keyboard(
            actual_city,
            city_in_favorites,
            lang,
            show_forecast=True,
            is_current_region=True,
            lat=weather_info.get("lat"),
            lon=weather_info.get("lon"),
            country=country
        )
        await query.edit_message_text(weather_text, reply_markup=keyboard)

async def language_menu(update: Update, context: CallbackContext):
    """Меню выбора языка"""
    query = update.callback_query if hasattr(update, 'callback_query') else None
    user_id = update.effective_user.id if update.message else query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    if lang == 'rus':
        text = "🌐 Выбор языка"
    else:
        text = "🌐 Language selection"

    keyboard = create_language_keyboard(lang)

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def handle_language_change(update: Update, context: CallbackContext, data: str):
    """Обработка изменения языка"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if data == "lang_ru":
        UserDataManager.set_user_lang(context, user_id, 'rus')
        keyboard = get_main_menu_keyboard('rus')
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await query.message.reply_text("✅ Язык изменён на русский", reply_markup=reply_markup)
    elif data == "lang_en":
        UserDataManager.set_user_lang(context, user_id, 'eng')
        keyboard = get_main_menu_keyboard('eng')
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await query.message.reply_text("✅ Language changed to English", reply_markup=reply_markup)

async def change_region_menu(update: Update, context: CallbackContext):
    """Меню изменения региона"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    if lang == 'rus':
        text = "📍 Изменение региона\n\nВыберите способ:"
    else:
        text = "📍 Change region\n\nChoose method:"

    keyboard = create_region_setup_keyboard(lang)
    await query.edit_message_text(text, reply_markup=keyboard)

async def autodetect_region(update: Update, context: CallbackContext):
    """Автоматическое определение региона"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    try:
        if lang == 'rus':
            text = "📍 Автоматическое определение региона\n\n"
            text += "⚠️ Работает только на мобильных устройствах!\n\n"
            text += "Нажмите кнопку ниже для отправки вашего местоположения."
        else:
            text = "📍 Automatic region detection\n\n"
            text += "⚠️ Works only on mobile devices!\n\n"
            text += "Press the button below to send your location."

        keyboard = create_location_keyboard(lang)

        context.user_data['awaiting_location'] = True
        context.user_data['location_for'] = 'region_setup'
        context.user_data['setting_region'] = True
        context.user_data['was_setting_region'] = True

        await query.message.reply_text(text, reply_markup=keyboard)

        if lang == 'rus':
            await query.edit_message_text("⏳ Ожидание местоположения для определения региона...")
        else:
            await query.edit_message_text("⏳ Waiting for location to detect region...")

    except Exception as e:
        logger.error(f"Ошибка autodetect_region: {e}")
        if lang == 'rus':
            await query.message.reply_text("❌ Ошибка определения региона")
        else:
            await query.message.reply_text("❌ Error detecting region")

async def manual_set_region(update: Update, context: CallbackContext):
    """Ручная установка региона"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    context.user_data['setting_region'] = True
    context.user_data['manual_region_input'] = True

    if lang == 'rus':
        await query.message.reply_text(
            "✍️ Введите название города:\n\n"
            "Например: Москва, Лондон, Париж\n\n"
            "Или введите /cancel для отмены."
        )
    else:
        await query.message.reply_text(
            "✍️ Enter city name:\n\n"
            "Example: Moscow, London, Paris\n\n"
            "Or type /cancel to cancel."
        )

async def change_timezone_menu(update: Update, context: CallbackContext):
    """Меню изменения часового пояса"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    if lang == 'rus':
        text = "🕐 Выбор часового пояса\n\n"
        text += "Часовой пояс используется для отображения времени восхода/заката."
    else:
        text = "🕐 Timezone selection\n\n"
        text += "Timezone is used to display sunrise/sunset time."

    keyboard = create_timezone_keyboard(lang)
    await query.edit_message_text(text, reply_markup=keyboard)

async def handle_timezone_change(update: Update, context: CallbackContext, data: str):
    """Обработка изменения часового пояса"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    timezone_code = data.split("_", 2)[2]
    timezone_map = {
        'mos': 'Europe/Moscow',
        'lon': 'Europe/London',
        'ny': 'America/New_York',
        'tok': 'Asia/Tokyo',
        'sid': 'Australia/Sydney',
        'dub': 'Asia/Dubai'
    }

    timezone_str = timezone_map.get(timezone_code, 'Europe/Moscow')
    UserDataManager.set_user_timezone(context, user_id, timezone_str)
    utc_offset = get_utc_offset(timezone_str)

    if lang == 'rus':
        await query.answer(f"✅ Часовой пояс установлен: {utc_offset}")
        await query.edit_message_text(
            f"✅ Часовой пояс изменён\n\n"
            f"🕐 Новый часовой пояс: {utc_offset}\n"
            f"🌍 Название: {timezone_str}\n\n"
            f"Теперь восход/закат будут показываться по этому времени."
        )
    else:
        await query.answer(f"✅ Timezone set: {utc_offset}")
        await query.edit_message_text(
            f"✅ Timezone changed\n\n"
            f"🕐 Timezone: {utc_offset}\n"
            f"🌍 Name: {timezone_str}\n\n"
            f"Now sunrise/sunset will be shown in this time."
        )

async def manual_timezone_number(update: Update, context: CallbackContext):
    """Ручной ввод часового пояса"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    context.user_data['setting_timezone_number'] = True

    if lang == 'rus':
        await query.message.reply_text(
            "🔢 Введите число для установки часового пояса\n\n"
            "Примеры:\n"
            "3 → UTC+3 (Москва)\n"
            "-5 → UTC-5 (Нью-Йорк)\n"
            "0 → UTC+0 (Лондон)\n"
            "9 → UTC+9 (Токио)\n\n"
            "Диапазон от -12 до +14\n\n"
            "Или введите /cancel для отмена."
        )
    else:
        await query.message.reply_text(
            "🔢 Enter number to set timezone\n\n"
            "Examples:\n"
            "3 → UTC+3 (Moscow)\n"
            "-5 → UTC-5 (New York)\n"
            "0 → UTC+0 (London)\n"
            "9 → UTC+9 (Tokyo)\n\n"
            "Range from -12 to +14\n\n"
            "Or type /cancel to cancel."
        )

    await query.edit_message_text("⏳ Ожидание ввода числа..." if lang == 'rus' else "⏳ Waiting for number input...")

async def handle_tz_add_my(update: Update, context: CallbackContext):
    """Добавить уведомление с моим часовым поясом"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    user_tz = UserDataManager.get_user_timezone(context, user_id)
    
    # Преобразуем в формат timezone string
    if user_tz.startswith("UTC"):
        offset_str = user_tz.replace("UTC", "").strip()
        if offset_str.startswith("+") or offset_str.startswith("-"):
            offset_hours = float(offset_str)
        else:
            offset_hours = float(offset_str) if offset_str else 0

        tz_map = {
            3: 'Europe/Moscow',
            0: 'Europe/London',
            -5: 'America/New_York',
            9: 'Asia/Tokyo',
            10: 'Australia/Sydney',
            4: 'Asia/Dubai'
        }
        timezone_str = tz_map.get(int(offset_hours), user_tz)
    else:
        timezone_str = user_tz

    await add_notification_step2(update, context, timezone_str)

async def tz_add_list(update: Update, context: CallbackContext):
    """Выбор часового пояса из списка"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    if lang == 'rus':
        text = f"🌍 Выбор часового пояса из списка\n\nВыберите часовой пояс:"
        from telegram import InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Москва (UTC+3)", callback_data="tz_add_mos")],
            [InlineKeyboardButton("🇬🇧 Лондон (UTC+0)", callback_data="tz_add_lon")],
            [InlineKeyboardButton("🇺🇸 Нью-Йорк (UTC-5)", callback_data="tz_add_ny")],
            [InlineKeyboardButton("🇯🇵 Токио (UTC+9)", callback_data="tz_add_tok")],
            [InlineKeyboardButton("🇦🇺 Сидней (UTC+10)", callback_data="tz_add_sid")],
            [InlineKeyboardButton("🇦🇪 Дубай (UTC+4)", callback_data="tz_add_dub")],
            [InlineKeyboardButton("◀️ Назад", callback_data="add_notification_step1")]
        ]
    else:
        text = f"🌍 Choose timezone from list\n\nSelect timezone:"
        from telegram import InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Moscow (UTC+3)", callback_data="tz_add_mos")],
            [InlineKeyboardButton("🇬🇧 London (UTC+0)", callback_data="tz_add_lon")],
            [InlineKeyboardButton("🇺🇸 New York (UTC-5)", callback_data="tz_add_ny")],
            [InlineKeyboardButton("🇯🇵 Tokyo (UTC+9)", callback_data="tz_add_tok")],
            [InlineKeyboardButton("🇦🇺 Sydney (UTC+10)", callback_data="tz_add_sid")],
            [InlineKeyboardButton("🇦🇪 Dubai (UTC+4)", callback_data="tz_add_dub")],
            [InlineKeyboardButton("◀️ Back", callback_data="add_notification_step1")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def handle_tz_add(update: Update, context: CallbackContext, data: str):
    """Обработка выбора часового пояса"""
    timezone_code = data.replace("tz_add_", "")
    timezone_map = {
        'mos': 'Europe/Moscow',
        'lon': 'Europe/London',
        'ny': 'America/New_York',
        'tok': 'Asia/Tokyo',
        'sid': 'Australia/Sydney',
        'dub': 'Asia/Dubai'
    }

    timezone_str = timezone_map.get(timezone_code, 'Europe/Moscow')
    await add_notification_step2(update, context, timezone_str)

async def manual_time_add(update: Update, context: CallbackContext):
    """Ручной ввод времени уведомления"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    context.user_data['action'] = 'add_notification_time'
    
    if lang == 'rus':
        await query.message.reply_text(
            "🕐 Введите время в формате ЧЧ:ММ\n\n"
            "Например: 08:30, 14:00, 19:45\n\n"
            "Или введите /cancel для отмены"
        )
    else:
        await query.message.reply_text(
            "🕐 Enter time in HH:MM format\n\n"
            "Example: 08:30, 14:00, 19:45\n\n"
            "Or type /cancel to cancel"
        )

async def handle_time_add(update: Update, context: CallbackContext, data: str):
    """Обработка выбора времени"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    time_code = data.replace("time_add_", "")

    if time_code == "manual":
        context.user_data['action'] = 'add_notification_time'

        if lang == 'rus':
            await query.message.reply_text(
                "🕐 Введите время в формате ЧЧ:ММ\n\n"
                "Например: 08:30, 14:00, 19:45\n\n"
                "Или /cancel для отмены"
            )
        else:
            await query.message.reply_text(
                "🕐 Enter time in HH:MM format\n\n"
                "Example: 08:30, 14:00, 19:45\n\n"
                "Or /cancel to cancel"
            )
    else:
        hour = int(time_code[:-1])
        minute = int(time_code[-1]) * 10 if len(time_code) > 1 else 0

        if 'temp_timezone' in context.user_data:
            timezone_str = context.user_data['temp_timezone']
            success, result = UserDataManager.add_user_notification(context, user_id, hour, minute, timezone_str)

            if success:
                region = UserDataManager.get_user_region(context, user_id)
                utc_offset = get_utc_offset(timezone_str)

                context.user_data.clear()

                if lang == 'rus':
                    await query.answer(f"✅ Уведомление на {hour:02d}:{minute:02d} добавлено!")
                    await query.message.reply_text(
                        f"✅ Уведомление добавлено!\n\n"
                        f"⏰ Время отправки уведомления: {hour:02d}:{minute:02d}\n"
                        f"📍 Регион: {region}\n"
                        f"🕐 Часовой пояс: {utc_offset}\n\n"
                        f"Каждый день в указанное время вы будете получать сводку о погоде в вашем регионе."
                    )
                else:
                    await query.answer(f"✅ Notification at {hour:02d}:{minute:02d} added!")
                    await query.message.reply_text(
                        f"✅ Notification added!\n\n"
                        f"⏰ Notification time: {hour:02d}:{minute:02d}\n"
                        f"📍 Region: {region}\n"
                        f"🕐 Timezone: {utc_offset}\n\n"
                        f"Every day at specified time you will receive weather report for your region."
                    )

                await show_my_notifications(update, context)
            elif result == "limit_exceeded":
                await query.answer("❌ Лимит достигнут" if lang == 'rus' else "❌ Limit reached", show_alert=True)
            else:
                await query.answer("❌ Уже существует" if lang == 'rus' else "❌ Already exists")

async def edit_notification(update: Update, context: CallbackContext, data: str):
    """Редактирование уведомления"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    notification_id = data.replace("edit_notification_", "")
    context.user_data['editing_notification_id'] = notification_id

    notifications = UserDataManager.get_user_notifications(context, user_id)
    notification = None

    for n in notifications:
        if n['id'] == notification_id:
            notification = n
            break

    if notification:
        if lang == 'rus':
            text = f"⚙️ Уведомление\n\n"
            text += f"⏰ Время: {notification['hour']:02d}:{notification['minute']:02d}\n"
            text += f"🕐 Часовой пояс: {notification['timezone']}\n"
            text += f"📍 Регион: {notification['region']}\n\n"
            from telegram import InlineKeyboardButton
            keyboard = [
                [InlineKeyboardButton("❌ Удалить", callback_data=f"delete_notification_{notification_id}")],
                [InlineKeyboardButton("◀️ Назад", callback_data="my_notifications")]
            ]
        else:
            text = f"⚙️ Notification\n\n"
            text += f"⏰ Time: {notification['hour']:02d}:{notification['minute']:02d}\n"
            text += f"🕐 Timezone: {notification['timezone']}\n"
            text += f"📍 Region: {notification['region']}\n\n"
            from telegram import InlineKeyboardButton
            keyboard = [
                [InlineKeyboardButton("❌ Delete", callback_data=f"delete_notification_{notification_id}")],
                [InlineKeyboardButton("◀️ Back", callback_data="my_notifications")]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

async def delete_notification(update: Update, context: CallbackContext, data: str):
    """Удаление уведомления"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    notification_id = data.replace("delete_notification_", "")
    UserDataManager.remove_user_notification(context, user_id, notification_id)

    if lang == 'rus':
        await query.answer("❌ Уведомление удалено")
    else:
        await query.answer("❌ Notification deleted")

    await show_my_notifications(update, context)

async def pressure_settings_menu(update: Update, context: CallbackContext):
    """Меню настроек давления"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    unit = UserDataManager.get_user_pressure_unit(context, user_id)

    if lang == "rus":
        text = "🔽 Давление\n\nВыберите единицы измерения:"
    else:
        text = "🔽 Pressure\n\nChoose units:"

    keyboard = create_pressure_settings_keyboard(lang, unit)
    await query.edit_message_text(text, reply_markup=keyboard)

async def handle_pressure_change(update: Update, context: CallbackContext, data: str):
    """Обработка изменения единиц давления"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    new_unit = "mmhg" if data == "pressure_mm" else "hpa"
    UserDataManager.set_user_pressure_unit(context, user_id, new_unit)

    unit = UserDataManager.get_user_pressure_unit(context, user_id)

    if lang == "rus":
        text = "🔽 Давление\n\nВыберите единицы измерения:"
    else:
        text = "🔽 Pressure\n\nChoose units:"

    keyboard = create_pressure_settings_keyboard(lang, unit)
    await query.edit_message_text(text, reply_markup=keyboard)

async def handle_day_forecast(update: Update, context: CallbackContext, data: str):
    """Обработка запроса прогноза на день"""
    parts = data.replace("day_forecast_", "").split("_")
    city_name = parts[0]
    day_offset = int(parts[1])
    await show_day_forecast(update, context, city_name, day_offset)

async def partners_menu(update: Update, context: CallbackContext):
    """Меню партнеров"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    if lang == 'rus':
        text = "🤝 Партнёры\n\n"
        text += "В данный момент список партнёров пуст.\n\n"
        text += "Следите за обновлениями!"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="settings_back")]]
    else:
        text = "🤝 Partners\n\n"
        text += "Currently the partner list is empty.\n\n"
        text += "Stay tuned!"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="settings_back")]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)