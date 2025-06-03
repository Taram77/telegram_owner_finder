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
