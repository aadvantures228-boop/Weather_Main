from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
import logging

from user_data import UserDataManager
from keyboards import get_main_menu_keyboard, create_settings_keyboard
from database import init_db

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    # Инициализация БД
    init_db()

    # Сбрасываем историю поиска
    if 'history' not in context.bot_data:
        context.bot_data['history'] = {}
    context.bot_data['history'][user_id] = []

    # Получаем клавиатуру главного меню
    keyboard = get_main_menu_keyboard(lang)
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    if lang == 'rus':
        text = (
            "👋 Привет! Я покажу тебе погоду в любой точке мира 🌍\n\n"
            "Просто напиши мне название города, и я пришлю сводку о погоде!\n\n"
            "Все функции доступны бесплатно!"
        )
    else:
        text = (
            "👋 Hello! I will show you the weather anywhere in the world 🌍\n\n"
            "Just write me the name of the city and I will send you a weather report!\n\n"
            "All features are free!"
        )

    await update.message.reply_text(text, reply_markup=reply_markup)

async def settings(update: Update, context: CallbackContext):
    """Обработчик команды /settings"""
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    region = UserDataManager.get_user_region(context, user_id)
    features = UserDataManager.get_user_features(context, user_id)

    if lang == 'rus':
        # Формируем текст для дополнительных функций
        features_text = ""
        if features.get('cloudiness', False):
            features_text += "☁️ Облачность: ✅\n"
        else:
            features_text += "☁️ Облачность: ❌\n"
        
        if features.get('wind_direction', False):
            features_text += "🧭 Направление ветра: ✅\n"
        else:
            features_text += "🧭 Направление ветра: ❌\n"
        
        if features.get('wind_gust', False):
            features_text += "💨 Порывы ветра: ✅\n"
        else:
            features_text += "💨 Порывы ветра: ❌\n"
        
        if features.get('sunrise_sunset', False):
            features_text += "🌅 Восход/закат: ✅\n"
        else:
            features_text += "🌅 Восход/закат: ❌\n"

        text = f"⚙️ Настройки\n\n{features_text}"
    else:
        text = "⚙️ Settings"

    keyboard = create_settings_keyboard(lang, region, features)
    
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def cancel(update: Update, context: CallbackContext):
    """Обработчик команды /cancel"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    context.user_data.clear()

    if lang == 'rus':
        await update.message.reply_text("❌ Операция отменена.")
    else:
        await update.message.reply_text("❌ Operation cancelled.")

async def help_command(update: Update, context: CallbackContext):
    """Обработчик команды /help"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    if lang == 'rus':
        text = """
🤖 *Помощь по боту Weather Worldmap*

*Основные команды:*
• Напишите название города — получите погоду
• `/start` — главное меню
• `/settings` — настройки
• `/cancel` — отмена текущей операции

*Функции:*
• 🌤 Погода в любом городе мира
• ⭐ Избранные города
• 🔔 Ежедневные уведомления
• 📍 Погода по геолокации
• 📜 История поиска
• ⚙️ Дополнительные данные (облачность, направление ветра и т.д.)

*Поддерживаемые города РФ:*
Более 100 городов России с точными координатами!
"""
    else:
        text = """
🤖 *Weather Worldmap Bot Help*

*Main commands:*
• Type city name — get weather
• `/start` — main menu
• `/settings` — settings
• `/cancel` — cancel current operation

*Features:*
• 🌤 Weather in any city worldwide
• ⭐ Favorite cities
• 🔔 Daily notifications
• 📍 Weather by geolocation
• 📜 Search history
• ⚙️ Extra data (cloudiness, wind direction, etc.)

*Supported Russian cities:*
Over 100 Russian cities with precise coordinates!
"""

    await update.message.reply_text(text, parse_mode='Markdown')