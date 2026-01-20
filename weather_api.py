import requests
import functools
from datetime import datetime, timedelta
import logging
from typing import Dict, Tuple, Optional
import pytz

from config import WEATHER_TOKEN, OPENSTREETMAP_URL, RUSSIANCITYCOORDINATES, WEATHER_CACHE_TTL_MINUTES
from utils import get_timezone_by_coordinates, calculate_timezone_by_longitude, get_location_info, get_utc_offset

logger = logging.getLogger(__name__)

def cache_weather(ttl_minutes=10):
    """Декоратор для кэширования погоды"""
    cache = {}

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            city = kwargs.get('city') or (args[0] if args else None)
            lang = kwargs.get('lang', 'ru')

            if city:
                key = f"{city.lower()}_{lang}"

                if key in cache:
                    cached_time, data = cache[key]
                    if datetime.now() - cached_time < timedelta(minutes=ttl_minutes):
                        return data

            result = func(*args, **kwargs)
            if city:
                cache[key] = (datetime.now(), result)
            return result

        return wrapper

    return decorator

def normalize_city_name_for_russian(city_name: str, lang: str) -> str:
    """Нормализация названия города для русского языка"""
    if lang != 'rus':
        return city_name

    city_lower = city_name.lower().strip()
    if city_lower in RUSSIANCITYCOORDINATES:
        # Возвращаем правильное название с заглавной буквы
        for key in RUSSIANCITYCOORDINATES:
            if key.lower() == city_lower:
                return key.title()

    return city_name

