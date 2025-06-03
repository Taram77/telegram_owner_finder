import asyncpg
from processing_service.src import config

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

async def update_contacted_user_status(user_id: int, status: str, response_text: str = None):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Обновляем статус и добавляем ответ в историю диалога
        if response_text:
            await conn.execute("""
                UPDATE contacted_users
                SET status = $1,
                    last_contact_at = CURRENT_TIMESTAMP,
                    dialog_history = dialog_history || jsonb_build_object('timestamp', NOW(), 'sender', 'user', 'text', $2)
                WHERE telegram_id = $3
            """, status, response_text, user_id)
        else:
            await conn.execute("""
                UPDATE contacted_users
                SET status = $1,
                    last_contact_at = CURRENT_TIMESTAMP
                WHERE telegram_id = $2
            """, status, user_id)

async def get_contacted_user_info(user_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT id, telegram_id, username FROM contacted_users WHERE telegram_id = $1", user_id)

async def get_processed_message_info(processed_message_db_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT message_text, original_link FROM processed_messages WHERE id = $1", processed_message_db_id)

async def add_owner_lead(contacted_user_id: int, original_message_id: int, owner_response_text: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO owner_leads (contacted_user_id, original_message_id, owner_response_text)
            VALUES ($1, $2, $3)
        """, contacted_user_id, original_message_id, owner_response_text)
