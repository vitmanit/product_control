import json
from typing import Any

import redis.asyncio as aioredis

from src.core.config import settings


class RedisCache:
    def __init__(self):
        self.redis: aioredis.Redis | None = None

    async def init(self):
        self.redis = aioredis.from_url(
            settings.redis_cache_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set(self, key: str, value: Any, ttl: int | None = None):
        serialized = json.dumps(value, default=str)
        if ttl:
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str):
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)


cache = RedisCache()
