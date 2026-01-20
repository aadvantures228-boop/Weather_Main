from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Optional

def create_weather_keyboard(city_name: str, in_favorites: bool, lang: str,
                           show_forecast: bool = True, is_current_region: bool = False,
                           lat: float = None, lon: float = None, country: str = "") -> InlineKeyboardMarkup:
    """Создание клавиатуры для погоды с динамическими кнопками"""
    keyboard = []
    
    # Кнопка избранного и установки региона в одном ряду
    region_row = []
    
    # Кнопка избранного
    if in_favorites:
        region_row.append(InlineKeyboardButton(
            "❌ Удалить из избранного" if lang == "rus" else "❌ Remove from favorites",
            callback_data=f"remove_favorite:{city_name}:{country}"
        ))
    else:
        region_row.append(InlineKeyboardButton(
            "⭐ Добавить в избранное" if lang == "rus" else "⭐ Add to favorites",
            callback_data=f"add_favorite:{city_name}:{country}"
        ))
    
    # Кнопка "Сделать моим регионом" только если не текущий регион
    if not is_current_region and lat is not None and lon is not None:
        region_row.append(InlineKeyboardButton(
            "🌍 Сделать моим регионом" if lang == "rus" else "🌍 Set as my region",
            callback_data=f"confirm_region:{city_name}:{lat},{lon}"
        ))
    
    if region_row:
        keyboard.append(region_row)

    # ✅ Прогноз + Доп. данные (всегда, если координаты есть)
    if lat is not None and lon is not None:
        forecast_row = []
        if show_forecast:
            forecast_row.append(InlineKeyboardButton(
                "📅 Прогноз на 5 дней" if lang == "rus" else "📅 5-Day Forecast",
                callback_data=f"week_forecast:{city_name}|{lat},{lon}"
            ))
        forecast_row.append(InlineKeyboardButton(
            "📊 Доп. данные" if lang == "rus" else "📊 Extra Data",
            callback_data=f"extra_data:{city_name}|{lat},{lon}"
        ))
        if forecast_row:
            keyboard.append(forecast_row)
    else:
        # Если координат нет, используем только название города
        forecast_row = []
        if show_forecast:
            forecast_row.append(InlineKeyboardButton(
                "📅 Прогноз на 5 дней" if lang == "rus" else "📅 5-Day Forecast",
                callback_data=f"week_forecast:{city_name}"
            ))
        forecast_row.append(InlineKeyboardButton(
            "📊 Доп. данные" if lang == "rus" else "📊 Extra Data",
            callback_data=f"extra_data:{city_name}"
        ))
        if forecast_row:
            keyboard.append(forecast_row)

    # Поделиться + Назад
    keyboard.append([InlineKeyboardButton(
        "📤 Поделиться" if lang == "rus" else "📤 Share",
        callback_data=f"share_weather:{city_name}"
    )])
    keyboard.append([InlineKeyboardButton(
        "◀️ Назад" if lang == "rus" else "◀️ Back",
        callback_data="favorites_back"
    )])

    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard(lang: str) -> List[List[str]]:
    """Возвращает основную клавиатуру меню"""
    if lang == 'rus':
        return [
            ["⚙️ Настройки", "⭐ Избранное"],
            ["🌅 Погода в моем регионе", "🔔 Авто-рассылка"],
            ["📍 Погода по геолокации", "📜 История"]
        ]
    else:
        return [
            ["⚙️ Settings", "⭐ Favorites"],
            ["🌅 Weather in my region", "🔔 Auto-notification"],
            ["📍 Weather by location", "📜 History"]
        ]

