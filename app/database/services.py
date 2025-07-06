import datetime
from sqlalchemy.orm import Session
from app.database.connection import engine, database
from app.database.models import APIKey, ErrorLog, RequestLog, Settings as SettingsModel
from app.config.config import settings
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, desc, asc, and_
from app.log.logger import get_database_logger

logger = get_database_logger()

class APIKeyService:
    async def get_total_keys_count(self) -> int:
        query = select(func.count(APIKey.id))
        return await database.fetch_val(query)

    async def get_banned_keys_count(self) -> int:
        query = select(func.count(APIKey.id)).where(APIKey.status == "banned")
        return await database.fetch_val(query)
    async def sync_keys_from_config(self):
        # 获取数据库中所有的key
        query_db_keys = select(APIKey.key_value)
        db_keys_result = await database.fetch_all(query_db_keys)
        db_keys = {row["key_value"] for row in db_keys_result}
        logger.info(f"Existing DB keys: {db_keys}")
        
        # 获取配置文件中所有的key
        config_keys = set(settings.API_KEYS)
        logger.info(f"Configured API_KEYS: {config_keys}")
        
        # 添加新的key
        new_keys = config_keys - db_keys
        logger.info(f"New keys to insert: {new_keys}")
        for key_value in new_keys:
            insert_query = APIKey.__table__.insert().values(key_value=key_value, service="gemini", status="active")
            await database.execute(insert_query)
        if new_keys:
            logger.info(f"Successfully inserted {len(new_keys)} new API keys.")
        else:
            logger.info("No new API keys to insert.")

    async def get_active_keys(self, service: str) -> list[APIKey]:
        query = select(APIKey).where(APIKey.service == service, APIKey.status == "active")
        results = await database.fetch_all(query)
        return [APIKey(**dict(row)) for row in results]

    async def get_limited_keys(self, service: str) -> list[APIKey]:
        query = select(APIKey).where(APIKey.service == service, APIKey.status == "limited")
        results = await database.fetch_all(query)
        return [APIKey(**dict(row)) for row in results]

    async def get_banned_keys(self, service: str) -> list[APIKey]:
        query = select(APIKey).where(APIKey.service == service, APIKey.status == "banned")
        results = await database.fetch_all(query)
        return [APIKey(**dict(row)) for row in results]

    async def mark_key_as_limited(self, key_value: str):
        update_query = APIKey.__table__.update().where(APIKey.key_value == key_value).values(
            status="limited"
        )
        await database.execute(update_query)

    async def mark_key_as_banned(self, key_value: str):
        update_query = APIKey.__table__.update().where(APIKey.key_value == key_value).values(
            status="banned",
            banned_at=datetime.datetime.now()
        )
        await database.execute(update_query)

    async def reset_key_status_to_active(self, key_value: str):
        update_query = APIKey.__table__.update().where(APIKey.key_value == key_value).values(
            status="active",
            failure_count=0,
            banned_at=None # Clear banned_at timestamp
        )
        await database.execute(update_query)

    async def get_all_keys(self, service: str) -> list[APIKey]:
        query = select(APIKey).where(APIKey.service == service)
        results = await database.fetch_all(query)
        return [APIKey(**dict(row)) for row in results]

    async def is_key_active(self, key_value: str) -> bool:
        """Checks if a key is active in the database."""
        query = select(APIKey.status).where(APIKey.key_value == key_value)
        result = await database.fetch_one(query)
        if not result:
            return False
        return result['status'] != 'banned'

    async def get_daily_banned_key_stats(self):
        query = (
            select(
                func.date(APIKey.banned_at).label("date"),
                func.count(APIKey.id).label("count"),
            )
            .where(APIKey.status == "banned", APIKey.banned_at.isnot(None))
            .group_by(func.date(APIKey.banned_at))
            .order_by(desc(func.date(APIKey.banned_at)))
        )
        results = await database.fetch_all(query)
        return [dict(row) for row in results]

    async def reset_all_limited_keys_status(self):
        """Resets the status of all 'limited' API keys to 'active' and sets failure_count to 0."""
        update_query = APIKey.__table__.update().where(APIKey.status == "limited").values(
            status="active",
            failure_count=0
        )
        await database.execute(update_query)
        logger.info("All 'limited' API keys have been reset to 'active' status.")