@cache_weather(ttl_minutes=WEATHER_CACHE_TTL_MINUTES)
def get_weather(
        city: str,
        lang: str = "ru",
        user_features: dict = None,
        user_timezone: str = None,
        save_coords: bool = True,
        pressure_unit: str | None = None
) -> tuple:
    """Получение погоды с сохранением координат и нормализацией русских городов"""
    try:
        # Нормализуем название для русского языка
        normalized_city = normalize_city_name_for_russian(city, lang)

        # Проверяем, есть ли город в нашем словаре координат
        city_lower = normalized_city.lower()
        if lang == 'rus' and city_lower in RUSSIANCITYCOORDINATES:
            lat, lon = RUSSIANCITYCOORDINATES[city_lower]
            # Используем координаты из словаря
            return get_weather_by_coordinates(
                lat, lon, lang, user_features, user_timezone, pressure_unit
            )

        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'q': normalized_city,
            'appid': WEATHER_TOKEN,
            'units': 'metric',
            'lang': 'ru' if lang == 'rus' else 'en'
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 404:
            return None, f"🌍 Город {city} не найден" if lang == 'rus' else f"🌍 City {city} not found"
        elif response.status_code != 200:
            return None, f"⚠️ Ошибка: код {response.status_code}" if lang == 'rus' else f"⚠️ Error: code {response.status_code}"

        data = response.json()

        lat = data['coord']['lat']
        lon = data['coord']['lon']
        city_name = data['name']

        # Нормализация названия для русских городов
        city_name = normalize_city_name_for_russian(city_name, lang)

        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        pressure_hpa = data['main']['pressure']
        wind_speed = data['wind']['speed']
        desc = data['weather'][0]['description']

        # Давление с учётом настроек пользователя
        if pressure_unit is None:
            pressure_unit = "mmhg" if lang == "rus" else "hpa"

        if pressure_unit == "mmhg":
            pressure_mmhg = round(pressure_hpa * 0.750062)
            pressure_display = f"{pressure_mmhg} мм рт. ст." if lang == "rus" else f"{pressure_mmhg} mmHg"
        else:
            pressure_display = f"{pressure_hpa} гПа" if lang == "rus" else f"{pressure_hpa} hPa"

        weather_info = {
            'city': city_name,
            'temp': temp,
            'feels_like': feels_like,
            'humidity': humidity,
            'pressure_hpa': pressure_hpa,
            'wind_speed': wind_speed,
            'desc': desc,
            'lat': lat,
            'lon': lon,
            'country': data.get('sys', {}).get('country', '')
        }

        # Формирование текста с дополнительными функциями
        if lang == 'rus':
            text = (f"🌤 Погода в городе {city_name}:\n\n"
                    f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    f"📖 Описание: {desc}\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"🔽 Давление: {pressure_display}\n"
                    f"💨 Скорость ветра: {wind_speed} м/с")

            if user_features:
                extended_text = "\n\n📊 Дополнительные данные:"

                if user_features.get('cloudiness', False):
                    clouds = data['clouds'].get('all', 'Н/Д')
                    extended_text += f"\n☁️ Облачность: {clouds}%"

                if user_features.get('wind_direction', False):
                    wind_deg = data['wind'].get('deg')
                    if wind_deg:
                        directions = ["⬆️ Северный", "↗️ Северо-восточный", "➡️ Восточный", "↘️ Юго-восточный",
                                      "⬇️ Южный", "↙️ Юго-западный", "⬅️ Западный", "↖️ Северо-западный"]
                        idx = round(wind_deg / 45) % 8
                        extended_text += f"\n🧭 Направление ветра: {directions[idx]}"

                if user_features.get('wind_gust', False):
                    wind_gust = data['wind'].get('gust')
                    if wind_gust:
                        extended_text += f"\n💨 Порывы ветра: {wind_gust} м/с"

                if user_features.get('sunrise_sunset', False):
                    sunrise = datetime.fromtimestamp(data['sys']['sunrise'])
                    sunset = datetime.fromtimestamp(data['sys']['sunset'])

                    try:
                        location_info = get_location_info(lat, lon)
                        if location_info:
                            tz_info = get_timezone_by_coordinates(lat, lon, location_info)
                            city_timezone = tz_info.get('timezone', '') if tz_info else ''
                        else:
                            tz_calc = calculate_timezone_by_longitude(lon)
                            city_timezone = tz_calc.get('timezone', '')

                        if city_timezone:
                            if city_timezone.startswith('UTC'):
                                offset_str = city_timezone.replace('UTC', '').strip()
                                offset_hours = float(offset_str) if offset_str else 0
                                sunrise_local = sunrise + timedelta(hours=offset_hours)
                                sunset_local = sunset + timedelta(hours=offset_hours)
                            else:
                                tz_name = city_timezone.split('(')[0].strip()
                                city_tz = pytz.timezone(tz_name)
                                sunrise_local = pytz.UTC.localize(sunrise).astimezone(city_tz)
                                sunset_local = pytz.UTC.localize(sunset).astimezone(city_tz)

                            sunrise_str = sunrise_local.strftime('%H:%M')
                            sunset_str = sunset_local.strftime('%H:%M')
                        else:
                            sunrise_str = sunrise.strftime('%H:%M')
                            sunset_str = sunset.strftime('%H:%M')
                    except Exception as e:
                        logger.error(f"Ошибка определения времени города: {e}")
                        sunrise_str = sunrise.strftime('%H:%M')
                        sunset_str = sunset.strftime('%H:%M')

                    extended_text += f"\n🌅 Восход солнца: {sunrise_str}\n🌇 Закат солнца: {sunset_str}"

                if extended_text != "\n\n📊 Дополнительные данные:":
                    text += extended_text
        else:
            text = (f"🌤 Weather in {city_name}:\n\n"
                    f"🌡 Temperature: {temp}°C (feels like {feels_like}°C)\n"
                    f"📖 Description: {desc}\n"
                    f"💧 Humidity: {humidity}%\n"
                    f"🔽 Pressure: {pressure_display}\n"
                    f"💨 Wind speed: {wind_speed} m/s")

            if user_features:
                extended_text = "\n\n📊 Additional data:"

                if user_features.get('cloudiness', False):
                    clouds = data['clouds'].get('all', 'N/A')
                    extended_text += f"\n☁️ Cloudiness: {clouds}%"

                if user_features.get('wind_direction', False):
                    wind_deg = data['wind'].get('deg')
                    if wind_deg:
                        directions = ["⬆️ North", "↗️ Northeast", "➡️ East", "↘️ Southeast",
                                      "⬇️ South", "↙️ Southwest", "⬅️ West", "↖️ Northwest"]
                        idx = round(wind_deg / 45) % 8
                        extended_text += f"\n🧭 Wind direction: {directions[idx]}"

                if user_features.get('wind_gust', False):
                    wind_gust = data['wind'].get('gust')
                    if wind_gust:
                        extended_text += f"\n💨 Wind gust: {wind_gust} m/s"

                if user_features.get('sunrise_sunset', False):
                    sunrise = datetime.fromtimestamp(data['sys']['sunrise'])
                    sunset = datetime.fromtimestamp(data['sys']['sunset'])
                    sunrise_str = sunrise.strftime('%H:%M')
                    sunset_str = sunset.strftime('%H:%M')
                    extended_text += f"\n🌅 Sunrise: {sunrise_str}\n🌇 Sunset: {sunset_str}"

                if extended_text != "\n\n📊 Additional data:":
                    text += extended_text

        return weather_info, text

    except Exception as e:
        logger.error(f"Ошибка get_weather: {e}")
        return None, f'❌ Ошибка: {e}' if lang == 'rus' else f'❌ Error: {e}'

