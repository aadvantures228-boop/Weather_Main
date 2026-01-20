from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext
import logging

from user_data import UserDataManager
from weather_api import get_weather, get_weather_by_coordinates, get_extended_data
from keyboards import get_main_menu_keyboard, create_weather_keyboard, create_location_keyboard
from handlers.history import history_menu
from handlers.notifications import show_my_notifications
from utils import get_location_info, get_timezone_by_coordinates
from config import RUSSIANCITYCOORDINATES

logger = logging.getLogger(__name__)

async def handle_reply(update: Update, context: CallbackContext):
    """Обработка текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    # Обработка истории
    if text in ["📜 История", "📜 History"]:
        await history_menu(update, context)
        return
    
    # Кнопка "Назад"
    if text in ["◀️ Назад", "◀️ Back"]:
        # Назад в настройке региона БЕЗ "ГЛАВНОЕ МЕНЮ"
        if context.user_data.get('was_setting_region'):
            context.user_data.clear()  # Очищаем все флаги
            
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            if lang == "rus":
                kb = [[InlineKeyboardButton(
                    "📍 Определить автоматически",
                    callback_data="autodetect_location_request"
                )],
                [InlineKeyboardButton(
                    "⌨️ Ввести вручную",
                    callback_data="manual_set_region"
                )]]
                text_msg = "Выберите способ установки региона"
            else:
                kb = [[InlineKeyboardButton(
                    "📍 Detect automatically",
                    callback_data="autodetect_location_request"
                )],
                [InlineKeyboardButton(
                    "⌨️ Enter manually",
                    callback_data="manual_set_region"
                )]]
                text_msg = "Choose region setup method"
            
            await update.message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(kb))
            return

        # Очистка флагов
        context.user_data.clear()

        # Основная нижняя клавиатура
        main_keyboard = ReplyKeyboardMarkup(
            get_main_menu_keyboard(lang),
            resize_keyboard=True
        )

        await update.message.reply_text(
            "Главное меню" if lang == 'rus' else "Main menu",
            reply_markup=main_keyboard
        )
        return

    # /cancel
    if text.lower() == "/cancel":
        from handlers.commands import cancel
        await cancel(update, context)
        return

    # Ручная установка региона
    if context.user_data.get('setting_region') and context.user_data.get('manual_region_input'):
        city_name = text.strip()

        # Проверяем, есть ли город в нашем словаре координат
        city_lower = city_name.lower()
        if lang == 'rus' and city_lower in RUSSIANCITYCOORDINATES:
            lat, lon = RUSSIANCITYCOORDINATES[city_lower]
            weather_info, weather_text = get_weather_by_coordinates(
                lat, lon, lang,
                pressure_unit=UserDataManager.get_user_pressure_unit(context, user_id)
            )
        else:
            weather_info, weather_text = get_weather(
                city_name,
                lang,
                pressure_unit=UserDataManager.get_user_pressure_unit(context, user_id)
            )

        if weather_info:
            UserDataManager.set_user_region(context, user_id, city_name)
            context.user_data.clear()

            features = UserDataManager.get_user_features(context, user_id)

            city_name_display = weather_info['city']
            if 'lat' in weather_info and 'lon' in weather_info:
                UserDataManager.save_city_coordinates(context, user_id, city_name_display, 
                                                     weather_info['lat'], weather_info['lon'])

            from user_data import make_favorite_key
            favs_dict = UserDataManager.get_user_favorites_dict(context, user_id)
            country = weather_info.get('country', '')
            fav_key = make_favorite_key(city_name_display, country)
            city_in_favorites = fav_key in favs_dict

            keyboard = create_weather_keyboard(
                city_name_display,
                city_in_favorites,
                lang,
                show_forecast=True,
                is_current_region=True,
                lat=weather_info.get('lat'),
                lon=weather_info.get('lon'),
                country=country
            )

            main_keyboard = ReplyKeyboardMarkup(
                get_main_menu_keyboard(lang),
                resize_keyboard=True
            )

            if lang == "rus":
                await update.message.reply_text(
                    f"✅ Регион {city_name_display} установлен!\n\n{weather_text}",
                    reply_markup=main_keyboard
                )
            else:
                await update.message.reply_text(
                    f"✅ Region {city_name_display} set!\n\n{weather_text}",
                    reply_markup=main_keyboard
                )
        else:
            if lang == "rus":
                await update.message.reply_text(f"❌ Не удалось получить погоду для города '{city_name}'.")
            else:
                await update.message.reply_text(f"❌ Failed to get weather for city '{city_name}'.")
        return

    # Числовой часовой пояс
    if context.user_data.get('setting_timezone_number'):
        try:
            tz_number = int(text.strip())
            if -12 <= tz_number <= 14:
                tz_str = f"UTC+{tz_number}" if tz_number >= 0 else f"UTC{tz_number}"
                UserDataManager.set_user_timezone(context, user_id, tz_str)
                context.user_data.clear()

                if lang == "rus":
                    await update.message.reply_text(
                        f"✅ Часовой пояс установлен: {tz_str}\n🕐 Теперь восход/закат будут отображаться в правильном времени."
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Timezone set: {tz_str}\n🕐 Now sunrise/sunset will be displayed in correct time."
                    )
            else:
                if lang == "rus":
                    await update.message.reply_text(
                        "❌ Неверное число. Диапазон от -12 до +14. Попробуйте еще раз или введите /cancel.")
                else:
                    await update.message.reply_text(
                        "❌ Invalid number. Range from -12 to +14. Try again or type /cancel.")
        except ValueError:
            if lang == "rus":
                await update.message.reply_text(
                    "❌ Пожалуйста, введите целое число. Пример: 3, -5, 0, 9. Или введите /cancel для отмены.")
            else:
                await update.message.reply_text(
                    "❌ Please enter an integer number. Example: 3, -5, 0, 9. Or type /cancel to cancel.")
        return

    # Русские команды
    if lang == "rus":
        if text == "⚙️ Настройки":
            from handlers.commands import settings
            await settings(update, context)
            return
        elif text == "⭐ Избранное":
            from handlers.favorites import favorites
            await favorites(update, context)
            return
        elif text == "🌅 Погода в моем регионе":
            from handlers.weather import get_weather_for_region
            await get_weather_for_region(update, context)
            return
        elif text == "🔔 Авто-рассылка":
            from handlers.notifications import notification_settings
            await notification_settings(update, context)
            return
        elif text == "📍 Погода по геолокации":
            keyboard = create_location_keyboard(lang)
            text_msg = ("📍 Определение погоды по геолокации\n\n"
                        "Нажмите на кнопку ниже, чтобы поделиться вашим местоположением и получить прогноз погоды.")
            context.user_data['awaiting_location'] = True
            context.user_data['location_for'] = 'weather_detection'
            await update.message.reply_text(text_msg, reply_markup=keyboard)
            return
        elif text == "📜 История":
            await history_menu(update, context)
            return

    # Английские команды
    else:
        if text == "⚙️ Settings":
            from handlers.commands import settings
            await settings(update, context)
            return
        elif text == "⭐ Favorites":
            from handlers.favorites import favorites
            await favorites(update, context)
            return
        elif text == "🌅 Weather in my region":
            from handlers.weather import get_weather_for_region
            await get_weather_for_region(update, context)
            return
        elif text == "🔔 Auto-notification":
            from handlers.notifications import notification_settings
            await notification_settings(update, context)
            return
        elif text == "📍 Weather by location":
            keyboard = create_location_keyboard(lang)
            text_msg = ("📍 Weather by geolocation\n\n"
                        "Press the button below to share your location and get weather forecast.")
            context.user_data['awaiting_location'] = True
            context.user_data['location_for'] = 'weather_detection'
            await update.message.reply_text(text_msg, reply_markup=keyboard)
            return
        elif text == "📜 History":
            await history_menu(update, context)
            return

    # Обработка времени уведомлений (ЧЧ:ММ)
    if context.user_data.get('action') == 'add_notification_time':
        await handle_notification_time_input(update, context, text)
        return

    # Изменение времени уведомления
    if ':' in text and len(text) <= 5 and context.user_data.get('action') == 'change_notification_time':
        await handle_notification_time_change(update, context, text)
        return

    # Погода по названию города
    await handle_city_weather_request(update, context, text)

async def handle_notification_time_input(update: Update, context: CallbackContext, text: str):
    """Обработка ввода времени уведомления"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    if ':' in text and len(text) <= 5:
        try:
            hour_str, minute_str = text.split(':')
            hour = int(hour_str)
            minute = int(minute_str)

            if 0 <= hour <= 23 and 0 <= minute <= 59:
                if 'temp_timezone' in context.user_data:
                    timezone_str = context.user_data['temp_timezone']
                    success, result = UserDataManager.add_user_notification(context, user_id, hour, minute, timezone_str)

                    if success:
                        region = UserDataManager.get_user_region(context, user_id)
                        from utils import get_utc_offset
                        utc_offset = get_utc_offset(timezone_str)
                        context.user_data.clear()

                        if lang == 'rus':
                            await update.message.reply_text(
                                f"✅ Уведомление добавлено!\n\n"
                                f"⏰ Время: {hour:02d}:{minute:02d}\n"
                                f"📍 Регион: {region}\n"
                                f"🕐 Часовой пояс: {utc_offset}"
                            )
                        else:
                            await update.message.reply_text(
                                f"✅ Notification added!\n\n"
                                f"⏰ Time: {hour:02d}:{minute:02d}\n"
                                f"📍 Region: {region}\n"
                                f"🕐 Timezone: {utc_offset}"
                            )
                        await show_my_notifications(update, context)
                        return
                    elif result == "limit_exceeded":
                        if lang == 'rus':
                            await update.message.reply_text("❌ Достигнут лимит уведомлений (10).")
                        else:
                            await update.message.reply_text("❌ Notification limit reached (10).")
                        return
                    else:
                        await update.message.reply_text(
                            "❌ Уведомление в это время уже существует" if lang == 'rus' else "❌ Notification at this time already exists")
                        return
                else:
                    await update.message.reply_text(
                        "⚠️ Ошибка: часовой пояс не найден" if lang == 'rus' else "⚠️ Error: timezone not found")
                    return
            else:
                await update.message.reply_text(
                    "⚠️ Неверный формат времени. Используйте ЧЧ:ММ" if lang == 'rus' else "⚠️ Invalid time format. Use HH:MM")
                return
        except ValueError:
            await update.message.reply_text(
                "⚠️ Неверный формат. Используйте ЧЧ:ММ, например: 08:30" if lang == 'rus' else "⚠️ Invalid format. Use HH:MM, example: 08:30")
            return
    elif text.lower() != "/cancel":
        await update.message.reply_text(
            "⚠️ Неверный формат. Используйте ЧЧ:ММ, например: 08:30" if lang == 'rus' else "⚠️ Invalid format. Use HH:MM, example: 08:30")

