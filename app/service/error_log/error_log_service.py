from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select

from app.config.config import settings
from app.database import services as db_services
from app.database.connection import database
from app.database.models import ErrorLog
from app.log.logger import get_error_log_logger

logger = get_error_log_logger()


async def delete_old_error_logs():
    """
    Deletes error logs older than a specified number of days,
    based on the AUTO_DELETE_ERROR_LOGS_ENABLED and AUTO_DELETE_ERROR_LOGS_DAYS settings.
    """
    if not settings.AUTO_DELETE_ERROR_LOGS_ENABLED:
        logger.info("Auto-deletion of error logs is disabled. Skipping.")
        return

    days_to_keep = settings.AUTO_DELETE_ERROR_LOGS_DAYS
    if not isinstance(days_to_keep, int) or days_to_keep <= 0:
        logger.error(
            f"Invalid AUTO_DELETE_ERROR_LOGS_DAYS value: {days_to_keep}. Must be a positive integer. Skipping deletion."
        )
        return

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

    logger.info(
        f"Attempting to delete error logs older than {days_to_keep} days (before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S %Z')})."
    )

    try:
        if not database.is_connected:
            await database.connect()
            logger.info("Database connection established for deleting error logs.")

        # First, count how many logs will be deleted (optional, for logging)
        count_query = select(func.count(ErrorLog.id)).where(
            ErrorLog.request_time < cutoff_date
        )
        num_logs_to_delete = await database.fetch_val(count_query)

        if num_logs_to_delete == 0:
            logger.info(
                "No error logs found older than the specified period. No deletion needed."
            )
            return

        logger.info(f"Found {num_logs_to_delete} error logs to delete.")

        # Perform the deletion
        query = delete(ErrorLog).where(ErrorLog.request_time < cutoff_date)
        await database.execute(query)
        logger.info(
            f"Successfully deleted {num_logs_to_delete} error logs older than {days_to_keep} days."
        )

    except Exception as e:
        logger.error(
            f"Error during automatic deletion of error logs: {e}", exc_info=True
        )


async def process_get_error_logs(
    limit: int,
    offset: int,
    key_search: Optional[str],
    error_search: Optional[str],
    error_code_search: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    sort_by: str,
    sort_order: str,
) -> Dict[str, Any]:
    """
    处理错误日志的检索，支持分页和过滤。
    """
    try:
        logs_data = await db_services.get_error_logs(
            limit=limit,
            offset=offset,
            key_search=key_search,
            error_search=error_search,
            error_code_search=error_code_search,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_count = await db_services.get_error_logs_count(
            key_search=key_search,
            error_search=error_search,
            error_code_search=error_code_search,
            start_date=start_date,
            end_date=end_date,
        )
        return {"logs": logs_data, "total": total_count}
    except Exception as e:
        logger.error(f"Service error in process_get_error_logs: {e}", exc_info=True)
        raise


async def process_get_error_logs_by_key(key: str) -> Dict[str, Any]:
    """
    按 API 密钥检索所有错误日志。
    """
    try:
        logs_data = await db_services.get_error_logs(key_search=key, limit=1000, offset=0) # Limit to 1000 for safety
        total_count = await db_services.get_error_logs_count(key_search=key)
        return {"logs": logs_data, "total": total_count}
    except Exception as e:
        logger.error(f"Service error in process_get_error_logs_by_key for key {key}: {e}", exc_info=True)
        raise


async def process_get_error_log_details(log_id: int) -> Optional[Dict[str, Any]]:
    """
    处理特定错误日志详细信息的检索。
    如果未找到，则返回 None。
    """
    try:
        log_details = await db_services.get_error_log_details(log_id=log_id)
        return log_details
    except Exception as e:
        logger.error(
            f"Service error in process_get_error_log_details for ID {log_id}: {e}",
            exc_info=True,
        )
        raise


async def process_delete_error_logs_by_ids(log_ids: List[int]) -> int:
    """
    按 ID 批量删除错误日志。
    返回尝试删除的日志数量。
    """
    if not log_ids:
        return 0
    try:
        deleted_count = await db_services.delete_error_logs_by_ids(log_ids)
        return deleted_count
    except Exception as e:
        logger.error(
            f"Service error in process_delete_error_logs_by_ids for IDs {log_ids}: {e}",
            exc_info=True,
        )
        raise


async def process_delete_error_log_by_id(log_id: int) -> bool:
    """
    按 ID 删除单个错误日志。
    如果删除成功（或找到日志并尝试删除），则返回 True，否则返回 False。
    """
    try:
        success = await db_services.delete_error_log_by_id(log_id)
        return success
    except Exception as e:
        logger.error(
            f"Service error in process_delete_error_log_by_id for ID {log_id}: {e}",
            exc_info=True,
        )
        raise


async def process_delete_all_error_logs() -> int:
    """
    处理删除所有错误日志的请求。
    返回删除的日志数量。
    """
    try:
        if not database.is_connected:
            await database.connect()
            logger.info("Database connection established for deleting all error logs.")

        deleted_count = await db_services.delete_all_error_logs()
        logger.info(
            f"Successfully processed request to delete all error logs. Count: {deleted_count}"
        )
        return deleted_count
    except Exception as e:
        logger.error(
            f"Service error in process_delete_all_error_logs: {e}",
            exc_info=True,
        )
        raise
