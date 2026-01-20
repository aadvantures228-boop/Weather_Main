import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('weather_bot.db')
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'rus',
            region TEXT DEFAULT 'Moscow',
            timezone TEXT DEFAULT 'UTC+0',
            pressure_unit TEXT DEFAULT 'mmhg',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица избранного
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            city_name TEXT,
            country TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Таблица уведомлений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            hour INTEGER,
            minute INTEGER,
            timezone TEXT,
            region TEXT,
            notification_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Таблица дополнительных функций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            feature_name TEXT,
            enabled BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def get_db_connection():
    """Получить соединение с базой данных"""
    return sqlite3.connect('weather_bot.db', check_same_thread=False)

def get_user_lang_db(user_id: int):
    """Получить язык пользователя из БД"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if result:
        lang = result[0]
    else:
        # Создаем пользователя, если не существует
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, lang, region, timezone, pressure_unit) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, 'rus', 'Moscow', 'UTC+0', 'mmhg'))
        conn.commit()
        lang = 'rus'

    conn.close()
    return lang

def set_user_lang_db(user_id: int, lang: str):
    """Установить язык пользователя в БД"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, lang) 
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang
    ''', (user_id, lang))

    conn.commit()
    conn.close()
    logger.info(f"Язык пользователя {user_id} установлен: {lang}")