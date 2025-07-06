import asyncio
import time
from itertools import cycle
from typing import Dict, Tuple, Union

from app.config.config import settings
from app.database.redis_conn import get_redis_pool
from app.exception.exceptions import ServiceUnavailableError
from app.log.logger import get_key_manager_logger
from app.database.services import api_key_service
from datetime import datetime, timezone

logger = get_key_manager_logger()

# New Redis keys for token bucket and RPD management
FULL_TOKEN_KEYS = "gemini:full_token_keys"  # Set of keys with available RPM tokens
EMPTY_TOKEN_KEYS = "gemini:empty_token_keys" # Sorted Set of keys with 0 RPM tokens, score is next refill time
RETIRED_KEYS = "gemini:retired_keys"      # Set of keys that have hit their RPD limit for the day
QUARANTINE_KEYS = "gemini:quarantine_keys" # Set of keys that failed too many times for non-rate-limit reasons

def get_daily_quota_ttl() -> int:
    """Calculates the TTL in seconds until midnight UTC."""
    now = datetime.now(timezone.utc)
    midnight = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
    return int((midnight - now).total_seconds())


class KeyManager:
    def __init__(self):
        self.vertex_api_keys = []
        self.vertex_key_cycle = cycle(self.vertex_api_keys)
        self.vertex_key_cycle_lock = asyncio.Lock()
        self.vertex_failure_count_lock = asyncio.Lock()
        self.vertex_key_failure_counts: Dict[str, int] = {}
        self.MAX_FAILURES = settings.MAX_FAILURES
        self.paid_key = settings.PAID_KEY
        self.redis = None

    async def initialize(self):
        self.redis = await get_redis_pool()
        
        # Clean up old redis keys
        await self.redis.delete("gemini_ready_keys", "gemini_cooldown_keys")

        # Initialize Gemini Keys into the new system
        all_gemini_keys = await api_key_service.get_all_keys('gemini')
        active_gemini_keys = [key.key_value for key in all_gemini_keys if key.status == "active"]
        
        # Use a pipeline for efficiency
        pipe = self.redis.pipeline()
        pipe.delete(FULL_TOKEN_KEYS, EMPTY_TOKEN_KEYS, RETIRED_KEYS)

        if active_gemini_keys:
            pipe.sadd(FULL_TOKEN_KEYS, *active_gemini_keys)
            # Initialize token buckets for all active keys
            for key in active_gemini_keys:
                rpm, _ = self._get_rate_limit_config(key, "default")
                pipe.hset(f"key:{key}:bucket", mapping={
                    "tokens": rpm,
                    "last_refill": time.time()
                })
        
        await pipe.execute()
        logger.info(f"Initialized {len(active_gemini_keys)} active Gemini keys into the token bucket system.")

        # Initialize Vertex Keys (in-memory) - Unchanged
        all_vertex_keys = await api_key_service.get_all_keys('vertex')
        self.vertex_api_keys = [key.key_value for key in all_vertex_keys if key.status == "active"]
        self.vertex_key_failure_counts = {key.key_value: key.failure_count or 0 for key in all_vertex_keys}
        self.vertex_key_cycle = cycle(self.vertex_api_keys) if self.vertex_api_keys else cycle([])

    def _get_rate_limit_config(self, key: str, model: str) -> Tuple[int, int]:
        """Gets the RPM and RPD for a key, following priority: Key-specific > Model-specific > Default."""
        key_suffix = key[-8:]
        if key_suffix in settings.KEY_RATE_LIMITS:
            rpm, rpd = settings.KEY_RATE_LIMITS[key_suffix]
            return rpm, rpd
        if model in settings.MODEL_RATE_LIMITS:
            rpm, rpd = settings.MODEL_RATE_LIMITS[model]
            return rpm, rpd
        return settings.DEFAULT_RPM, settings.DEFAULT_RPD

    async def _refill_token_bucket(self, key: str, rpm: int):
        """Refills the token bucket for a given key based on elapsed time."""
        bucket_info = await self.redis.hgetall(f"key:{key}:bucket")
        if not bucket_info:
            # If bucket doesn't exist, initialize it
            await self.redis.hset(f"key:{key}:bucket", mapping={"tokens": rpm, "last_refill": time.time()})
            return rpm

        tokens = float(bucket_info.get(b'tokens', rpm))
        last_refill = float(bucket_info.get(b'last_refill', time.time()))
        
        now = time.time()
        elapsed = now - last_refill
        
        # Rate of token generation per second
        rate_per_second = rpm / 60.0
        new_tokens = elapsed * rate_per_second
        
        current_tokens = min(tokens + new_tokens, rpm)
        
        await self.redis.hset(f"key:{key}:bucket", mapping={"tokens": current_tokens, "last_refill": now})
        return current_tokens

    async def get_key_with_token(self, model: str) -> str:
        """Gets a key that has an available token and has not exceeded its daily quota."""
        # First, try to get a key from the full bucket
        key = await self.redis.spop(FULL_TOKEN_KEYS)
        if not key:
            # If no keys in full bucket, it means all keys are rate-limited.
            # This is the primary indicator of high load.
            raise ServiceUnavailableError("All API keys are currently rate-limited (RPM).")

        key = key
        rpm, rpd = self._get_rate_limit_config(key, model)

        # 1. Check RPD limit
        daily_count_key = f"key:{key}:daily_count"
        current_daily_count = await self.redis.get(daily_count_key)
        
        if current_daily_count and int(current_daily_count) >= rpd:
            logger.warning(f"Key ...{key[-4:]} has reached its RPD limit of {rpd}. Retiring for the day.")
            await self.redis.sadd(RETIRED_KEYS, key)
            # Try to get another key
            return await self.get_key_with_token(model)

        # 2. Refill and consume token from bucket
        current_tokens = await self._refill_token_bucket(key, rpm)
        
        if current_tokens >= 1:
            # Consume a token
            await self.redis.hincrbyfloat(f"key:{key}:bucket", "tokens", -1)
            
            # Increment daily count
            ttl = get_daily_quota_ttl()
            await self.redis.incr(daily_count_key)
            await self.redis.expire(daily_count_key, ttl)

            # Put the key back into the appropriate bucket
            if current_tokens - 1 >= 1:
                await self.redis.sadd(FULL_TOKEN_KEYS, key)
            else:
                # No tokens left, move to empty bucket
                next_refill_time = time.time() + (60.0 / rpm)
                await self.redis.zadd(EMPTY_TOKEN_KEYS, {key: next_refill_time})
            
            return key
        else:
            # Not enough tokens even after refill, move to empty bucket and try again
            next_refill_time = time.time() + (60.0 / rpm)
            await self.redis.zadd(EMPTY_TOKEN_KEYS, {key: next_refill_time})
            return await self.get_key_with_token(model)

    async def handle_api_failure(self, api_key: str, status_code: int = None):
        """Handles non-rate-limit related API failures."""
        failure_count_key = f"key:{api_key}:failures"
        current_failures = await self.redis.incr(failure_count_key)

        if current_failures >= self.MAX_FAILURES:
            logger.warning(f"Key ...{api_key[-4:]} has failed {current_failures} times. Moving to quarantine.")
            # Move from all possible buckets to quarantine
            async with self.redis.pipeline() as pipe:
                pipe.srem(FULL_TOKEN_KEYS, api_key)
                pipe.zrem(EMPTY_TOKEN_KEYS, api_key)
                pipe.sadd(QUARANTINE_KEYS, api_key)
                await pipe.execute()
            await api_key_service.mark_key_as_limited(api_key)
        else:
            logger.warning(f"Key ...{api_key[-4:]} failed (non-rate-limit). Failure count: {current_failures}.")

    async def get_keys_by_status(self) -> dict:
        """Gets the status of all Gemini keys, including their daily request counts."""
        full_keys_set = await self.redis.smembers(FULL_TOKEN_KEYS)
        empty_keys_with_scores = await self.redis.zrange(EMPTY_TOKEN_KEYS, 0, -1, withscores=True)
        retired_keys_set = await self.redis.smembers(RETIRED_KEYS)
        quarantine_keys_set = await self.redis.smembers(QUARANTINE_KEYS)
        banned_keys_from_db = await api_key_service.get_banned_keys('gemini')
        banned_keys_set = {key.key_value for key in banned_keys_from_db}

        all_keys = full_keys_set.union(
            {k for k, v in empty_keys_with_scores},
            retired_keys_set,
            quarantine_keys_set,
            banned_keys_set
        )

        # Fetch daily counts in a pipeline
        pipe = self.redis.pipeline()
        for key in all_keys:
            pipe.get(f"key:{key}:daily_count")
        daily_counts_raw = await pipe.execute()

        daily_counts = {key: int(count) if count else 0 for key, count in zip(all_keys, daily_counts_raw)}

        now = time.time()
        
        def format_key_list(keys):
            return [{"key": k, "daily_count": daily_counts.get(k, 0)} for k in keys]

        status_dict = {
            "full_token_keys": format_key_list(full_keys_set),
            "empty_token_keys": {
                k: {"cooldown": v - now, "daily_count": daily_counts.get(k, 0)}
                for k, v in empty_keys_with_scores
            },
            "retired_keys": format_key_list(retired_keys_set),
            "quarantine_keys": format_key_list(quarantine_keys_set),
            "banned_keys": format_key_list(banned_keys_set),
        }
        return status_dict

    # --- Unchanged Vertex Methods ---
    async def get_next_vertex_key(self) -> str:
        async with self.vertex_key_cycle_lock:
            if not self.vertex_api_keys:
                raise ServiceUnavailableError("No active Vertex API keys available.")
            return next(self.vertex_key_cycle)

    async def handle_vertex_api_failure(self, api_key: str, retries: int) -> str:
        async with self.vertex_failure_count_lock:
            self.vertex_key_failure_counts[api_key] += 1
            if self.vertex_key_failure_counts[api_key] >= self.MAX_FAILURES:
                logger.warning(f"Vertex API key {api_key} has failed {self.MAX_FAILURES} times")

    # --- Other methods that might need adaptation or can be kept ---
    async def get_paid_key(self) -> str:
        return self.paid_key
    
    async def reset_key_failure_count(self, key: str) -> bool:
        """Resets a key from quarantine or retired status."""
        await api_key_service.reset_key_status_to_active(key)
        
        rpm, _ = self._get_rate_limit_config(key, "default")
        async with self.redis.pipeline() as pipe:
            pipe.srem(QUARANTINE_KEYS, key)
            pipe.srem(RETIRED_KEYS, key)
            pipe.zrem(EMPTY_TOKEN_KEYS, key)
            pipe.delete(f"key:{key}:failures")
            pipe.delete(f"key:{key}:daily_count")
            pipe.hset(f"key:{key}:bucket", mapping={"tokens": rpm, "last_refill": time.time()})
            pipe.sadd(FULL_TOKEN_KEYS, key)
            await pipe.execute()
        
        logger.info(f"Key ...{key[-4:]} has been fully reset and moved to the full token bucket.")
        return True

