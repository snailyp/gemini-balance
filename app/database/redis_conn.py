import aioredis
from app.config.config import settings

redis_pool = None

async def get_redis_pool():
    global redis_pool
    if redis_pool is None:
        redis_pool = await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    return redis_pool
