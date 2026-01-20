from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
import logging

from user_data import UserDataManager
from weather_api import get_weather
from keyboards import create_weather_keyboard
from user_data import make_favorite_key

logger = logging.getLogger(__name__)

async def history_menu(update: Update, context: CallbackContext):
    """Меню истории поиска"""
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    history = UserDataManager.get_user_history(context, user_id)
    
    if not history:
        if lang == 'rus':
            text = "📜 История поиска\n\nИстория пуста. Начните искать города, и они появятся здесь!"
        else:
            text = "📜 Search History\n\nHistory is empty. Start searching for cities and they will appear here!"
        
        keyboard = []
    else:
        if lang == 'rus':
            text = f"📜 История поиска\n\nПоследние {len(history)} уникальных городов:"
        else:
            text = f"📜 Search History\n\nLast {len(history)} unique cities:"
        
        keyboard = []
        for i, city in enumerate(history, 1):
            keyboard.append([
                InlineKeyboardButton(f"{i}. {city}", callback_data=f"history_{city}")
            ])
    
    # Добавляем кнопку очистки
    if history:
        keyboard.append([InlineKeyboardButton(
            "🗑 Очистить историю" if lang == 'rus' else "🗑 Clear history",
            callback_data="clear_history"
        )])
    
    keyboard.append([InlineKeyboardButton(
        "◀️ Назад" if lang == 'rus' else "◀️ Back",
        callback_data="main_menu"
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def handle_history_city(update: Update, context: CallbackContext, city_name: str):
    """Обработка выбора города из истории"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    # Получаем погоду для выбранного города
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

async def clear_history(update: Update, context: CallbackContext):
    """Очистить историю"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    UserDataManager.clear_user_history(context, user_id)
    
    if lang == 'rus':
        await query.answer("🗑 История очищена")
        text = "📜 История поиска\n\nИстория пуста. Начните искать города, и они появятся здесь!"
    else:
        await query.answer("🗑 History cleared")
        text = "📜 Search History\n\nHistory is empty. Start searching for cities and they will appear here!"
    
    keyboard = [
        [InlineKeyboardButton("◀️ Назад" if lang == 'rus' else "◀️ Back", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)