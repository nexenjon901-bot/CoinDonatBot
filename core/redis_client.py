import redis.asyncio as redis
from core.config import config


class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_client(self) -> redis.Redis:
        """Redis client olish"""
        if not hasattr(self, '_client') or self._client is None:
            self._client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                decode_responses=True,
                db=0
            )
        return self._client

    async def close(self):
        """Redis clientni yopish"""
        if hasattr(self, '_client') and self._client:
            await self._client.close()
            self._client = None


redis_client = RedisClient()
