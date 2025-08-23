# ВНИМАНИЕ:
# - Это пример конфигурации БЕЗ секретов.
# - Основной файл: config.py (он в .gitignore и НЕ попадает в git).
# - Для анализа ИИ используйте этот файл. Секретов здесь НЕТ.

DEBUG = False
DRY_RUN = True  # dry-режим по умолчанию

# Часовой пояс для логов/отчётов (пример)
TIMEZONE = "Europe/Moscow"

# База данных (локальная SQLite по умолчанию)
# В проде можете использовать PostgreSQL, пример:
# DB_URL = "postgresql+psycopg2://user:pass@localhost:5432/ebot"
DB_URL = "sqlite:///data/ebot.db"

TELEGRAM = {
    "BOT_TOKEN": "___PUT_HERE___",   # секрет в config.py
    "CHAT_ID":   0                   # числовой id чата/пользователя
}

EXCHANGES = {
    "MEXC": {
        "API_KEY":    "___PUT_HERE___",  # секрет в config.py
        "API_SECRET": "___PUT_HERE___"   # секрет в config.py
    }
}

# Пары/биржи/интервалы для работы сервисов
MARKET = {
    "default_exchange": "MEXC",
    "symbols": ["BTCUSDC"],
    "interval": "1m"
}

# Прочие параметры сервиса (пример)
REPORT = {
    "send_daily": True,
    "hour_utc": 6
}
