import asyncpg
from userbot_core.src import config

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

async def get_active_user_accounts():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT id, phone_number, session_string FROM user_accounts WHERE is_active = TRUE ORDER BY last_used_at ASC")

async def update_user_account_last_used(account_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE user_accounts SET last_used_at = CURRENT_TIMESTAMP WHERE id = $1", account_id)

async def add_user_account(phone_number: str, session_string: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO user_accounts (phone_number, session_string) VALUES ($1, $2) ON CONFLICT (phone_number) DO UPDATE SET session_string = EXCLUDED.session_string, is_active = TRUE",
                           phone_number, session_string)

async def get_active_channels():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT telegram_id, name, keywords FROM channels WHERE is_active = TRUE")

async def record_processed_message(message_id: int, channel_id: int, text: str, text_hash: str, author_id: int, username: str, original_link: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Check if message already processed (can happen if hash collision, but less likely with unique constraint on message_id+channel_id)
        existing_id = await conn.fetchval("SELECT id FROM processed_messages WHERE message_telegram_id = $1 AND channel_telegram_id = $2", message_id, channel_id)
        if existing_id:
            return existing_id

        return await conn.fetchval("""
            INSERT INTO processed_messages (message_telegram_id, channel_telegram_id, message_text, message_hash, author_telegram_id, author_username, original_link)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """, message_id, channel_id, text, text_hash, author_id, username, original_link)

async def get_contacted_user_status(user_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT status FROM contacted_users WHERE telegram_id = $1", user_id)

async def add_contacted_user(user_id: int, username: str, first_message_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO contacted_users (telegram_id, username, first_contact_message_id, status)
            VALUES ($1, $2, $3, 'pending')
            ON CONFLICT (telegram_id) DO UPDATE SET username = EXCLUDED.username, status = 'pending', last_contact_at = CURRENT_TIMESTAMP
        """, user_id, username, first_message_id)

async def get_welcome_message_from_settings():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        message = await conn.fetchval("SELECT value FROM settings WHERE key = 'welcome_message'")
        return message if message else config.DEFAULT_WELCOME_MESSAGE
