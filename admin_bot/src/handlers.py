from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.utils.markdown import hlink

from admin_bot.src import db, config
import aio_pika
import json

dp = Dispatcher()
connection = None
channel = None

async def init_rabbitmq():
    global connection, channel
    connection = await aio_pika.connect_robust(
        f"amqp://{config.RABBITMQ_USER}:{config.RABBITMQ_PASS}@{config.RABBITMQ_HOST}/"
    )
    channel = await connection.channel()
    await channel.declare_queue(config.Q_OWNER_CONFIRMED, durable=True)
    await channel.consume(config.Q_OWNER_CONFIRMED, on_owner_confirmed)

async def on_owner_confirmed(message: aio_pika.IncomingMessage):
    async with message.process():
        data = json.loads(message.body.decode())
        await dp.bot.send_message(
            chat_id=config.ADMIN_USER_ID,
            text=f"✅ **Новый собственник найден!**\n\n"
                 f"**Пользователь:** {data['username']} (ID: {data['user_id']})\n"
                 f"**Объявление:** {hlink('посмотреть оригинал', data['original_link']) if data['original_link'] else data['ad_text'][:200] + '...'}\n"
                 f"**Ответ:** `{data['response_text']}`\n\n"
                 f"Время: {data['timestamp']}",
            parse_mode="HTML"
        )
        print(f"Sent owner confirmed notification: {data['username']}")

@dp.message_handler(Command("start"), user_id=config.ADMIN_USER_ID)
async def cmd_start(message: types.Message):
    await message.reply(
        "Привет, Алексей! Я Admin Bot для твоего проекта поиска собственников.\n"
        "Доступные команды:\n"
        "/add_channel <ID канала/username> - Добавить канал для мониторинга.\n"
        "/remove_channel <ID канала> - Отключить мониторинг канала.\n"
        "/list_channels - Показать активные каналы.\n"
        "/set_welcome_message <текст> - Изменить приветственное сообщение для DM.\n"
        "/get_welcome_message - Показать текущее приветственное сообщение.\n"
        "/list_leads - Показать последние найденные собственники.\n"
    )

@dp.message_handler(Command("add_channel"), user_id=config.ADMIN_USER_ID)
async def cmd_add_channel(message: types.Message):
    args = message.get_args().split(maxsplit=1)
    if not args:
        await message.reply("Использование: `/add_channel <ID канала или username>`")
        return

    try:
        channel_id_or_username = args[0]
        # Для простоты, пока будем ожидать числовой ID
        # В реальном проекте, можно использовать bot.get_chat(username).id
        channel_id = int(channel_id_or_username)
        
        # Попробовать получить инфо о канале через Bot API, чтобы получить имя
        chat = await dp.bot.get_chat(channel_id)
        channel_name = chat.title if chat.title else "Unknown Channel"

        success = await db.add_channel(channel_id, channel_name)
        if success:
            await message.reply(f"Канал '{channel_name}' ({channel_id}) добавлен для мониторинга.")
        else:
            await message.reply(f"Не удалось добавить канал '{channel_name}' ({channel_id}). Возможно, он уже добавлен или произошла ошибка.")
    except ValueError:
        await message.reply("ID канала должен быть числом (например, -1001234567890).")
    except Exception as e:
        await message.reply(f"Произошла ошибка при добавлении канала: {e}")

@dp.message_handler(Command("remove_channel"), user_id=config.ADMIN_USER_ID)
async def cmd_remove_channel(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply("Использование: `/remove_channel <ID канала>`")
        return
    try:
        channel_id = int(args)
        await db.remove_channel(channel_id)
        await message.reply(f"Мониторинг канала {channel_id} остановлен.")
    except ValueError:
        await message.reply("ID канала должен быть числом.")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

@dp.message_handler(Command("list_channels"), user_id=config.ADMIN_USER_ID)
async def cmd_list_channels(message: types.Message):
    channels = await db.get_active_channels()
    if not channels:
        await message.reply("Список активных каналов пуст.")
        return
    
    text = "Активные каналы:\n"
    for ch in channels:
        text += f"- {ch['name']} (ID: `{ch['telegram_id']}`)\n"
    await message.reply(text, parse_mode="MarkdownV2")

@dp.message_handler(Command("set_welcome_message"), user_id=config.ADMIN_USER_ID)
async def cmd_set_welcome_message(message: types.Message):
    new_message_text = message.get_args()
    if not new_message_text:
        await message.reply("Использование: `/set_welcome_message <новый текст сообщения>`")
        return
    
    await db.set_welcome_message(new_message_text)
    await message.reply(f"Приветственное сообщение обновлено:\n`{new_message_text}`", parse_mode="MarkdownV2")

@dp.message_handler(Command("get_welcome_message"), user_id=config.ADMIN_USER_ID)
async def cmd_get_welcome_message(message: types.Message):
    current_message = await db.get_welcome_message()
    await message.reply(f"Текущее приветственное сообщение:\n`{current_message}`", parse_mode="MarkdownV2")

@dp.message_handler(Command("list_leads"), user_id=config.ADMIN_USER_ID)
async def cmd_list_leads(message: types.Message):
    leads = await db.get_owner_leads()
    if not leads:
        await message.reply("Пока не найдено ни одного собственника.")
        return
    
    text = "Последние найденные собственники:\n\n"
    for lead in leads:
        text += (f"**Пользователь:** @{lead['username']} \n"
                 f"**Объявление:** {hlink('ссылка', lead['original_link']) if lead['original_link'] else lead['message_text'][:100] + '...'}\n"
                 f"**Подтверждение:** `{lead['owner_response_text']}`\n"
                 f"**Когда:** {lead['found_at'].strftime('%Y-%m-%d %H:%M')}\n\n")
    await message.reply(text, parse_mode="HTML")
