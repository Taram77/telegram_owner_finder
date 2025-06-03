import asyncio
import logging
import hashlib
import random
import time
from pyrogram import Client, filters as pyrogram_filters
from pyrogram.types import Message
from pyrogram.enums import ChatType
import aio_pika
import json
import redis.asyncio as redis

from userbot_core.src import config, db
from userbot_core.src.filters import is_ad_message
from userbot_core.src.rate_limiter import RateLimiter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

userbot_clients = {} # client_id -> pyrogram.Client instance
rabbit_connection = None
rabbit_channel = None
redis_client = None
rate_limiter = None

async def init_services():
    global rabbit_connection, rabbit_channel, redis_client, rate_limiter
    await db.get_db_pool() # Инициализируем пул БД
    
    redis_client = redis.Redis(host=config.REDIS_HOST, port=6379, db=0)
    rate_limiter = RateLimiter(redis_client)

    rabbit_connection = await aio_pika.connect_robust(
        f"amqp://{config.RABBITMQ_USER}:{config.RABBITMQ_PASS}@{config.RABBITMQ_HOST}/"
    )
    rabbit_channel = await rabbit_connection.channel()
    await rabbit_channel.declare_queue(config.Q_NEW_AD, durable=True)
    await rabbit_channel.declare_queue(config.Q_SEND_DM, durable=True)
    await rabbit_channel.declare_queue(config.Q_DM_RESPONSE, durable=True)

    # Запускаем consumer для отправки DM
    await rabbit_channel.consume(config.Q_SEND_DM, on_send_dm_request)

async def load_and_start_userbots():
    accounts = await db.get_active_user_accounts()
    if not accounts:
        logger.warning("No active user accounts found in DB. Please add at least one using session_generator.py and add to DB.")
        return

    for acc in accounts:
        client_id = acc['id']
        phone_number = acc['phone_number']
        session_string = acc['session_string']

        try:
            client = Client(
                name=str(client_id), # Уникальное имя для сессии
                api_id=config.PYROGRAM_API_ID,
                api_hash=config.PYROGRAM_API_HASH,
                session_string=session_string,
                phone_number=phone_number, # Для более удобного логирования
                workdir="pyrogram_sessions/" # Хранение сессий
            )
            # Добавляем хендлеры на этот конкретный клиент
            client.add_handler(pyrogram_filters.new_message & pyrogram_filters.private & pyrogram_filters.user(lambda _, __, msg: msg.from_user.id != client.me.id), process_dm_response)
            client.add_handler(pyrogram_filters.new_message & pyrogram_filters.channel, process_channel_message)

            await client.start()
            userbot_clients[client_id] = client
            logger.info(f"Userbot account {phone_number} (ID: {client_id}) started successfully.")
        except Exception as e:
            logger.error(f"Failed to start userbot account {phone_number} (ID: {client_id}): {e}")

async def process_channel_message(client: Client, message: Message):
    """Обрабатывает новые сообщения в каналах."""
    if not message.text:
        return

    channel_id = message.chat.id
    message_text = message.text
    message_id = message.id
    
    # Получаем keywords для этого канала
    active_channels_data = await db.get_active_channels()
    channel_keywords = config.DEFAULT_KEYWORDS
    for ch_data in active_channels_data:
        if ch_data['telegram_id'] == channel_id and ch_data['keywords']:
            channel_keywords = [k.strip() for k in ch_data['keywords'].split(',')]
            break

    if not is_ad_message(message_text, channel_keywords):
        return

    message_hash = hashlib.sha256(message_text.encode()).hexdigest()

    if await rate_limiter.is_message_processed(message_hash):
        logger.info(f"Message {message_id} in {channel_id} already processed. Skipping.")
        return

    author_id = message.from_user.id if message.from_user else None
    author_username = message.from_user.username if message.from_user else None
    original_link = message.link if message.link else None

    # Записываем сообщение как обработанное в БД и Redis
    processed_msg_db_id = await db.record_processed_message(
        message_id, channel_id, message_text, message_hash, author_id, author_username, original_link
    )
    await rate_limiter.mark_message_processed(message_hash)

    # Публикуем событие о новом объявлении
    await rabbit_channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps({
                "processed_message_db_id": processed_msg_db_id,
                "channel_id": channel_id,
                "message_id": message_id,
                "message_text": message_text,
                "author_id": author_id,
                "author_username": author_username,
                "original_link": original_link
            }).encode(),
            content_type='application/json'
        ),
        routing_key=config.Q_NEW_AD
    )
    logger.info(f"New ad found and published from channel {channel_id}, message {message_id}")


