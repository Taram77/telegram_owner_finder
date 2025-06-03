import asyncio
import logging
from aiogram import Bot, Dispatcher, executor
from admin_bot.src import config, handlers, db

logging.basicConfig(level=logging.INFO)

async def on_startup(dispatcher: Dispatcher):
    await db.get_db_pool() # Инициализируем пул подключений к БД
    await handlers.init_rabbitmq() # Инициализируем подключение к RabbitMQ
    logging.info("Admin Bot started")

async def on_shutdown(dispatcher: Dispatcher):
    pool = await db.get_db_pool()
    if pool:
        await pool.close()
    if handlers.connection:
        await handlers.connection.close()
    logging.info("Admin Bot stopped")

def main():
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    dp = handlers.dp
    dp.bot = bot # Присваиваем бота диспетчеру из handlers

    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)

if __name__ == "__main__":
    main()
