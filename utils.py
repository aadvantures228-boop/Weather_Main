import logging
import logging.handlers
from datetime import datetime
import pytz
import requests
from typing import Dict, Optional
from config import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT, OPENSTREETMAP_URL

logger = logging.getLogger(__name__)

def setup_logging():
    """Настройка логирования"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Файловый хендлер
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_location_info(lat: float, lon: float) -> Optional[Dict]:
    """Получить информацию о местоположении по координатам"""
    try:
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'addressdetails': 1
        }
        response = requests.get(OPENSTREETMAP_URL, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"OpenStreetMap вернул код {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Ошибка get_location_info: {e}")
        return None

def get_timezone_by_coordinates(lat: float, lon: float, location_info: dict = None):
    """Получить часовой пояс по координатам"""
    try:
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)

        if timezone_str:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            offset = now.utcoffset().total_seconds() / 3600

            if offset >= 0:
                offset_str = f"UTC+{int(offset)}"
            else:
                offset_str = f"UTC{int(offset)}"

            return {
                'timezone': timezone_str,
                'utc_offset': offset_str,
                'offset_hours': offset
            }
        else:
            return calculate_timezone_by_longitude(lon)
    except ImportError:
        logger.warning("timezonefinder не установлен, используется расчёт по долготе")
        return calculate_timezone_by_longitude(lon)
    except Exception as e:
        logger.error(f"Ошибка определения часового пояса: {e}")
        return calculate_timezone_by_longitude(lon)

def calculate_timezone_by_longitude(lon: float):
    """Рассчитать часовой пояс по долготе"""
    offset_hours = round(lon / 15)

    if offset_hours >= 0:
        offset_str = f"UTC+{offset_hours}"
        timezone_name = f"Etc/GMT-{offset_hours}"
    else:
        offset_str = f"UTC{offset_hours}"
        timezone_name = f"Etc/GMT+{abs(offset_hours)}"

    return {
        'timezone': timezone_name,
        'utc_offset': offset_str,
        'offset_hours': offset_hours
    }

def get_utc_offset(timezone_str: str) -> str:
    """Получить смещение UTC для часового пояса"""
    try:
        if timezone_str.startswith('UTC'):
            return timezone_str

        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        offset = now.utcoffset().total_seconds() / 3600

        if offset >= 0:
            return f"UTC+{int(offset)}"
        else:
            return f"UTC{int(offset)}"
    except:
        return timezone_str

def normalize_city_name(city_name: str, lang: str) -> str:
    """Нормализовать название города"""
    from config import RUSSIANCITYCOORDINATES
    
    if lang != 'rus':
        return city_name

    city_lower = city_name.lower().strip()
    if city_lower in RUSSIANCITYCOORDINATES:
        # Возвращаем правильное название с заглавной буквы
        for key in RUSSIANCITYCOORDINATES:
            if key.lower() == city_lower:
                return key.title()

    return city_name