def create_location_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Создать клавиатуру для запроса местоположения"""
    if lang == 'rus':
        keyboard = [
            [KeyboardButton("📍 Отправить местоположение", request_location=True)],
            [KeyboardButton("◀️ Назад")]
        ]
    else:
        keyboard = [
            [KeyboardButton("📍 Send location", request_location=True)],
            [KeyboardButton("◀️ Back")]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def create_settings_keyboard(lang: str, region: str, features: dict = None) -> InlineKeyboardMarkup:
    """Создать клавиатуру настроек"""
    if lang == 'rus':
        keyboard = [
            [InlineKeyboardButton(f"🌐 Язык: Русский", callback_data="language")],
            [InlineKeyboardButton(f"🏙 Мой регион: {region}", callback_data="change_region")],
            [InlineKeyboardButton(f"🕐 Часовой пояс", callback_data="change_timezone")],
            [InlineKeyboardButton(f"🔽 Давление", callback_data="pressure_settings")],
            [InlineKeyboardButton(f"⚙️ Дополнительные функции", callback_data="extra_features")],
            [InlineKeyboardButton(f"🤝 Партнёры", callback_data="partners")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(f"🌐 Language: English", callback_data="language")],
            [InlineKeyboardButton(f"🏙 My region: {region}", callback_data="change_region")],
            [InlineKeyboardButton(f"🕐 Timezone", callback_data="change_timezone")],
            [InlineKeyboardButton(f"🔽 Pressure", callback_data="pressure_settings")],
            [InlineKeyboardButton(f"⚙️ Extra Features", callback_data="extra_features")],
            [InlineKeyboardButton(f"🤝 Partners", callback_data="partners")],
        ]
    
    return InlineKeyboardMarkup(keyboard)

def create_language_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру выбора языка"""
    if lang == 'rus':
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings_back")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("◀️ Back", callback_data="settings_back")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def create_timezone_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру выбора часового пояса"""
    if lang == 'rus':
        text = "🕐 Выбор часового пояса\n\n"
        text += "Часовой пояс используется для отображения времени восхода/заката."
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Москва (UTC+3)", callback_data="tz_user_mos")],
            [InlineKeyboardButton("🇬🇧 Лондон (UTC+0)", callback_data="tz_user_lon")],
            [InlineKeyboardButton("🇺🇸 Нью-Йорк (UTC-5)", callback_data="tz_user_ny")],
            [InlineKeyboardButton("🇯🇵 Токио (UTC+9)", callback_data="tz_user_tok")],
            [InlineKeyboardButton("🇦🇺 Сидней (UTC+10)", callback_data="tz_user_sid")],
            [InlineKeyboardButton("🇦🇪 Дубай (UTC+4)", callback_data="tz_user_dub")],
            [InlineKeyboardButton("🔢 Ввести число вручную", callback_data="manual_timezone_number")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings_back")]
        ]
    else:
        text = "🕐 Timezone selection\n\n"
        text += "Timezone is used to display sunrise/sunset time."
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Moscow (UTC+3)", callback_data="tz_user_mos")],
            [InlineKeyboardButton("🇬🇧 London (UTC+0)", callback_data="tz_user_lon")],
            [InlineKeyboardButton("🇺🇸 New York (UTC-5)", callback_data="tz_user_ny")],
            [InlineKeyboardButton("🇯🇵 Tokyo (UTC+9)", callback_data="tz_user_tok")],
            [InlineKeyboardButton("🇦🇺 Sydney (UTC+10)", callback_data="tz_user_sid")],
            [InlineKeyboardButton("🇦🇪 Dubai (UTC+4)", callback_data="tz_user_dub")],
            [InlineKeyboardButton("🔢 Enter number manually", callback_data="manual_timezone_number")],
            [InlineKeyboardButton("◀️ Back", callback_data="settings_back")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def create_region_setup_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру настройки региона"""
    if lang == 'rus':
        keyboard = [
            [InlineKeyboardButton("📍 Определить автоматически", callback_data="autodetect_region")],
            [InlineKeyboardButton("✍️ Ввести вручную", callback_data="manual_set_region")],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings_back")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("📍 Detect automatically", callback_data="autodetect_region")],
            [InlineKeyboardButton("✍️ Enter manually", callback_data="manual_set_region")],
            [InlineKeyboardButton("◀️ Back", callback_data="settings_back")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def create_pressure_settings_keyboard(lang: str, current_unit: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру настроек давления"""
    if lang == "rus":
        mm_label = "✅ мм рт. ст." if current_unit == "mmhg" else "❌ мм рт. ст."
        hpa_label = "✅ гПа" if current_unit == "hpa" else "❌ гПа"
        back = "◀️ Назад"
    else:
        mm_label = "✅ mmHg" if current_unit == "mmhg" else "❌ mmHg"
        hpa_label = "✅ hPa" if current_unit == "hpa" else "❌ hPa"
        back = "◀️ Back"

    keyboard = [
        [
            InlineKeyboardButton(mm_label, callback_data="pressure_mm"),
            InlineKeyboardButton(hpa_label, callback_data="pressure_hpa"),
        ],
        [InlineKeyboardButton(back, callback_data="settings_back")],
    ]

    return InlineKeyboardMarkup(keyboard)

def create_extra_features_keyboard(lang: str, features: dict) -> InlineKeyboardMarkup:
    """Создать клавиатуру дополнительных функций"""
    if lang == 'rus':
        keyboard = [
            [InlineKeyboardButton(
                f"{'✅' if features['cloudiness'] else '❌'} ☁️ Облачность", 
                callback_data="toggle_cloudiness"
            )],
            [InlineKeyboardButton(
                f"{'✅' if features['wind_direction'] else '❌'} 🧭 Направление ветра", 
                callback_data="toggle_wind_direction"
            )],
            [InlineKeyboardButton(
                f"{'✅' if features['wind_gust'] else '❌'} 💨 Порывы ветра", 
                callback_data="toggle_wind_gust"
            )],
            [InlineKeyboardButton(
                f"{'✅' if features['sunrise_sunset'] else '❌'} 🌅 Восход/закат", 
                callback_data="toggle_sunrise_sunset"
            )],
            [InlineKeyboardButton("◀️ Назад", callback_data="settings_back")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(
                f"{'✅' if features['cloudiness'] else '❌'} ☁️ Cloudiness", 
                callback_data="toggle_cloudiness"
            )],
            [InlineKeyboardButton(
                f"{'✅' if features['wind_direction'] else '❌'} 🧭 Wind direction", 
                callback_data="toggle_wind_direction"
            )],
            [InlineKeyboardButton(
                f"{'✅' if features['wind_gust'] else '❌'} 💨 Wind gusts", 
                callback_data="toggle_wind_gust"
            )],
            [InlineKeyboardButton(
                f"{'✅' if features['sunrise_sunset'] else '❌'} 🌅 Sunrise/Sunset", 
                callback_data="toggle_sunrise_sunset"
            )],
            [InlineKeyboardButton("◀️ Back", callback_data="settings_back")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def create_favorites_keyboard(lang: str, favorites_dict: dict) -> InlineKeyboardMarkup:
    """Создать клавиатуру избранного"""
    keyboard = []
    for key, city in favorites_dict.items():
        city_name = city
        country = key.split("|", 1)[1] if "|" in key else ""
        fav_payload = f"{city_name}|{country}" if country else city_name

        keyboard.append([
            InlineKeyboardButton(f"🌤 {city_name}", callback_data=f"fav_{city_name}"),
            InlineKeyboardButton("❌", callback_data=f"remove_favorite:{fav_payload}"),
        ])

    if favorites_dict:
        keyboard.append([InlineKeyboardButton("🗑 Очистить всё" if lang == 'rus' else "🗑 Clear all",
                                              callback_data="clear_favorites")])
    
    return InlineKeyboardMarkup(keyboard)

def create_notification_time_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру выбора времени уведомления"""
    if lang == 'rus':
        keyboard = [
            [
                InlineKeyboardButton("🌅 09:00 (утро)", callback_data="time_add_90"),
                InlineKeyboardButton("☀️ 12:00 (день)", callback_data="time_add_120")
            ],
            [
                InlineKeyboardButton("🌆 18:00 (вечер)", callback_data="time_add_180"),
                InlineKeyboardButton("🌃 21:00 (ночь)", callback_data="time_add_210")
            ],
            [
                InlineKeyboardButton("⏰ 08:00", callback_data="time_add_80"),
                InlineKeyboardButton("⏰ 14:00", callback_data="time_add_140"),
                InlineKeyboardButton("⏰ 20:00", callback_data="time_add_200")
            ],
            [InlineKeyboardButton("✍️ Ввести своё время", callback_data="time_add_manual")],
            [InlineKeyboardButton("◀️ Назад", callback_data="add_notification_step1")]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("🌅 09:00 (morning)", callback_data="time_add_90"),
                InlineKeyboardButton("☀️ 12:00 (day)", callback_data="time_add_120")
            ],
            [
                InlineKeyboardButton("🌆 18:00 (evening)", callback_data="time_add_180"),
                InlineKeyboardButton("🌃 21:00 (night)", callback_data="time_add_210")
            ],
            [
                InlineKeyboardButton("⏰ 08:00", callback_data="time_add_80"),
                InlineKeyboardButton("⏰ 14:00", callback_data="time_add_140"),
                InlineKeyboardButton("⏰ 20:00", callback_data="time_add_200")
            ],
            [InlineKeyboardButton("✍️ Enter custom time", callback_data="time_add_manual")],
            [InlineKeyboardButton("◀️ Back", callback_data="add_notification_step1")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def create_forecast_keyboard(lang: str, city_name: str) -> InlineKeyboardMarkup:
    """Создать клавиатуру для прогноза погоды"""
    if lang == 'rus':
        days_of_week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    else:
        days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    from datetime import datetime, timedelta
    now = datetime.now()
    keyboard = []

    for i in range(5):
        forecast_date = now + timedelta(days=i)
        day_num = forecast_date.day
        month_num = forecast_date.month

        if lang == 'rus':
            if i == 0:
                day_name = "Сегодня"
            elif i == 1:
                day_name = "Завтра"
            else:
                day_name = days_of_week[forecast_date.weekday()]
        else:
            if i == 0:
                day_name = "Today"
            elif i == 1:
                day_name = "Tomorrow"
            else:
                day_name = days_of_week[forecast_date.weekday()]

        button_text = f"{day_name}, {day_num}.{month_num:02d}"

        if i % 2 == 0:
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"day_forecast_{city_name}_{i}")])
        else:
            keyboard[-1].append(InlineKeyboardButton(button_text, callback_data=f"day_forecast_{city_name}_{i}"))

    keyboard.append([InlineKeyboardButton("◀️ Назад к погоде" if lang == 'rus' else "◀️ Back to weather",
                                          callback_data=f"weather:{city_name}")])

    return InlineKeyboardMarkup(keyboard)