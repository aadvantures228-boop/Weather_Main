import logging
from datetime import time
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from user_data import UserDataManager
from keyboards import create_notification_time_keyboard
from weather_api import get_weather
from utils import get_utc_offset

logger = logging.getLogger(__name__)

async def notification_settings(update: Update, context: CallbackContext):
    """Настройки уведомлений"""
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    region = UserDataManager.get_user_region(context, user_id)
    notifications = UserDataManager.get_user_notifications(context, user_id)
    has_notifications = len(notifications) > 0

    if has_notifications:
        if lang == 'rus':
            text = f"🔔 Автоматическая рассылка погоды\n\n"
            text += f"✅ Уведомления включены ({len(notifications)})\n"
            text += f"📍 Регион: {region}\n\n"
            text += f"Каждый день в указанное время вы будете получать сводку о погоде в вашем регионе."

            keyboard = [
                [InlineKeyboardButton("📋 Мои уведомления", callback_data="my_notifications")],
                [InlineKeyboardButton("➕ Добавить уведомление", callback_data="add_notification_step1")],
                [InlineKeyboardButton("❌ Отключить все уведомления", callback_data="disable_all_notifications")]
            ]
        else:
            text = f"🔔 Automatic weather notifications\n\n"
            text += f"✅ Notifications enabled ({len(notifications)})\n"
            text += f"📍 Region: {region}\n\n"
            text += f"Every day at specified time you will receive weather report for your region."

            keyboard = [
                [InlineKeyboardButton("📋 My notifications", callback_data="my_notifications")],
                [InlineKeyboardButton("➕ Add notification", callback_data="add_notification_step1")],
                [InlineKeyboardButton("❌ Disable all notifications", callback_data="disable_all_notifications")]
            ]
    else:
        if lang == 'rus':
            text = f"🔔 Автоматическая рассылка погоды\n\n"
            text += f"❌ Уведомления отключены\n"
            text += f"📍 Регион: {region}\n\n"
            text += f"Настройте ежедневные уведомления о погоде для вашего региона!"

            keyboard = [
                [InlineKeyboardButton("➕ Добавить уведомление", callback_data="add_notification_step1")]
            ]
        else:
            text = f"🔔 Automatic weather notifications\n\n"
            text += f"❌ Notifications disabled\n"
            text += f"📍 Region: {region}\n\n"
            text += f"Set up daily weather notifications for your region!"

            keyboard = [
                [InlineKeyboardButton("➕ Add notification", callback_data="add_notification_step1")]
            ]

    from telegram import InlineKeyboardButton
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def show_my_notifications(update: Update, context: CallbackContext):
    """Показать мои уведомления"""
    query = update.callback_query if hasattr(update, 'callback_query') else None
    user_id = update.effective_user.id if update.message else query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    notifications = UserDataManager.get_user_notifications(context, user_id)

    if notifications:
        if lang == 'rus':
            text = f"📋 Мои уведомления ({len(notifications)})\n\nНажмите на уведомление для редактирования:"
        else:
            text = f"📋 My notifications ({len(notifications)})\n\nClick notification to edit:"

        from telegram import InlineKeyboardButton
        keyboard = []
        for notification in notifications:
            time_str = f"{notification['hour']:02d}:{notification['minute']:02d}"
            tz_str = get_utc_offset(notification['timezone'])
            button_text = f"⏰ {time_str} ({tz_str})"
            keyboard.append(
                [InlineKeyboardButton(button_text, callback_data=f"edit_notification_{notification['id']}")])

        keyboard.append(
            [InlineKeyboardButton("➕ Добавить" if lang == 'rus' else "➕ Add", callback_data="add_notification_step1")])
    else:
        if lang == 'rus':
            text = "📋 У вас нет активных уведомлений\n\n✨ Добавьте первое уведомление, чтобы получать ежедневную погоду!"
        else:
            text = "📋 You have no active notifications\n\n✨ Add your first notification to receive daily weather!"

        from telegram import InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton("➕ Добавить уведомление" if lang == 'rus' else "➕ Add notification",
                                  callback_data="add_notification_step1")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def add_notification_step1(update: Update, context: CallbackContext):
    """Первый шаг добавления уведомления"""
    query = update.callback_query if hasattr(update, 'callback_query') else None
    user_id = query.from_user.id if query else update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    notifications = UserDataManager.get_user_notifications(context, user_id)
    
    # Проверка на максимальное количество уведомлений
    if len(notifications) >= 10:
        if lang == "rus":
            text = "❌ Достигнут лимит уведомлений\n\nВы можете создать не более 10 уведомлений."
        else:
            text = "❌ Notification limit reached\n\nYou can create up to 10 notifications."
        
        if query:
            await query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    region = UserDataManager.get_user_region(context, user_id)
    user_tz = UserDataManager.get_user_timezone(context, user_id)

    if lang == 'rus':
        text = f"🔔 Добавление уведомления\n\n📍 Регион: {region}\n\nШаг 1: Выберите часовой пояс"
        from telegram import InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton(f"🏙 Мой часовой пояс ({user_tz})", callback_data="tz_add_my")],
            [InlineKeyboardButton("🌍 Выбрать из списка", callback_data="tz_add_list")],
            [InlineKeyboardButton("✍️ Ввести время вручную", callback_data="manual_time_add")],
            [InlineKeyboardButton("◀️ Назад", callback_data="my_notifications")]
        ]
    else:
        text = f"🔔 Adding notification\n\n📍 Region: {region}\n\nStep 1: Choose timezone"
        from telegram import InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton(f"🏙 My timezone ({user_tz})", callback_data="tz_add_my")],
            [InlineKeyboardButton("🌍 Choose from list", callback_data="tz_add_list")],
            [InlineKeyboardButton("✍️ Enter time manually", callback_data="manual_time_add")],
            [InlineKeyboardButton("◀️ Back", callback_data="my_notifications")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def add_notification_step2(update: Update, context: CallbackContext, timezone_str: str):
    """Второй шаг добавления уведомления - выбор времени"""
    query = update.callback_query if hasattr(update, 'callback_query') else None
    user_id = update.effective_user.id if update.message else query.from_user.id
    lang = UserDataManager.get_user_lang(context, user_id)

    context.user_data['temp_timezone'] = timezone_str
    utc_offset = get_utc_offset(timezone_str)

    # Проверяем, редактируем ли мы существующее уведомление
    editing_notification_id = context.user_data.get('editing_notification_id')
    action = context.user_data.get('action')
    is_editing_mode = editing_notification_id and action == 'change_timezone'

    if lang == 'rus':
        if is_editing_mode:
            text = f"🕐 Часовой пояс выбран: {utc_offset}\n\n"
            text += f"Теперь выберите новое время для уведомления:"
        else:
            text = f"🕐 Часовой пояс установлен: {utc_offset}\n\n"
            text += f"Шаг 2: Выберите время уведомления\n\n"
            text += f"📍 Регион: {UserDataManager.get_user_region(context, user_id)}"
        
        keyboard = create_notification_time_keyboard(lang)
    else:
        if is_editing_mode:
            text = f"🕐 Timezone selected: {utc_offset}\n\n"
            text += f"Now choose new time for notification:"
        else:
            text = f"🕐 Timezone set: {utc_offset}\n\n"
            text += f"Step 2: Choose notification time\n\n"
            text += f"📍 Region: {UserDataManager.get_user_region(context, user_id)}"
        
        keyboard = create_notification_time_keyboard(lang)

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif query:
        await query.edit_message_text(text, reply_markup=keyboard)

async def send_daily_notification(context: CallbackContext):
    """Отправка ежедневного уведомления"""
    job = context.job
    notification_id = job.data.get('notification_id')
    user_id = job.data.get('user_id')

    if not notification_id or not user_id:
        logger.error(f"Некорректные данные job: notification_id={notification_id}, user_id={user_id}")
        return

    try:
        lang = UserDataManager.get_user_lang(context, user_id) or 'rus'
        features = UserDataManager.get_user_features(context, user_id)
        logger.info(f"Отправка уведомления user {user_id}, features={features}")
    except Exception as e:
        logger.error(f"Ошибка получения данных для user {user_id}: {e}")
        lang = 'rus'
        features = None

    notifications = UserDataManager.get_user_notifications(context, user_id)
    for notification in notifications:
        if notification['id'] == notification_id:
            region = notification['region']
            try:
                # Используем дополнительные функции пользователя
                from weather_api import get_weather
                weather_info, weather_text = get_weather(
                    region, 
                    lang, 
                    features,
                    UserDataManager.get_user_timezone(context, user_id),
                    pressure_unit=UserDataManager.get_user_pressure_unit(context, user_id)
                )
                if weather_info:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🔔 {region}\n\n{weather_text}"
                    )
                    logger.info(f"Уведомление отправлено пользователю {user_id} для региона {region}")
                else:
                    logger.error(f"Не удалось получить погоду для региона {region}, пользователь {user_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            break

def create_notification_job(context: CallbackContext, user_id: int, notification):
    """Создать задачу уведомления"""
    job_queue = context.application.job_queue
    if job_queue is not None:
        job_name = f"notif_{user_id}_{notification['id']}"
        try:
            remove_notification_job(context, user_id, notification['id'])

            import pytz
            from datetime import time
            timezone_str = notification['timezone']
            user_tz = pytz.timezone(timezone_str)
            notification_time = time(hour=notification['hour'], minute=notification['minute'])

            job_queue.run_daily(
                send_daily_notification,
                time=notification_time,
                days=(0, 1, 2, 3, 4, 5, 6),
                data={'notification_id': notification['id'], 'user_id': user_id},
                name=job_name,
                timezone=user_tz
            )
            logger.info(
                f"Создана задача {job_name} на {notification['hour']:02d}:{notification['minute']:02d} {timezone_str}")
        except Exception as e:
            logger.error(f"Ошибка создания задачи: {e}")

def remove_notification_job(context: CallbackContext, user_id: int, notification_id: str):
    """Удалить задачу уведомления"""
    job_queue = context.application.job_queue
    if job_queue is not None:
        job_name = f"notif_{user_id}_{notification_id}"
        jobs = job_queue.jobs()
        jobs_to_remove = []

        for job in jobs:
            if job.name == job_name:
                jobs_to_remove.append(job)

        for job in jobs_to_remove:
            job.schedule_removal()

        logger.info(f"Удалена задача {job_name}")
        return len(jobs_to_remove) > 0
    return False