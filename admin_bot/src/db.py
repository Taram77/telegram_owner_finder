import asyncpg
from admin_bot.src import config

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASS,
            host=config.DB_HOST
        )
    return _pool

async def get_welcome_message():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        message = await conn.fetchval("SELECT value FROM settings WHERE key = 'welcome_message'")
        return message if message else config.DEFAULT_WELCOME_MESSAGE

async def set_welcome_message(message: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                           'welcome_message', message)

async def add_channel(channel_id: int, name: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        try:
            await conn.execute("INSERT INTO channels (telegram_id, name) VALUES ($1, $2) ON CONFLICT (telegram_id) DO UPDATE SET name = EXCLUDED.name, is_active = TRUE",
                               channel_id, name)
            return True
        except Exception as e:
            print(f"Error adding channel: {e}")
            return False

async def remove_channel(channel_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE channels SET is_active = FALSE WHERE telegram_id = $1", channel_id)

async def get_active_channels():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT telegram_id, name FROM channels WHERE is_active = TRUE")

async def get_channel_keywords(channel_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        keywords_str = await conn.fetchval("SELECT keywords FROM channels WHERE telegram_id = $1", channel_id)
        return [k.strip() for k in keywords_str.split(',')] if keywords_str else config.DEFAULT_KEYWORDS

async def update_channel_keywords(channel_id: int, keywords: list):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE channels SET keywords = $1 WHERE telegram_id = $2", ','.join(keywords), channel_id)

async def get_owner_leads():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT ol.found_at, cu.username, pm.message_text, pm.original_link, ol.owner_response_text
            FROM owner_leads ol
            JOIN contacted_users cu ON ol.contacted_user_id = cu.id
            JOIN processed_messages pm ON ol.original_message_id = pm.id
            ORDER BY ol.found_at DESC
            LIMIT 20 -- Последние 20 лидов
        """)
