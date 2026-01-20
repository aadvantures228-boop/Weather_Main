import uuid
import logging
from typing import Dict, List, Optional
from telegram.ext import CallbackContext
from config import DEFAULT_LANG, DEFAULT_REGION, DEFAULT_TIMEZONE, DEFAULT_PRESSURE_UNIT

logger = logging.getLogger(__name__)

def make_favorite_key(city_name: str, country: str) -> str:
    """Создать ключ для избранного"""
    return f"{city_name.strip().lower()}|{country.strip().upper()}"

class UserDataManager:
    @staticmethod
    def get_user_lang(context: CallbackContext, user_id: int) -> str:
        """Получить язык пользователя"""
        if 'lang' not in context.bot_data:
            context.bot_data['lang'] = {}
        
        if user_id not in context.bot_data['lang']:
            from database import get_user_lang_db
            lang = get_user_lang_db(user_id)
            context.bot_data['lang'][user_id] = lang
        
        return context.bot_data['lang'][user_id]
    
    @staticmethod
    def set_user_lang(context: CallbackContext, user_id: int, lang: str):
        """Установить язык пользователя"""
        if 'lang' not in context.bot_data:
            context.bot_data['lang'] = {}
        
        context.bot_data['lang'][user_id] = lang
        from database import set_user_lang_db
        set_user_lang_db(user_id, lang)
        logger.info(f"Язык пользователя {user_id} установлен: {lang}")
    
    @staticmethod
    def get_user_region(context: CallbackContext, user_id: int) -> str:

        if 'region' not in context.bot_data:
            context.bot_data['region'] = {}
        
        if user_id not in context.bot_data['region']:
            context.bot_data['region'][user_id] = DEFAULT_REGION
        
        return context.bot_data['region'][user_id]
    
    @staticmethod
    def set_user_region(context: CallbackContext, user_id: int, region: str):
        """Установить регион пользователя"""
        if 'region' not in context.bot_data:
            context.bot_data['region'] = {}
        
        context.bot_data['region'][user_id] = region
        
        # Обновляем регион в уведомлениях
        if 'notifications' in context.bot_data and user_id in context.bot_data['notifications']:
            notifications = context.bot_data['notifications'][user_id]
            for notification in notifications:
                notification['region'] = region
            context.bot_data['notifications'][user_id] = notifications
        
        logger.info(f"Регион пользователя {user_id} установлен: {region}")
        return True
    
    @staticmethod
    def get_user_timezone(context: CallbackContext, user_id: int) -> str:
        """Получить часовой пояс пользователя"""
        if 'timezone' not in context.bot_data:
            context.bot_data['timezone'] = {}
        
        if user_id not in context.bot_data['timezone']:
            context.bot_data['timezone'][user_id] = DEFAULT_TIMEZONE
        
        return context.bot_data['timezone'][user_id]
    
    @staticmethod
    def set_user_timezone(context: CallbackContext, user_id: int, timezone: str):
        """Установить часовой пояс пользователя"""
        if 'timezone' not in context.bot_data:
            context.bot_data['timezone'] = {}
        
        context.bot_data['timezone'][user_id] = timezone
        logger.info(f"Часовой пояс пользователя {user_id} установлен: {timezone}")
        return True
    
    @staticmethod
    def get_user_pressure_unit(context: CallbackContext, user_id: int) -> str:
        """Получить единицу измерения давления"""
        if 'pressure_unit' not in context.bot_data:
            context.bot_data['pressure_unit'] = {}
        
        if user_id not in context.bot_data['pressure_unit']:
            lang = UserDataManager.get_user_lang(context, user_id)
            context.bot_data['pressure_unit'][user_id] = 'mmhg' if lang == 'rus' else 'hpa'
        
        return context.bot_data['pressure_unit'][user_id]
    
    @staticmethod
    def set_user_pressure_unit(context: CallbackContext, user_id: int, unit: str):
        """Установить единицу измерения давления"""
        if 'pressure_unit' not in context.bot_data:
            context.bot_data['pressure_unit'] = {}
        
        context.bot_data['pressure_unit'][user_id] = unit
        logger.info(f"Единица давления пользователя {user_id} установлена: {unit}")
    
    @staticmethod
    def get_user_features(context: CallbackContext, user_id: int) -> Dict:
        """Получить настройки дополнительных функций"""
        if 'features' not in context.bot_data:
            context.bot_data['features'] = {}
        
        if user_id not in context.bot_data['features']:
            # По умолчанию все функции выключены
            context.bot_data['features'][user_id] = {
                'cloudiness': False,
                'wind_direction': False,
                'wind_gust': False,
                'sunrise_sunset': False
            }
        
        return context.bot_data['features'][user_id]
    
    @staticmethod
    def set_user_features(context: CallbackContext, user_id: int, features: Dict):
        if 'features' not in context.bot_data:
            context.bot_data['features'] = {}
        
        context.bot_data['features'][user_id] = features
        logger.info(f"Настройки функций пользователя {user_id} обновлены")
        return True
    
    @staticmethod
    def toggle_user_feature(context: CallbackContext, user_id: int, feature: str) -> bool:
        """Переключить дополнительную функцию"""
        features = UserDataManager.get_user_features(context, user_id)
        
        if feature in features:
            features[feature] = not features[feature]
            UserDataManager.set_user_features(context, user_id, features)
            logger.info(f"Функция {feature} пользователя {user_id} переключена: {features[feature]}")
            return True
        return False
    
    @staticmethod
    def get_user_notifications(context: CallbackContext, user_id: int):
        """Получить уведомления пользователя"""
        if 'notifications' not in context.bot_data:
            context.bot_data['notifications'] = {}
        
        if user_id not in context.bot_data['notifications']:
            context.bot_data['notifications'][user_id] = []
        
        return context.bot_data['notifications'][user_id]
    
    @staticmethod
    def set_user_notifications(context: CallbackContext, user_id: int, notifications_list):
        """Установить уведомления пользователя"""
        if 'notifications' not in context.bot_data:
            context.bot_data['notifications'] = {}
        
        context.bot_data['notifications'][user_id] = notifications_list
        return True
    
    @staticmethod
    def add_user_notification(context: CallbackContext, user_id: int, hour: int, minute: int, timezone_str: str):
        """Добавить уведомление пользователя"""
        from handlers.notifications import create_notification_job
        
        notifications = UserDataManager.get_user_notifications(context, user_id)
        
        # Проверка на максимальное количество уведомлений
        if len(notifications) >= 10:
            return False, "limit_exceeded"

        for notification in notifications:
            if notification['hour'] == hour and notification['minute'] == minute and notification[
                'timezone'] == timezone_str:
                return False, "already_exists"

        new_notification = {
            'id': str(uuid.uuid4())[:8],
            'hour': hour,
            'minute': minute,
            'timezone': timezone_str,
            'region': UserDataManager.get_user_region(context, user_id)
        }

        notifications.append(new_notification)
        UserDataManager.set_user_notifications(context, user_id, notifications)

        if context.application and context.application.job_queue:
            create_notification_job(context, user_id, new_notification)
            logger.info(f"Уведомление добавлено для пользователя {user_id}: {hour}:{minute} {timezone_str}")
            return True, "success"
        else:
            logger.error("Job queue недоступна!")
            return False, "job_queue_unavailable"
    
    @staticmethod
    def remove_user_notification(context: CallbackContext, user_id: int, notification_id: str):
        """Удалить уведомление пользователя"""
        from handlers.notifications import remove_notification_job
        
        notifications = UserDataManager.get_user_notifications(context, user_id)
        new_notifications = []
        removed = False

        for notification in notifications:
            if notification['id'] == notification_id:
                remove_notification_job(context, user_id, notification_id)
                removed = True
            else:
                new_notifications.append(notification)

        UserDataManager.set_user_notifications(context, user_id, new_notifications)
        
        if removed:
            logger.info(f"Уведомление {notification_id} удалено для пользователя {user_id}")
        
        return removed
    
    @staticmethod
    def disable_all_notifications(context: CallbackContext, user_id: int):
        """Отключить все уведомления"""
        from handlers.notifications import remove_notification_job
        
        notifications = UserDataManager.get_user_notifications(context, user_id)
        for notification in notifications:
            remove_notification_job(context, user_id, notification['id'])
        
        context.bot_data['notifications'][user_id] = []
        logger.info(f"Все уведомления отключены для пользователя {user_id}")
        return True
    
    @staticmethod
    def get_user_favorites(context: CallbackContext, user_id: int):
        """Получить избранное пользователя (старый формат)"""
        if 'favorites' not in context.bot_data:
            context.bot_data['favorites'] = {}
        
        if user_id not in context.bot_data['favorites']:
            context.bot_data['favorites'][user_id] = []
        
        return context.bot_data['favorites'][user_id]
    
    @staticmethod
    def get_user_favorites_dict(context: CallbackContext, user_id: int) -> dict:
        """Получить избранное пользователя в формате словаря"""
        if "favorites_dict" not in context.bot_data:
            context.bot_data["favorites_dict"] = {}
        
        if user_id not in context.bot_data["favorites_dict"]:
            context.bot_data["favorites_dict"][user_id] = {}

            old_list = UserDataManager.get_user_favorites(context, user_id)
            for city in old_list:
                key = f"{city.strip().lower()}|"
                context.bot_data["favorites_dict"][user_id][key] = city

        return context.bot_data["favorites_dict"][user_id]
    
    @staticmethod
    def save_user_favorites_dict(context: CallbackContext, user_id: int, favs: dict) -> None:
        """Сохранить избранное пользователя в формате словаря"""
        if "favorites_dict" not in context.bot_data:
            context.bot_data["favorites_dict"] = {}
        
        context.bot_data["favorites_dict"][user_id] = favs
    
    @staticmethod
    def set_user_favorites(context: CallbackContext, user_id: int, favorites_list: list):
        """Установить избранное пользователя (старый формат)"""
        if 'favorites' not in context.bot_data:
            context.bot_data['favorites'] = {}
        
        context.bot_data['favorites'][user_id] = favorites_list
        return True
    
    @staticmethod
    def add_user_favorite(context: CallbackContext, user_id: int, city: str, country: str = ""):
        """Добавить город в избранное"""
        favs_dict = UserDataManager.get_user_favorites_dict(context, user_id)
        fav_key = make_favorite_key(city, country)
        
        if fav_key not in favs_dict:
            favs_dict[fav_key] = city
            UserDataManager.save_user_favorites_dict(context, user_id, favs_dict)
            
            # Также обновляем старый список для совместимости
            favorites_list = UserDataManager.get_user_favorites(context, user_id)
            if city not in favorites_list:
                favorites_list.append(city)
                UserDataManager.set_user_favorites(context, user_id, favorites_list)
            
            logger.info(f"Город {city} добавлен в избранное для пользователя {user_id}")
            return True
        return False
    
    @staticmethod
    def remove_user_favorite(context: CallbackContext, user_id: int, city: str, country: str = ""):
        """Удалить город из избранного"""
        favs_dict = UserDataManager.get_user_favorites_dict(context, user_id)
        fav_key = make_favorite_key(city, country)
        
        if fav_key in favs_dict:
            del favs_dict[fav_key]
            UserDataManager.save_user_favorites_dict(context, user_id, favs_dict)
            
            # Также обновляем старый список
            favorites_list = UserDataManager.get_user_favorites(context, user_id)
            if city in favorites_list:
                favorites_list.remove(city)
                UserDataManager.set_user_favorites(context, user_id, favorites_list)
            
            logger.info(f"Город {city} удален из избранного для пользователя {user_id}")
            return True
        return False
    
    @staticmethod
    def clear_user_favorites(context: CallbackContext, user_id: int):
        """Очистить избранное пользователя"""
        if 'favorites' not in context.bot_data:
            context.bot_data['favorites'] = {}
        
        context.bot_data['favorites'][user_id] = []
        logger.info(f"Избранное очищено для пользователя {user_id}")
        return True
    
    @staticmethod
    def save_city_coordinates(context: CallbackContext, user_id: int, city: str, lat: float, lon: float):
        """Сохранить координаты города"""
        if 'city_coordinates' not in context.bot_data:
            context.bot_data['city_coordinates'] = {}
        
        if user_id not in context.bot_data['city_coordinates']:
            context.bot_data['city_coordinates'][user_id] = {}
        
        context.bot_data['city_coordinates'][user_id][city] = {'lat': lat, 'lon': lon}
    
    @staticmethod
    def get_city_coordinates(context: CallbackContext, user_id: int, city: str):
        """Получить координаты города"""
        if 'city_coordinates' not in context.bot_data:
            return None
        
        if user_id not in context.bot_data['city_coordinates']:
            return None
        
        return context.bot_data['city_coordinates'][user_id].get(city)
    
    @staticmethod
    def add_to_history(context: CallbackContext, user_id: int, city_name: str):
        """Добавить город в историю поиска"""
        from config import MAX_HISTORY_ITEMS
        
        if 'history' not in context.bot_data:
            context.bot_data['history'] = {}
        
        if user_id not in context.bot_data['history']:
            context.bot_data['history'][user_id] = []
        
        # Удаляем если уже есть (для уникальности)
        history = context.bot_data['history'][user_id]
        if city_name in history:
            history.remove(city_name)
        
        # Добавляем в начало
        history.insert(0, city_name)
        
        # Ограничиваем размер истории
        context.bot_data['history'][user_id] = history[:MAX_HISTORY_ITEMS]
        
        logger.info(f"Город {city_name} добавлен в историю пользователя {user_id}")
        return True
    
    @staticmethod
    def get_user_history(context: CallbackContext, user_id: int):
        """Получить историю поиска пользователя"""
        if 'history' not in context.bot_data:
            context.bot_data['history'] = {}
        
        if user_id not in context.bot_data['history']:
            context.bot_data['history'][user_id] = []
        
        return context.bot_data['history'][user_id]
    
    @staticmethod
    def clear_user_history(context: CallbackContext, user_id: int):
        """Очистить историю поиска"""
        if 'history' not in context.bot_data:
            context.bot_data['history'] = {}
        
        context.bot_data['history'][user_id] = []
        logger.info(f"История очищена для пользователя {user_id}")
        return True