def get_weather_by_coordinates(
        lat: float,
        lon: float,
        lang: str = "ru",
        user_features: dict = None,
        user_timezone: str = None,
        pressure_unit: str | None = None
):
    """Получение погоды по координатам"""
    try:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'lat': lat,
            'lon': lon,
            'appid': WEATHER_TOKEN,
            'units': 'metric',
            'lang': 'ru' if lang == 'rus' else 'en'
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None, f"⚠️ Ошибка получения погоды" if lang == 'rus' else f"⚠️ Error getting weather"

        data = response.json()
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        pressure_hpa = data['main']['pressure']
        wind_speed = data['wind']['speed']
        desc = data['weather'][0]['description']
        city_name = data['name']

        # Нормализация для русских городов
        city_name = normalize_city_name_for_russian(city_name, lang)

        # Выбор единиц давления
        if pressure_unit is None:
            pressure_unit = "mmhg" if lang == "rus" else "hpa"

        if pressure_unit == "mmhg":
            pressure_mmhg = round(pressure_hpa * 0.750062)
            pressure_display = f"{pressure_mmhg} мм рт. ст." if lang == "rus" else f"{pressure_mmhg} mmHg"
        else:
            pressure_display = f"{pressure_hpa} гПа" if lang == "rus" else f"{pressure_hpa} hPa"

        weather_info = {
            'city': city_name,
            'temp': temp,
            'feels_like': feels_like,
            'humidity': humidity,
            'pressure_hpa': pressure_hpa,
            'wind_speed': wind_speed,
            'desc': desc,
            'lat': lat,
            'lon': lon,
            'country': data.get('sys', {}).get('country', '')
        }

        if lang == 'rus':
            text = (f"🌤 Погода в городе {city_name}:\n\n"
                    f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    f"📖 Описание: {desc}\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"🔽 Давление: {pressure_display}\n"
                    f"💨 Скорость ветра: {wind_speed} м/с")

            if user_features:
                extended_text = "\n\n📊 Дополнительные данные:"

                if user_features.get('cloudiness', False):
                    clouds = data['clouds'].get('all', 'Н/Д')
                    extended_text += f"\n☁️ Облачность: {clouds}%"

                if user_features.get('wind_direction', False):
                    wind_deg = data['wind'].get('deg')
                    if wind_deg:
                        directions = ["⬆️ Северный", "↗️ Северо-восточный", "➡️ Восточный", "↘️ Юго-восточный",
                                      "⬇️ Южный", "↙️ Юго-западный", "⬅️ Западный", "↖️ Северо-западный"]
                        idx = round(wind_deg / 45) % 8
                        extended_text += f"\n🧭 Направление ветра: {directions[idx]}"

                if user_features.get('wind_gust', False):
                    wind_gust = data['wind'].get('gust')
                    if wind_gust:
                        extended_text += f"\n💨 Порывы ветра: {wind_gust} м/с"

                if user_features.get('sunrise_sunset', False):
                    sunrise = datetime.fromtimestamp(data['sys']['sunrise'])
                    sunset = datetime.fromtimestamp(data['sys']['sunset'])

                    try:
                        location_info = get_location_info(lat, lon)

                        if location_info:
                            tz_info = get_timezone_by_coordinates(lat, lon, location_info)
                            city_timezone = tz_info.get('timezone', '') if tz_info else ''
                        else:
                            tz_calc = calculate_timezone_by_longitude(lon)
                            city_timezone = tz_calc.get('timezone', '')

                        if city_timezone:
                            if city_timezone.startswith('UTC'):
                                offset_str = city_timezone.replace('UTC', '').strip()
                                if offset_str.startswith('+') or offset_str.startswith('-'):
                                    offset_hours = float(offset_str)
                                else:
                                    offset_hours = float(offset_str) if offset_str else 0

                                sunrise_local = sunrise + timedelta(hours=offset_hours)
                                sunset_local = sunset + timedelta(hours=offset_hours)
                            else:
                                tz_name = city_timezone.split('(')[0].strip()
                                city_tz = pytz.timezone(tz_name)
                                sunrise_local = pytz.UTC.localize(sunrise).astimezone(city_tz)
                                sunset_local = pytz.UTC.localize(sunset).astimezone(city_tz)

                            sunrise_str = sunrise_local.strftime('%H:%M')
                            sunset_str = sunset_local.strftime('%H:%M')
                        else:
                            sunrise_str = sunrise.strftime('%H:%M')
                            sunset_str = sunset.strftime('%H:%M')
                    except Exception as e:
                        logger.error(f"Ошибка конвертации времени: {e}")
                        sunrise_str = sunrise.strftime('%H:%M')
                        sunset_str = sunset.strftime('%H:%M')

                    extended_text += f"\n🌅 Восход солнца: {sunrise_str}\n🌇 Закат солнца: {sunset_str}"

                if extended_text != "\n\n📊 Дополнительные данные:":
                    text += extended_text
        else:
            text = (f"🌤 Weather in {city_name}:\n\n"
                    f"🌡 Temperature: {temp}°C (feels like {feels_like}°C)\n"
                    f"📖 Description: {desc}\n"
                    f"💧 Humidity: {humidity}%\n"
                    f"🔽 Pressure: {pressure_display}\n"
                    f"💨 Wind speed: {wind_speed} m/s")

            if user_features:
                extended_text = "\n\n📊 Additional data:"

                if user_features.get('cloudiness', False):
                    clouds = data['clouds'].get('all', 'N/A')
                    extended_text += f"\n☁️ Cloudiness: {clouds}%"

                if user_features.get('wind_direction', False):
                    wind_deg = data['wind'].get('deg')
                    if wind_deg:
                        directions = ["⬆️ North", "↗️ Northeast", "➡️ East", "↘️ Southeast",
                                      "⬇️ South", "↙️ Southwest", "⬅️ West", "↖️ Northwest"]
                        idx = round(wind_deg / 45) % 8
                        extended_text += f"\n🧭 Wind direction: {directions[idx]}"

                if user_features.get('wind_gust', False):
                    wind_gust = data['wind'].get('gust')
                    if wind_gust:
                        extended_text += f"\n💨 Wind gust: {wind_gust} m/s"

                if user_features.get('sunrise_sunset', False):
                    sunrise = datetime.fromtimestamp(data['sys']['sunrise'])
                    sunset = datetime.fromtimestamp(data['sys']['sunset'])

                    try:
                        location_info = get_location_info(lat, lon)

                        if location_info:
                            tz_info = get_timezone_by_coordinates(lat, lon, location_info)
                            city_timezone = tz_info.get('timezone', '') if tz_info else ''
                        else:
                            tz_calc = calculate_timezone_by_longitude(lon)
                            city_timezone = tz_calc.get('timezone', '')

                        if city_timezone:
                            if city_timezone.startswith('UTC'):
                                offset_str = city_timezone.replace('UTC', '').strip()
                                if offset_str.startswith('+') or offset_str.startswith('-'):
                                    offset_hours = float(offset_str)
                                else:
                                    offset_hours = float(offset_str) if offset_str else 0

                                sunrise_local = sunrise + timedelta(hours=offset_hours)
                                sunset_local = sunset + timedelta(hours=offset_hours)
                            else:
                                tz_name = city_timezone.split('(')[0].strip()
                                city_tz = pytz.timezone(tz_name)
                                sunrise_local = pytz.UTC.localize(sunrise).astimezone(city_tz)
                                sunset_local = pytz.UTC.localize(sunset).astimezone(city_tz)

                            sunrise_str = sunrise_local.strftime('%H:%M')
                            sunset_str = sunset_local.strftime('%H:%M')
                        else:
                            sunrise_str = sunrise.strftime('%H:%M')
                            sunset_str = sunset.strftime('%H:%M')
                    except Exception as e:
                        logger.error(f"Ошибка конвертации: {e}")
                        sunrise_str = sunrise.strftime('%H:%M')
                        sunset_str = sunset.strftime('%H:%M')

                    extended_text += f"\n🌅 Sunrise: {sunrise_str}\n🌇 Sunset: {sunset_str}"

                if extended_text != "\n\n📊 Additional data:":
                    text += extended_text

        return weather_info, text

    except Exception as e:
        logger.error(f"Ошибка получения погоды по координатам: {e}")
        return None, f'❌ Ошибка: {e}' if lang == 'rus' else f'❌ Error: {e}'

