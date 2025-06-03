import asyncio
import logging
import json
import datetime

import aio_pika

from processing_service.src import config, db
from processing_service.src.dialog_manager import parse_owner_agent_response

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

rabbit_connection = None
rabbit_channel = None

async def init_services():
    global rabbit_connection, rabbit_channel
    await db.get_db_pool() # Инициализируем пул БД
    
    rabbit_connection = await aio_pika.connect_robust(
        f"amqp://{config.RABBITMQ_USER}:{config.RABBITMQ_PASS}@{config.RABBITMQ_HOST}/"
    )
    rabbit_channel = await rabbit_connection.channel()
    
    # Объявляем очереди
    await rabbit_channel.declare_queue(config.Q_NEW_AD, durable=True)
    await rabbit_channel.declare_queue(config.Q_DM_RESPONSE, durable=True)
    await rabbit_channel.declare_queue(config.Q_OWNER_CONFIRMED, durable=True)
    await rabbit_channel.declare_queue(config.Q_SEND_DM, durable=True) # На случай, если нужно будет отправлять DM отсюда

    # Запускаем consumer-ы
    await rabbit_channel.consume(config.Q_NEW_AD, on_new_ad_found)
    await rabbit_channel.consume(config.Q_DM_RESPONSE, on_dm_response)

async def on_new_ad_found(message: aio_pika.IncomingMessage):
    """
    Обрабатывает событие о новом найденном объявлении.
    Инициирует отправку DM, если пользователь ранее не был опрошен.
    """
    async with message.process():
        data = json.loads(message.body.decode())
        user_id = data['author_id']
        username = data['author_username']
        processed_message_db_id = data['processed_message_db_id']
        original_link = data['original_link']
        
        if not user_id: # Если не удалось получить ID автора, пропускаем
            logger.warning(f"Skipping ad {processed_message_db_id}: no author ID found.")
            return

        # Проверяем статус пользователя в БД
        contact_status = await db.get_contacted_user_status(user_id)

        if contact_status in ['owner', 'agent', 'blacklisted']:
            logger.info(f"User {user_id} already has status '{contact_status}'. Skipping DM initiation.")
            return
        
        logger.info(f"New ad from user {user_id}. Initiating DM request.")
        
        # Получаем актуальное приветственное сообщение
        welcome_message = await db.get_welcome_message_from_settings()

        # Публикуем запрос на отправку DM
        await rabbit_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps({
                    "user_id": user_id,
                    "username": username,
                    "welcome_message": welcome_message,
                    "processed_message_db_id": processed_message_db_id,
                    "original_link": original_link
                }).encode(),
                content_type='application/json'
            ),
            routing_key=config.Q_SEND_DM
        )
        logger.info(f"DM request for user {user_id} published.")


async def on_dm_response(message: aio_pika.IncomingMessage):
    """
    Обрабатывает ответы от пользователей на DM.
    Определяет статус (собственник/агент) и сохраняет результат.
    """
    async with message.process():
        data = json.loads(message.body.decode())
        user_id = data['user_id']
        username = data['username']
        response_text = data['response_text']

        logger.info(f"Processing DM response from {user_id}: '{response_text}'")

        status = parse_owner_agent_response(response_text)
        await db.update_contacted_user_status(user_id, status, response_text)

        if status == 'owner':
            user_info = await db.get_contacted_user_info(user_id)
            if user_info:
                # Получаем processed_message_db_id из contacted_users
                processed_message_db_id = user_info['first_contact_message_id'] 
                original_ad_info = await db.get_processed_message_info(processed_message_db_id)

                if original_ad_info:
                    await db.add_owner_lead(user_info['id'], processed_message_db_id, response_text)
                    logger.info(f"User {user_id} confirmed as owner! Lead saved.")

                    # Уведомляем Admin Bot
                    await rabbit_channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps({
                                "user_id": user_id,
                                "username": username,
                                "response_text": response_text,
                                "ad_text": original_ad_info['message_text'],
                                "original_link": original_ad_info['original_link'],
                                "timestamp": datetime.datetime.now().isoformat()
                            }).encode(),
                            content_type='application/json'
                        ),
                        routing_key=config.Q_OWNER_CONFIRMED
                    )
                    logger.info(f"Owner confirmed notification for {user_id} published.")
                else:
                    logger.error(f"Could not retrieve original ad info for processed_message_db_id {processed_message_db_id} for user {user_id}")
            else:
                logger.error(f"Could not retrieve contacted user info for user_id {user_id} after owner confirmation.")
        elif status == 'agent':
            logger.info(f"User {user_id} identified as agent. Dialogue stopped.")
        else: # pending
            logger.info(f"User {user_id} response unclear. Status remains 'pending'.")
            # Можно добавить логику для отправки повторных вопросов
            pass

async def main():
    await init_services()
    logger.info("Processing Service started. Waiting for messages...")
    try:
        await asyncio.Future() # Runs forever
    finally:
        if rabbit_connection:
            await rabbit_connection.close()
        pool = await db.get_db_pool()
        if pool:
            await pool.close()
        logger.info("Processing Service stopped.")

if __name__ == "__main__":
    asyncio.run(main())