class ErrorLogService:
    async def add_log(
        self,
        gemini_key: str,
        model_name: str,
        error_type: str,
        error_log: str,
        error_code: int,
        request_msg: Dict[str, Any],
    ):
        query = ErrorLog.__table__.insert().values(
            gemini_key=gemini_key,
            model_name=model_name,
            error_type=error_type,
            error_log=error_log,
            error_code=error_code,
            request_msg=request_msg,
            request_time=datetime.datetime.now(),
        )
        await database.execute(query)

    async def get_error_logs(
        self,
        limit: int,
        offset: int,
        key_search: Optional[str],
        error_search: Optional[str],
        error_code_search: Optional[str],
        start_date: Optional[datetime.datetime],
        end_date: Optional[datetime.datetime],
        sort_by: str,
        sort_order: str,
    ) -> List[Dict[str, Any]]:
        query = select(ErrorLog)
        conditions = []
        if key_search:
            conditions.append(ErrorLog.gemini_key.like(f"%{key_search}%"))
        if error_search:
            conditions.append(ErrorLog.error_log.like(f"%{error_search}%"))
        if error_code_search:
            conditions.append(ErrorLog.error_code == int(error_code_search))
        if start_date:
            conditions.append(ErrorLog.request_time >= start_date)
        if end_date:
            conditions.append(ErrorLog.request_time <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        if sort_by == "request_time":
            if sort_order == "desc":
                query = query.order_by(desc(ErrorLog.request_time))
            else:
                query = query.order_by(asc(ErrorLog.request_time))
        elif sort_by == "error_code":
            if sort_order == "desc":
                query = query.order_by(desc(ErrorLog.error_code))
            else:
                query = query.order_by(asc(ErrorLog.error_code))

        query = query.limit(limit).offset(offset)
        
        results = await database.fetch_all(query)
        return [dict(row) for row in results]

    async def get_error_logs_count(
        self,
        key_search: Optional[str],
        error_search: Optional[str],
        error_code_search: Optional[str],
        start_date: Optional[datetime.datetime],
        end_date: Optional[datetime.datetime],
    ) -> int:
        query = select(func.count(ErrorLog.id))
        conditions = []
        if key_search:
            conditions.append(ErrorLog.gemini_key.like(f"%{key_search}%"))
        if error_search:
            conditions.append(ErrorLog.error_log.like(f"%{error_search}%"))
        if error_code_search:
            conditions.append(ErrorLog.error_code == int(error_code_search))
        if start_date:
            conditions.append(ErrorLog.request_time >= start_date)
        if end_date:
            conditions.append(ErrorLog.request_time <= end_date)

        if conditions:
            query = query.where(and_(*conditions))
        
        return await database.fetch_val(query)

    async def get_error_log_details(self, log_id: int) -> Optional[Dict[str, Any]]:
        query = select(ErrorLog).where(ErrorLog.id == log_id)
        result = await database.fetch_one(query)
        return dict(result) if result else None

    async def delete_error_logs_by_ids(self, log_ids: List[int]) -> int:
        query = ErrorLog.__table__.delete().where(ErrorLog.id.in_(log_ids))
        await database.execute(query)
        return len(log_ids) # Assuming all requested IDs are deleted

    async def delete_error_log_by_id(self, log_id: int) -> bool:
        query = ErrorLog.__table__.delete().where(ErrorLog.id == log_id)
        result = await database.execute(query)
        return result > 0

    async def delete_all_error_logs(self) -> int:
        query = ErrorLog.__table__.delete()
        result = await database.execute(query)
        return result


class RequestLogService:
    async def add_log(
        self,
        model_name: str,
        api_key: str,
        is_success: bool,
        status_code: int,
        latency_ms: int,
        request_time: datetime.datetime,
    ):
        query = RequestLog.__table__.insert().values(
            model_name=model_name,
            api_key=api_key,
            is_success=is_success,
            status_code=status_code,
            latency_ms=latency_ms,
            request_time=request_time,
        )
        await database.execute(query)

class SettingsService:
    async def get_all_settings(self) -> List[Dict[str, Any]]:
        query = select(SettingsModel.key, SettingsModel.value, SettingsModel.description)
        results = await database.fetch_all(query)
        return [{"key": row["key"], "value": row["value"], "description": row["description"]} for row in results]

api_key_service = APIKeyService()
error_log_service = ErrorLogService()
request_log_service = RequestLogService()
settings_service = SettingsService()