async def handle_notification_time_change(update: Update, context: CallbackContext, text: str):
    """Обработка изменения времени уведомления"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    try:
        hour_str, minute_str = text.split(':')
        hour = int(hour_str)
        minute = int(minute_str)

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            notification_id = context.user_data.get('editing_notification_id')
            if notification_id:
                notifications = UserDataManager.get_user_notifications(context, user_id)
                for notification in notifications:
                    if notification['id'] == notification_id:
                        from handlers.notifications import remove_notification_job, create_notification_job
                        remove_notification_job(context, user_id, notification_id)
                        notification['hour'] = hour
                        notification['minute'] = minute
                        create_notification_job(context, user_id, notification)
                        UserDataManager.set_user_notifications(context, user_id, notifications)

                        context.user_data.clear()

                        await update.message.reply_text(
                            f"✅ Время уведомления изменено на {hour:02d}:{minute:02d}"
                            if lang == 'rus' else f"✅ Notification time changed to {hour:02d}:{minute:02d}"
                        )
                        await show_my_notifications(update, context)
                        return
                await update.message.reply_text(
                    "❌ Уведомление не найдено" if lang == 'rus' else "❌ Notification not found")
            else:
                await update.message.reply_text(
                    "❌ Ошибка: ID уведомления не найден" if lang == 'rus' else "❌ Error: notification ID not found")
        else:
            await update.message.reply_text(
                "⚠️ Неверный формат времени" if lang == 'rus' else "⚠️ Invalid time format")
        return
    except ValueError:
        pass

async def handle_city_weather_request(update: Update, context: CallbackContext, text: str):
    """Обработка запроса погоды по городу"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    show_extra_data = text.endswith('?')
    if show_extra_data:
        city_name = text[:-1].strip()
    else:
        city_name = text

    features = UserDataManager.get_user_features(context, user_id)
    timezone = UserDataManager.get_user_timezone(context, user_id)
    pressure_unit = UserDataManager.get_user_pressure_unit(context, user_id)

    if show_extra_data:
        success, extra_text, extra_data = get_extended_data(city_name, lang, features, timezone)
        if success:
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = [[InlineKeyboardButton("🌤 Показать погоду" if lang == 'rus' else "🌤 Show weather",
                                              callback_data=f"weather_{city_name}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(extra_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(extra_text)
    else:
        weather_info, weather_text = get_weather(
            city_name,
            lang,
            features,
            timezone,
            pressure_unit=pressure_unit
        )

        if weather_info:
            city_name_display = weather_info['city']
            # Добавляем город в историю поиска
            UserDataManager.add_to_history(context, user_id, city_name_display)
            
            if 'lat' in weather_info and 'lon' in weather_info:
                UserDataManager.save_city_coordinates(context, user_id, city_name_display, 
                                                     weather_info['lat'], weather_info['lon'])

            from user_data import make_favorite_key
            favs_dict = UserDataManager.get_user_favorites_dict(context, user_id)
            country = weather_info.get('country', '')
            fav_key = make_favorite_key(city_name_display, country)
            city_in_favorites = fav_key in favs_dict

            current_region = UserDataManager.get_user_region(context, user_id)
            is_current_region = (city_name_display.lower() == current_region.lower())

            keyboard = create_weather_keyboard(
                city_name_display,
                city_in_favorites,
                lang,
                show_forecast=True,
                is_current_region=is_current_region,
                lat=weather_info.get('lat'),
                lon=weather_info.get('lon'),
                country=country
            )
            await update.message.reply_text(weather_text, reply_markup=keyboard)
        else:
            await update.message.reply_text(weather_text)

async def handle_location_message(update: Update, context: CallbackContext):
    """Обработка сообщений с геолокацией"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    location_for = context.user_data.get('location_for')

    lat = update.message.location.latitude
    lon = update.message.location.longitude

    logger.info(f"Получена геолокация: {lat}, {lon} для {location_for}")

    # Запоминаем координаты в любом случае
    UserDataManager.save_city_coordinates(context, user_id, 'geolocation', lat, lon)
    
    if location_for == 'region_setup':
        await handle_region_setup_from_location(update, context, lat, lon)
    elif location_for == 'weather_detection':
        await handle_weather_from_location(update, context, lat, lon)
    elif location_for == 'timezone_setup':
        await handle_timezone_from_location(update, context, lat, lon)

async def handle_region_setup_from_location(update: Update, context: CallbackContext, lat: float, lon: float):
    """Установка региона из геолокации"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    try:
        # Получаем информацию о местоположении
        location_info = get_location_info(lat, lon)
        
        if location_info:
            address = location_info.get('address', {})
            city = address.get('city') or address.get('town') or address.get('village') or address.get('county')
            
            if not city:
                # Пробуем получить название из display_name
                display_name = location_info.get('display_name', '')
                if ',' in display_name:
                    city = display_name.split(',')[0].strip()
            
            if city:
                # Получаем погоду для этого города
                features = UserDataManager.get_user_features(context, user_id)
                timezone = UserDataManager.get_user_timezone(context, user_id)
                pressure_unit = UserDataManager.get_user_pressure_unit(context, user_id)
                
                weather_info, weather_text = get_weather_by_coordinates(
                    lat, lon, lang, features, timezone, pressure_unit=pressure_unit
                )
                
                if weather_info:
                    city_name = weather_info['city']
                    UserDataManager.set_user_region(context, user_id, city_name)
                    context.user_data.clear()

                    from user_data import make_favorite_key
                    favs_dict = UserDataManager.get_user_favorites_dict(context, user_id)
                    country = weather_info.get('country', '')
                    fav_key = make_favorite_key(city_name, country)
                    city_in_favorites = fav_key in favs_dict

                    keyboard = create_weather_keyboard(
                        city_name,
                        city_in_favorites,
                        lang,
                        show_forecast=True,
                        is_current_region=True,
                        lat=lat,
                        lon=lon,
                        country=country
                    )

                    main_keyboard = ReplyKeyboardMarkup(
                        get_main_menu_keyboard(lang),
                        resize_keyboard=True
                    )

                    if lang == "rus":
                        await update.message.reply_text(
                            f"✅ Регион {city_name} установлен!\n\n{weather_text}",
                            reply_markup=main_keyboard
                        )
                    else:
                        await update.message.reply_text(
                            f"✅ Region {city_name} set!\n\n{weather_text}",
                            reply_markup=main_keyboard
                        )
                else:
                    if lang == "rus":
                        await update.message.reply_text(f"❌ Не удалось определить город по координатам.")
                    else:
                        await update.message.reply_text(f"❌ Failed to detect city from coordinates.")
            else:
                if lang == "rus":
                    await update.message.reply_text(f"❌ Не удалось определить город по координатам.")
                else:
                    await update.message.reply_text(f"❌ Failed to detect city from coordinates.")
        else:
            if lang == "rus":
                await update.message.reply_text(f"❌ Не удалось получить информацию о местоположении.")
            else:
                await update.message.reply_text(f"❌ Failed to get location information.")
                
    except Exception as e:
        logger.error(f"Ошибка обработки геолокации: {e}")
        if lang == "rus":
            await update.message.reply_text(f"❌ Ошибка обработки местоположения.")
        else:
            await update.message.reply_text(f"❌ Error processing location.")

async def handle_weather_from_location(update: Update, context: CallbackContext, lat: float, lon: float):
    """Получение погоды из геолокации"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    try:
        features = UserDataManager.get_user_features(context, user_id)
        timezone = UserDataManager.get_user_timezone(context, user_id)
        pressure_unit = UserDataManager.get_user_pressure_unit(context, user_id)
        
        weather_info, weather_text = get_weather_by_coordinates(
            lat, lon, lang, features, timezone, pressure_unit=pressure_unit
        )
        
        if weather_info:
            city_name = weather_info['city']
            # Добавляем город в историю поиска
            UserDataManager.add_to_history(context, user_id, city_name)
            
            from user_data import make_favorite_key
            favs_dict = UserDataManager.get_user_favorites_dict(context, user_id)
            country = weather_info.get('country', '')
            fav_key = make_favorite_key(city_name, country)
            city_in_favorites = fav_key in favs_dict

            current_region = UserDataManager.get_user_region(context, user_id)
            is_current_region = (city_name.lower() == current_region.lower())

            keyboard = create_weather_keyboard(
                city_name,
                city_in_favorites,
                lang,
                show_forecast=True,
                is_current_region=is_current_region,
                lat=lat,
                lon=lon,
                country=country
            )
            
            await update.message.reply_text(weather_text, reply_markup=keyboard)
        else:
            await update.message.reply_text(weather_text)
            
    except Exception as e:
        logger.error(f"Ошибка получения погоды по геолокации: {e}")
        if lang == "rus":
            await update.message.reply_text(f"❌ Ошибка получения погоды.")
        else:
            await update.message.reply_text(f"❌ Error getting weather.")

async def handle_timezone_from_location(update: Update, context: CallbackContext, lat: float, lon: float):
    """Установка часового пояса из геолокации"""
    user_id = update.effective_user.id
    lang = UserDataManager.get_user_lang(context, user_id)
    
    try:
        tz_info = get_timezone_by_coordinates(lat, lon)
        
        if tz_info:
            timezone_str = tz_info.get('timezone', '')
            utc_offset = tz_info.get('utc_offset', '')
            
            if timezone_str:
                UserDataManager.set_user_timezone(context, user_id, timezone_str)
                context.user_data.clear()

                if lang == 'rus':
                    await update.message.reply_text(
                        f"✅ Часовой пояс установлен: {utc_offset}\n\n"
                        f"🌍 Название: {timezone_str}\n\n"
                        f"Теперь восход/закат будут показываться по этому времени."
                    )
                else:
                    await update.message.reply_text(
                        f"✅ Timezone set: {utc_offset}\n\n"
                        f"🌍 Name: {timezone_str}\n\n"
                        f"Now sunrise/sunset will be shown in this time."
                    )
            else:
                if lang == 'rus':
                    await update.message.reply_text("❌ Не удалось определить часовой пояс.")
                else:
                    await update.message.reply_text("❌ Failed to detect timezone.")
        else:
            if lang == 'rus':
                await update.message.reply_text("❌ Не удалось определить часовой пояс.")
            else:
                await update.message.reply_text("❌ Failed to detect timezone.")
                
    except Exception as e:
        logger.error(f"Ошибка определения часового пояса: {e}")
        if lang == 'rus':
            await update.message.reply_text("❌ Ошибка определения часового пояса.")
        else:
            await update.message.reply_text("❌ Error detecting timezone.")