# --- Singleton Management ---
_singleton_instance = None
_singleton_lock = asyncio.Lock()

async def get_key_manager_instance() -> KeyManager:
    global _singleton_instance
    async with _singleton_lock:
        if _singleton_instance is None:
            _singleton_instance = KeyManager()
            await _singleton_instance.initialize()
        return _singleton_instance

async def reset_key_manager_instance():
    global _singleton_instance
    async with _singleton_lock:
        if _singleton_instance:
            _singleton_instance = None
            logger.info("KeyManager instance has been reset.")
        else:
            logger.info("KeyManager instance was not set, no reset action performed.")


async def reset_retired_keys_daily():
    """
    Moves all keys from the retired set back to the full token bucket at the start of a new day (UTC).
    """
    redis = await get_redis_pool()
    retired_keys = await redis.smembers(RETIRED_KEYS)
    if not retired_keys:
        logger.info("No retired keys to reset.")
        return

    async with redis.pipeline() as pipe:
        pipe.sadd(FULL_TOKEN_KEYS, *retired_keys)
        pipe.delete(RETIRED_KEYS)
        # Also reset their daily request count
        for key in retired_keys:
            pipe.delete(f"key:{key}:daily_count")
        await pipe.execute()
    
    logger.info(f"Reset {len(retired_keys)} retired keys and moved them to the full token bucket.")