async def on_send_dm_request(message: aio_pika.IncomingMessage):
    """Обрабатывает запросы на отправку DM."""
    async with message.process():
        data = json.loads(message.body.decode())
        user_id = data['user_id']
        welcome_message = data['welcome_message']
        processed_message_db_id = data['processed_message_db_id']
        username = data['username']

        if await rate_limiter.is_user_contacted(user_id):
            logger.info(f"User {user_id} already contacted. Skipping DM.")
            return
        
        # Выбираем Userbot аккаунт для отправки
        selected_client_id = None
        for client_id, client in userbot_clients.items():
            if await rate_limiter.check_and_increment_dm_count(client_id):
                selected_client_id = client_id
                break
        
        if selected_client_id is None:
            logger.warning(f"No available userbot accounts to send DM to {user_id}. Re-queueing.")
            # Вернуть сообщение в очередь или в DLQ
            await message.nack(requeue=True) # Повторно поставить в очередь
            return
        
        client = userbot_clients[selected_client_id]
        
        try:
            # Обновляем last_used_at для аккаунта
            await db.update_user_account_last_used(selected_client_id)
            
            # Отправляем сообщение
            await asyncio.sleep(random.uniform(*config.DM_SEND_DELAY_SECONDS)) # Случайная задержка
            
            sent_message = await client.send_message(user_id, welcome_message)
            logger.info(f"DM sent to {user_id} using userbot {selected_client_id}. Message ID: {sent_message.id}")
            
            # Отмечаем пользователя как опрошенного в Redis
            await rate_limiter.mark_user_contacted(user_id)

            # Сохраняем информацию о контакте в БД
            await db.add_contacted_user(user_id, username, processed_message_db_id)

        except Exception as e:
            logger.error(f"Failed to send DM to {user_id} using userbot {selected_client_id}: {e}")
            # В зависимости от ошибки, можно маркировать аккаунт как неактивный или просто пропустить
            # Например, если PRIVACY_RESTRICTED, то пользователь закрыл DM, помечаем как contacted
            if "PRIVACY_RESTRICTED" in str(e):
                logger.warning(f"User {user_id} has privacy restrictions. Cannot send DM.")
                await rate_limiter.mark_user_contacted(user_id) # все равно помечаем как "контактировали"
                await db.add_contacted_user(user_id, username, processed_message_db_id)
            else:
                pass # Другие ошибки, возможно, требуют ручного вмешательства или более умного retry


async def process_dm_response(client: Client, message: Message):
    """Обрабатывает ответы на DM от потенциальных собственников."""
    if message.from_user.is_bot: # Игнорируем ответы от ботов
        return

    user_id = message.from_user.id
    response_text = message.text
    username = message.from_user.username or f"id{user_id}"

    # Публикуем ответ в очередь для Processing Service
    await rabbit_channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps({
                "user_id": user_id,
                "username": username,
                "response_text": response_text
            }).encode(),
            content_type='application/json'
        ),
        routing_key=config.Q_DM_RESPONSE
    )
    logger.info(f"DM response from {user_id} published to processing service.")

async def main():
    await init_services()
    await load_and_start_userbots()

    # Запускаем основной цикл Pyrogram.
    # Pyrogram Client.run() блокирует выполнение, поэтому управляем им вручную
    # через Event Loop
    try:
        # Для того, чтобы Pyrogram продолжал работу в фоне
        # и хендлеры слушали сообщения, мы просто держим Event Loop открытым.
        # Цикл не должен завершаться, пока клиенты активны.
        # Например, можно добавить периодическую проверку здоровья или просто sleep
        while True:
            await asyncio.sleep(60) # Просто держим Event Loop живым
    finally:
        for client in userbot_clients.values():
            await client.stop()
        if rabbit_connection:
            await rabbit_connection.close()
        if redis_client:
            await redis_client.close()
        pool = await db.get_db_pool()
        if pool:
            await pool.close()
        logger.info("Userbot Core stopped.")

if __name__ == "__main__":
    asyncio.run(main())
