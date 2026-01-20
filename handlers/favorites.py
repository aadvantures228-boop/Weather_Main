from telegram import Update, InlineKeyboardMarkup
from telegram.ext import CallbackContext
import logging

from user_data import UserDataManager
from keyboards import create_favorites_keyboard
from weather_api import get_weather
from keyboards import create_weather_keyboard
from user_data import make_favorite_key

logger = logging.getLogger(__name__)

async def favorites(update: Update, context: CallbackContext):
    """Показать избранное"""
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    favs_dict = UserDataManager.get_user_favorites_dict(context, user_id)
    favorite_cities = list(favs_dict.values())

    if favorite_cities:
        if lang == 'rus':
            text = f"⭐ Избранное ({len(favorite_cities)} городов)\n\nНажмите на город или удалите:"
        else:
            text = f"⭐ Favorites ({len(favorite_cities)} cities)\n\nClick city or remove:"
        
        keyboard = create_favorites_keyboard(lang, favs_dict)
    else:
        if lang == 'rus':
            text = "⭐ Избранное пустое\n\n✨ Добавляйте города в избранное для быстрого доступа к прогнозу погоды!"
        else:
            text = "⭐ Favorites empty\n\n✨ Add cities to favorites for quick access to weather forecast!"
        
        keyboard = InlineKeyboardMarkup([])

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def handle_favorite_weather(update: Update, context: CallbackContext, city_name: str):
    """Обработка запроса погоды для города из избранного"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    # Получаем настройки пользователя
    features = UserDataManager.get_user_features(context, user_id)
    timezone = UserDataManager.get_user_timezone(context, user_id)
    pressure_unit = UserDataManager.get_user_pressure_unit(context, user_id)
    
    # Получаем погоду
    weather_info, weather_text = get_weather(
        city_name,
        lang,
        features,
        timezone,
        pressure_unit=pressure_unit
    )
    
    if weather_info:
        city_name_display = weather_info["city"]
        country = weather_info.get("country", "")
        favorites_dict = UserDataManager.get_user_favorites_dict(context, user_id)
        fav_key = make_favorite_key(city_name_display, country)
        city_in_favorites = fav_key in favorites_dict
        current_region = UserDataManager.get_user_region(context, user_id)
        is_current_region = (city_name_display.lower() == current_region.lower())
        
        keyboard = create_weather_keyboard(
            city_name_display,
            city_in_favorites,
            lang,
            show_forecast=True,
            is_current_region=is_current_region,
            lat=weather_info.get("lat"),
            lon=weather_info.get("lon"),
            country=country
        )
        await query.edit_message_text(weather_text, reply_markup=keyboard)
    else:
        await query.edit_message_text(weather_text)

async def add_favorite(update: Update, context: CallbackContext, city_name: str, country: str = ""):
    """Добавить город в избранное"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    success = UserDataManager.add_user_favorite(context, user_id, city_name, country)
    
    if success:
        await query.answer(
            f"✅ {city_name} добавлен в избранное!" if lang == "rus" else f"✅ {city_name} added to favorites!"
        )
        
        # Обновляем клавиатуру
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
            current_region = UserDataManager.get_user_region(context, user_id)
            is_current_region = (actual_city.lower() == current_region.lower())

            keyboard = create_weather_keyboard(
                actual_city,
                True,
                lang,
                show_forecast=True,
                is_current_region=is_current_region,
                lat=weather_info.get("lat"),
                lon=weather_info.get("lon"),
                country=country
            )
            await query.edit_message_text(weather_text, reply_markup=keyboard)
    else:
        await query.answer(
            f"❌ {city_name} уже в избранном!" if lang == "rus" else f"❌ {city_name} already in favorites!"
        )

async def remove_favorite(update: Update, context: CallbackContext, city_name: str, country: str = ""):
    """Удалить город из избранного"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    success = UserDataManager.remove_user_favorite(context, user_id, city_name, country)
    
    if success:
        await query.answer(
            f"✅ {city_name} удален из избранного!" if lang == "rus" else f"✅ {city_name} removed from favorites!"
        )
        
        # Обновляем клавиатуру
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
            current_region = UserDataManager.get_user_region(context, user_id)
            is_current_region = (actual_city.lower() == current_region.lower())

            keyboard = create_weather_keyboard(
                actual_city,
                False,
                lang,
                show_forecast=True,
                is_current_region=is_current_region,
                lat=weather_info.get("lat"),
                lon=weather_info.get("lon"),
                country=country
            )
            await query.edit_message_text(weather_text, reply_markup=keyboard)
    else:
        await query.answer(
            f"❌ {city_name} не найден в избранном!" if lang == "rus" else f"❌ {city_name} not found in favorites!"
        )

async def clear_favorites(update: Update, context: CallbackContext):
    """Очистить избранное"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    UserDataManager.clear_user_favorites(context, user_id)
    
    if lang == 'rus':
        await query.answer("❌ Избранное очищено")
        await query.edit_message_text(
            "❌ Избранное очищено\n\n✨ Добавляйте города в избранное для быстрого доступа!")
    else:
        await query.answer("❌ Favorites cleared")
        await query.edit_message_text("❌ Favorites cleared\n\n✨ Add cities to favorites for quick access!")