import os

# Database settings
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_NAME = os.getenv("POSTGRES_DB", "telegram_owner_finder")
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "password")

# RabbitMQ settings
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASSWORD", "guest")

# Redis settings
REDIS_HOST = os.getenv("REDIS_HOST", "redis")

# Pyrogram API ID/Hash for Userbot-ов
PYROGRAM_API_ID = int(os.getenv("PYROGRAM_API_ID"))
PYROGRAM_API_HASH = os.getenv("PYROGRAM_API_HASH")

# Default welcome message for DMs
DEFAULT_WELCOME_MESSAGE = os.getenv("DEFAULT_WELCOME_MESSAGE", "Здравствуйте! Подскажите, вы собственник квартиры или агент?")

# RabbitMQ queue names
Q_NEW_AD = "new_ad_found"
Q_SEND_DM = "send_dm"
Q_DM_RESPONSE = "dm_response"
Q_OWNER_CONFIRMED = "owner_confirmed"

# Keywords for filtering
DEFAULT_KEYWORDS = ["продажа", "квартира", "цена", "м2", "собственник"]

# Userbot specific settings
MAX_DMS_PER_HOUR_PER_ACCOUNT = 20 # Пример: 20 DM в час с одного аккаунта
DM_SEND_DELAY_SECONDS = (10, 30) # Случайная задержка между DM (от 10 до 30 секунд)
CHANNEL_MONITOR_INTERVAL_SECONDS = 300 # Как часто проверять новые сообщения в каналах (5 минут)

# Redis Keys
REDIS_DM_COUNT_KEY_PREFIX = "dm_count:" # dm_count:account_id:timestamp
REDIS_PROCESSED_MESSAGE_KEY_PREFIX = "processed_msg:" # processed_msg:message_hash
REDIS_CONTACTED_USER_KEY_PREFIX = "contacted_user:" # contacted_user:user_id
