import redis.asyncio as redis
import time
from userbot_core.src import config

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_and_increment_dm_count(self, account_id: int) -> bool:
        """
        Проверяет, не превышен ли лимит DM для данного аккаунта за последний час.
        Возвращает True, если можно отправить, False если лимит превышен.
        """
        key = f"{config.REDIS_DM_COUNT_KEY_PREFIX}{account_id}:{int(time.time() // 3600)}" # Лимит по часам
        
        current_count = await self.redis.get(key)
        current_count = int(current_count) if current_count else 0

        if current_count >= config.MAX_DMS_PER_HOUR_PER_ACCOUNT:
            return False
        
        await self.redis.incr(key)
        await self.redis.expire(key, 3600 * 2) # Ключ живет 2 часа на всякий случай
        return True

    async def is_message_processed(self, message_hash: str) -> bool:
        """Проверяет, было ли сообщение уже обработано по его хешу."""
        key = f"{config.REDIS_PROCESSED_MESSAGE_KEY_PREFIX}{message_hash}"
        return await self.redis.exists(key)

    async def mark_message_processed(self, message_hash: str):
        """Отмечает сообщение как обработанное."""
        key = f"{config.REDIS_PROCESSED_MESSAGE_KEY_PREFIX}{message_hash}"
        await self.redis.set(key, 1, ex=86400 * 7) # Храним флаг 7 дней

    async def is_user_contacted(self, user_id: int) -> bool:
        """Проверяет, был ли пользователь уже опрошен."""
        key = f"{config.REDIS_CONTACTED_USER_KEY_PREFIX}{user_id}"
        return await self.redis.exists(key)

    async def mark_user_contacted(self, user_id: int):
        """Отмечает пользователя как опрошенного."""
        key = f"{config.REDIS_CONTACTED_USER_KEY_PREFIX}{user_id}"
        await self.redis.set(key, 1, ex=86400 * 30) # Храним флаг 30 дней
