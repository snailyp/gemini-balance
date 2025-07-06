import asyncio
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.config import settings
from app.database.redis_conn import get_redis_pool
from app.log.logger import Logger
from app.service.error_log.error_log_service import delete_old_error_logs
from app.service.key.key_manager import (
    EMPTY_TOKEN_KEYS,
    FULL_TOKEN_KEYS,
    reset_retired_keys_daily,
)
from app.service.request_log.request_log_service import (
    delete_old_request_logs_task,
)

logger = Logger.setup_logger("scheduler")
scheduler_instance = None


async def activate_keys_from_empty_bucket():
    """
    Periodically moves keys from the empty bucket back to the full bucket
    once their token refill time has come.
    """
    redis = await get_redis_pool()
    now = time.time()

    # Get keys whose cooldown (next token refill time) has expired.
    keys_to_activate = await redis.zrangebyscore(EMPTY_TOKEN_KEYS, -1, now)

    if not keys_to_activate:
        return

    # Use a pipeline to move all activated keys at once.
    async with redis.pipeline() as pipe:
        pipe.sadd(FULL_TOKEN_KEYS, *keys_to_activate)
        pipe.zrem(EMPTY_TOKEN_KEYS, *keys_to_activate)
        await pipe.execute()
    
    logger.debug(f"Activated {len(keys_to_activate)} keys from empty bucket.")


def setup_scheduler():
    """Sets up and starts the APScheduler."""
    global scheduler_instance
    scheduler = AsyncIOScheduler(timezone=str(settings.TIMEZONE))

    # The new, lightweight key activation job. Runs frequently.
    scheduler.add_job(
        activate_keys_from_empty_bucket,
        "interval",
        seconds=1,
        id="activate_keys_job",
        name="Activate Keys from Empty Bucket",
    )
    logger.info(
        "Key activation job scheduled to run every 1 second."
    )

    # Log cleanup jobs
    scheduler.add_job(
        delete_old_error_logs,
        "cron",
        hour=3,
        minute=0,
        id="delete_old_error_logs_job",
        name="Delete Old Error Logs",
    )
    logger.info("Auto-delete error logs job scheduled to run daily at 3:00 AM.")

    scheduler.add_job(
        delete_old_request_logs_task,
        "cron",
        hour=3,
        minute=5,
        id="delete_old_request_logs_job",
        name="Delete Old Request Logs",
    )
    logger.info(
        "Auto-delete request logs job scheduled to run daily at 3:05 AM."
    )

    # Daily reset for retired keys
    scheduler.add_job(
        reset_retired_keys_daily,
        "cron",
        hour=0,
        minute=0,
        second=5, # Run slightly after midnight
        id="reset_retired_keys_job",
        name="Reset Retired Keys Daily",
    )
    logger.info("Daily reset for retired keys scheduled to run at 00:00:05 UTC.")

    scheduler.start()
    scheduler_instance = scheduler
    logger.info("Scheduler started with all jobs.")
    return scheduler


def start_scheduler():
    global scheduler_instance
    if scheduler_instance is None or not scheduler_instance.running:
        logger.info("Starting scheduler...")
        scheduler_instance = setup_scheduler()
    else:
        logger.info("Scheduler is already running.")


def stop_scheduler():
    global scheduler_instance
    if scheduler_instance and scheduler_instance.running:
        scheduler_instance.shutdown()
        logger.info("Scheduler stopped.")