def get_forecast(city: str, lang: str = "ru"):
    """Получение прогноза погоды"""
    try:
        url = 'https://api.openweathermap.org/data/2.5/forecast'
        params = {
            'q': city,
            'appid': WEATHER_TOKEN,
            'units': 'metric',
            'lang': 'ru' if lang == 'rus' else 'en',
            'cnt': 40
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 404:
            return None, None, f"Город {city} не найден" if lang == 'rus' else f"City {city} not found"
        elif response.status_code != 200:
            return None, None, f"Ошибка: код {response.status_code}" if lang == 'rus' else f"Error: code {response.status_code}"

        data = response.json()
        city_name = data['city']['name']
        forecast_list = data['list']

        return city_name, forecast_list, None

    except Exception as e:
        return None, None, f'Ошибка: {e}' if lang == 'rus' else f'Error: {e}'

def get_daily_forecast(forecast_list, day_offset: int = 0):
    """Получение дневного прогноза"""
    if not forecast_list:
        return None

    target_date = (datetime.now() + timedelta(days=day_offset)).date()
    day_forecasts = []

    for forecast in forecast_list:
        forecast_dt = datetime.fromtimestamp(forecast['dt'])
        if forecast_dt.date() == target_date:
            day_forecasts.append(forecast)

    if not day_forecasts:
        return None

    temps = [f['main']['temp'] for f in day_forecasts]
    feels_like = [f['main']['feels_like'] for f in day_forecasts]
    humidities = [f['main']['humidity'] for f in day_forecasts]

    day_forecast = None
    for forecast in day_forecasts:
        hour = datetime.fromtimestamp(forecast['dt']).hour
        if 12 <= hour <= 15:
            day_forecast = forecast
            break

    if not day_forecast:
        day_forecast = day_forecasts[0]

    return {
        'date': target_date,
        'temp_min': min(temps),
        'temp_max': max(temps),
        'temp_day': day_forecast['main']['temp'],
        'feels_like': day_forecast['main']['feels_like'],
        'humidity': day_forecast['main']['humidity'],
        'pressure': day_forecast['main']['pressure'],
        'wind_speed': day_forecast['wind']['speed'],
        'description': day_forecast['weather'][0]['description'],
        'icon': day_forecast['weather'][0]['icon']
    }

def get_extended_data(city: str, lang: str = "ru", features: dict = None, user_timezone: str = None) -> tuple:
    """Получение расширенных данных о городе"""
    try:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'q': city,
            'appid': WEATHER_TOKEN,
            'units': 'metric',
            'lang': 'ru' if lang == 'rus' else 'en'
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 404:
            return False, f"Город {city} не найден" if lang == 'rus' else f"City {city} not found", None
        elif response.status_code != 200:
            return False, f"Ошибка: код {response.status_code}" if lang == 'rus' else f"Error: code {response.status_code}", None

        data = response.json()
        
        lat = data['coord']['lat']
        lon = data['coord']['lon']
        city_name = data['name']
        country = data.get('sys', {}).get('country', '')

        # Нормализация названия
        city_name = normalize_city_name_for_russian(city_name, lang)

        # Получаем часовой пояс
        location_info = get_location_info(lat, lon)
        if location_info:
            tz_info = get_timezone_by_coordinates(lat, lon, location_info)
            city_timezone = tz_info.get('utc_offset', 'UTC+0') if tz_info else 'UTC+0'
        else:
            tz_calc = calculate_timezone_by_longitude(lon)
            city_timezone = tz_calc.get('utc_offset', 'UTC+0')

        extended_data = {
            'city': city_name,
            'country': country,
            'lat': lat,
            'lon': lon,
            'timezone': city_timezone
        }

        # Формируем текст
        if lang == 'rus':
            text = f"📊 Дополнительные данные о городе {city_name}\n\n"
            text += f"🏙 Город: {city_name}\n"
            text += f"🌍 Страна: {country}\n"
            text += f"📍 Координаты: {lat:.4f}, {lon:.4f}\n"
            text += f"🕐 Часовой пояс города: {city_timezone}\n"

            if features and features.get('sunrise_sunset', False):
                sunrise = datetime.fromtimestamp(data['sys']['sunrise'])
                sunset = datetime.fromtimestamp(data['sys']['sunset'])

                try:
                    if user_timezone and user_timezone.startswith('UTC'):
                        offset_str = user_timezone.replace('UTC', '').strip()
                        if offset_str.startswith('+') or offset_str.startswith('-'):
                            offset_hours = float(offset_str)
                        else:
                            offset_hours = float(offset_str) if offset_str else 0

                        sunrise_user = sunrise + timedelta(hours=offset_hours)
                        sunset_user = sunset + timedelta(hours=offset_hours)
                        now_user = datetime.utcnow() + timedelta(hours=offset_hours)

                        sunrise_str = sunrise_user.strftime('%H:%M')
                        sunset_str = sunset_user.strftime('%H:%M')
                        local_time_str = now_user.strftime('%H:%M:%S')
                    else:
                        sunrise_str = sunrise.strftime('%H:%M')
                        sunset_str = sunset.strftime('%H:%M')
                        local_time_str = datetime.utcnow().strftime('%H:%M:%S')

                    text += f"\n📅 Время восхода и заката (ваш часовой пояс: {user_timezone or 'UTC+0'}):\n"
                    text += f"🌅 Восход солнца: {sunrise_str}\n"
                    text += f"🌇 Закат солнца: {sunset_str}\n"
                    text += f"🕐 Текущее время: {local_time_str}\n"
                except Exception as e:
                    logger.error(f"Ошибка конвертации для пользователя: {e}")
                    text += f"\n⚠️ Ошибка отображения времени"
            else:
                text += f"\n⚠️ Включите функцию 'Восход/закат' в настройках дополнительных функций."
        else:
            text = f"📊 Extended data for {city_name}\n\n"
            text += f"🏙 City: {city_name}\n"
            text += f"🌍 Country: {country}\n"
            text += f"📍 Coordinates: {lat:.4f}, {lon:.4f}\n"
            text += f"🕐 City timezone: {city_timezone}\n"

            if features and features.get('sunrise_sunset', False):
                sunrise = datetime.fromtimestamp(data['sys']['sunrise'])
                sunset = datetime.fromtimestamp(data['sys']['sunset'])

                try:
                    if user_timezone and user_timezone.startswith('UTC'):
                        offset_str = user_timezone.replace('UTC', '').strip()
                        if offset_str.startswith('+') or offset_str.startswith('-'):
                            offset_hours = float(offset_str)
                        else:
                            offset_hours = float(offset_str) if offset_str else 0

                        sunrise_user = sunrise + timedelta(hours=offset_hours)
                        sunset_user = sunset + timedelta(hours=offset_hours)
                        now_user = datetime.utcnow() + timedelta(hours=offset_hours)

                        sunrise_str = sunrise_user.strftime('%H:%M')
                        sunset_str = sunset_user.strftime('%H:%M')
                        local_time_str = now_user.strftime('%H:%M:%S')
                    else:
                        sunrise_str = sunrise.strftime('%H:%M')
                        sunset_str = sunset.strftime('%H:%M')
                        local_time_str = datetime.utcnow().strftime('%H:%M:%S')

                    text += f"\n📅 Sunrise and sunset time (your timezone: {user_timezone or 'UTC+0'}):\n"
                    text += f"🌅 Sunrise: {sunrise_str}\n"
                    text += f"🌇 Sunset: {sunset_str}\n"
                    text += f"🕐 Current time: {local_time_str}\n"
                except Exception as e:
                    logger.error(f"Ошибка конвертации: {e}")
                    text += f"\n⚠️ Error displaying time"
            else:
                text += f"\n⚠️ Enable 'Sunrise/Sunset' feature in extra settings."

        return True, text, extended_data

    except Exception as e:
        logger.error(f"Ошибка get_extended_data: {e}")
        return False, f'❌ Ошибка: {e}' if lang == 'rus' else f'❌ Error: {e}', None