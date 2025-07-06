"""
应用程序配置模块
"""

import logging
from app.log.logger import LOG_LEVELS
import asyncio
import datetime
import json
import time
from typing import Any, Dict, List, Optional, Type

from pydantic import ValidationError, ValidationInfo, field_validator
from pydantic_settings import BaseSettings
from sqlalchemy import insert, select, update

from app.core.constants import (
    API_VERSION,
    DEFAULT_CREATE_IMAGE_MODEL,
    DEFAULT_FILTER_MODELS,
    DEFAULT_MODEL,
    DEFAULT_SAFETY_SETTINGS,
    DEFAULT_STREAM_CHUNK_SIZE,
    DEFAULT_STREAM_LONG_TEXT_THRESHOLD,
    DEFAULT_STREAM_MAX_DELAY,
    DEFAULT_STREAM_MIN_DELAY,
    DEFAULT_STREAM_SHORT_TEXT_THRESHOLD,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
)



class Settings(BaseSettings):
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # 数据库配置
    DATABASE_TYPE: str = "mysql"
    SQLITE_DATABASE: str = "default_db"
    MYSQL_HOST: str = ""
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = ""
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = ""
    MYSQL_SOCKET: str = ""

    # 验证 MySQL 配置
    @field_validator(
        "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"
    )
    def validate_mysql_config(cls, v: Any, info: ValidationInfo) -> Any:
        if info.data.get("DATABASE_TYPE") == "mysql":
            if v is None or v == "":
                raise ValueError(
                    "MySQL configuration is required when DATABASE_TYPE is 'mysql'"
                )
        return v

    # API相关配置
    API_KEYS: List[str]

    @field_validator('API_KEYS', mode='before')
    @classmethod
    def parse_api_keys(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                # Attempt to parse as JSON list
                parsed = json.loads(v)
                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                    return parsed
            except json.JSONDecodeError:
                pass  # Not a JSON string, proceed to treat as single key
            # If not a JSON list, treat the whole string as a single key
            return [v]
        elif isinstance(v, list):
            return v
        return [] # Default to empty list if unexpected type
    ALLOWED_TOKENS: List[str]
    GEMINI_BASE_URL: List[str] = [f"https://generativelanguage.googleapis.com/{API_VERSION}"]

    @field_validator('GEMINI_BASE_URL', mode='before')
    @classmethod
    def validate_gemini_base_url(cls, v: Any) -> List[str]:
        logger = logging.getLogger(__name__)
        default_url = f"https://generativelanguage.googleapis.com/{API_VERSION}"

        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                    v = parsed
                else:
                    logger.warning(f"GEMINI_BASE_URL string '{v}' is not a valid JSON list. Treating as single URL.")
                    v = [v]
            except json.JSONDecodeError:
                logger.warning(f"GEMINI_BASE_URL string '{v}' is not JSON. Treating as single URL.")
                v = [v]
        elif not isinstance(v, list):
            logger.warning(f"GEMINI_BASE_URL received unexpected type {type(v)}. Defaulting to standard URL.")
            return [default_url]

        # Ensure all URLs have a protocol
        cleaned_urls = []
        for url in v:
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                logger.warning(f"Invalid URL '{url}' found in GEMINI_BASE_URL. Replacing with default.")
                cleaned_urls.append(default_url)
            else:
                cleaned_urls.append(url)
        
        if not cleaned_urls:
            logger.warning("GEMINI_BASE_URL list is empty after cleaning. Defaulting to standard URL.")
            return [default_url]

        return cleaned_urls
    GEMINI_BASE_URL_SELECTION_STRATEGY: str = "round_robin"  # round_robin, random, consistency_hash_by_api_key

    @field_validator('GEMINI_BASE_URL_SELECTION_STRATEGY', mode='after')
    @classmethod
    def validate_gemini_base_url_selection_strategy(cls, v: str) -> str:
        valid_strategies = ["round_robin", "random", "consistency_hash_by_api_key"]
        if v not in valid_strategies:
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid GEMINI_BASE_URL_SELECTION_STRATEGY '{v}' found. Defaulting to 'round_robin'.")
            return "round_robin"
        return v
    OPENAI_BASE_URL: List[str] = ["https://api.openai.com/v1"]
    OPENAI_BASE_URL_SELECTION_STRATEGY: str = "round_robin" # round_robin, random, consistency_hash_by_api_key
    AUTH_TOKEN: str = ""
    MAX_FAILURES: int = 3
    TEST_MODEL: str = DEFAULT_MODEL
    TIME_OUT: int = DEFAULT_TIMEOUT
    MAX_RETRIES: int = MAX_RETRIES
    RETRY_BASE_DELAY_SECONDS: int = 1 # 基础重试延迟（秒）
    RETRY_MAX_DELAY_SECONDS: int = 3 # 最大重试延迟（秒）
    GEMINI_RPM_LIMIT: int = 5
    PROXIES: List[str] = []
    PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY: bool = True  # 是否使用一致性哈希来选择代理
    VERTEX_API_KEYS: List[str] = []
    VERTEX_EXPRESS_BASE_URL: List[str] = ["https://aiplatform.googleapis.com/v1beta1/publishers/google"]

    @field_validator('VERTEX_EXPRESS_BASE_URL', mode='before')
    @classmethod
    def parse_vertex_express_base_url(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                    return parsed
            except json.JSONDecodeError:
                pass
            if v == "":
                return []
            return [v]
        elif isinstance(v, list):
            return v
        return []

    @field_validator('VERTEX_EXPRESS_BASE_URL', mode='before')
    @classmethod
    def validate_vertex_express_base_url(cls, v: Any) -> List[str]:
        logger = logging.getLogger(__name__)
        default_url = "https://aiplatform.googleapis.com/v1beta1/publishers/google"

        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                    v = parsed
                else:
                    logger.warning(f"VERTEX_EXPRESS_BASE_URL string '{v}' is not a valid JSON list. Treating as single URL.")
                    v = [v]
            except json.JSONDecodeError:
                logger.warning(f"VERTEX_EXPRESS_BASE_URL string '{v}' is not JSON. Treating as single URL.")
                v = [v]
        elif not isinstance(v, list):
            logger.warning(f"VERTEX_EXPRESS_BASE_URL received unexpected type {type(v)}. Defaulting to standard URL.")
            return [default_url]

        # Ensure all URLs have a protocol
        cleaned_urls = []
        for url in v:
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                logger.warning(f"Invalid URL '{url}' found in VERTEX_EXPRESS_BASE_URL. Replacing with default.")
                cleaned_urls.append(default_url)
            else:
                cleaned_urls.append(url)
        
        if not cleaned_urls:
            logger.warning("VERTEX_EXPRESS_BASE_URL list is empty after cleaning. Defaulting to standard URL.")
            return [default_url]

        return cleaned_urls

    @field_validator('VERTEX_EXPRESS_BASE_URL', mode='before')
    @classmethod
    def validate_vertex_express_base_url(cls, v: Any) -> List[str]:
        logger = logging.getLogger(__name__)
        default_url = "https://aiplatform.googleapis.com/v1beta1/publishers/google"

        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                    return parsed
            except json.JSONDecodeError:
                pass  # Not a JSON string, proceed to treat as single URL or empty list
            
            if v == "":
                return []
            else:
                logger.warning(f"VERTEX_EXPRESS_BASE_URL string '{v}' is not a valid JSON list. Treating as single URL.")
                return [v]
        elif isinstance(v, list):
            return v
        
        logger.warning(f"VERTEX_EXPRESS_BASE_URL received unexpected type {type(v)}. Defaulting to standard URL.")
        return [default_url]
    VERTEX_EXPRESS_BASE_URL_SELECTION_STRATEGY: str = "round_robin" # round_robin, random, consistency_hash_by_api_key
 
    # 模型相关配置
    SEARCH_MODELS: List[str] = ["gemini-2.0-flash-exp"]
    IMAGE_MODELS: List[str] = ["gemini-2.0-flash-exp"]
    FILTERED_MODELS: List[str] = DEFAULT_FILTER_MODELS
    TOOLS_CODE_EXECUTION_ENABLED: bool = False
    SHOW_SEARCH_LINK: bool = True
    SHOW_THINKING_PROCESS: bool = True
    THINKING_MODELS: List[str] = []
    THINKING_BUDGET_MAP: Dict[str, float] = {}

    # 图像生成相关配置
    PAID_KEY: str = ""
    CREATE_IMAGE_MODEL: str = DEFAULT_CREATE_IMAGE_MODEL
    UPLOAD_PROVIDER: str = "smms"
    SMMS_SECRET_TOKEN: str = ""
    PICGO_API_KEY: str = ""
    CLOUDFLARE_IMGBED_URL: str = ""
    CLOUDFLARE_IMGBED_AUTH_CODE: str = ""

    # 流式输出优化器配置
    STREAM_OPTIMIZER_ENABLED: bool = False
    STREAM_MIN_DELAY: float = DEFAULT_STREAM_MIN_DELAY
    STREAM_MAX_DELAY: float = DEFAULT_STREAM_MAX_DELAY
    STREAM_SHORT_TEXT_THRESHOLD: int = DEFAULT_STREAM_SHORT_TEXT_THRESHOLD
    STREAM_LONG_TEXT_THRESHOLD: int = DEFAULT_STREAM_LONG_TEXT_THRESHOLD
    STREAM_CHUNK_SIZE: int = DEFAULT_STREAM_CHUNK_SIZE

    # 假流式配置 (Fake Streaming Configuration)
    FAKE_STREAM_ENABLED: bool = False  # 是否启用假流式输出
    FAKE_STREAM_EMPTY_DATA_INTERVAL_SECONDS: int = 5  # 假流式发送空数据的间隔时间（秒）

    # 调度器配置
    CHECK_INTERVAL_HOURS: int = 1  # 默认检查间隔为1小时
    LIMITED_KEY_VERIFICATION_ENABLED: bool = True
    LIMITED_KEY_VERIFICATION_MIN_INTERVAL_HOURS: int = 1
    LIMITED_KEY_VERIFICATION_MAX_INTERVAL_HOURS: int = 2
    TIMEZONE: str = "Asia/Shanghai"  # 默认时区
    INITIAL_COOLDOWN_SECONDS: int = 3600  # 初始冷却时间（秒）
    REVALIDATION_INTERVAL_MINUTES: int = 1 # 重新验证工作器运行间隔（分钟）
    MAX_REVALIDATIONS_PER_RUN: int = 20 # 每次重新验证工作器运行时检查的最大密钥数
    IMMEDIATE_COOLDOWN_SECONDS: int = 60 # 任何失败后的即时冷却时间（秒）

    # Global Circuit Breaker
    GLOBAL_FAILURE_THRESHOLD: int = 50 # 在断路器跳闸前，一分钟内允许的全局5xx错误数
    GLOBAL_COOLDOWN_SECONDS: int = 60 # 全局断路器跳闸后的冷却时间（秒）

    # Rate Limiting
    DEFAULT_RPM: int = 5
    DEFAULT_RPD: int = 100
    MODEL_RATE_LIMITS: Dict[str, List[int]] = {}
    KEY_RATE_LIMITS: Dict[str, List[int]] = {}

    @field_validator('MODEL_RATE_LIMITS', 'KEY_RATE_LIMITS', mode='before')
    @classmethod
    def parse_rate_limits(cls, v: Any) -> Dict[str, List[int]]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v

    # github
    GITHUB_REPO_OWNER: str = "snailyp"
    GITHUB_REPO_NAME: str = "gemini-balance"

    # 日志配置
    LOG_LEVEL: str = "DEBUG"
    AUTO_DELETE_ERROR_LOGS_ENABLED: bool = True
    AUTO_DELETE_ERROR_LOGS_DAYS: int = 7
    AUTO_DELETE_REQUEST_LOGS_ENABLED: bool = False
    AUTO_DELETE_REQUEST_LOGS_DAYS: int = 30
    SAFETY_SETTINGS: List[Dict[str, str]] = DEFAULT_SAFETY_SETTINGS

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 设置默认AUTH_TOKEN（如果未提供）
        if not self.AUTH_TOKEN and self.ALLOWED_TOKENS:
            self.AUTH_TOKEN = self.ALLOWED_TOKENS[0]


# 创建全局配置实例
settings = Settings()


def _parse_db_value(key: str, db_value: str, target_type: Type) -> Any:
    """尝试将数据库字符串值解析为目标 Python 类型"""
    logger = logging.getLogger(__name__)
    try:
        # Special handling for GEMINI_BASE_URL_SELECTION_STRATEGY
        if key == "GEMINI_BASE_URL_SELECTION_STRATEGY":
            return str(db_value)
        # 处理 List[str]
        if target_type == List[str]:
            try:
                parsed = json.loads(db_value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                return [item.strip() for item in db_value.split(",") if item.strip()]
            logger.warning(
                f"Could not parse '{db_value}' as List[str] for key '{key}', falling back to comma split or empty list."
            )
            return [item.strip() for item in db_value.split(",") if item.strip()]
        # 处理 Dict[str, float]
        elif target_type == Dict[str, float]:
            parsed_dict = {}
            try:
                parsed = json.loads(db_value)
                if isinstance(parsed, dict):
                    parsed_dict = {str(k): float(v) for k, v in parsed.items()}
                else:
                    logger.warning(
                        f"Parsed DB value for key '{key}' is not a dictionary type. Value: {db_value}"
                    )
            except (json.JSONDecodeError, ValueError, TypeError) as e1:
                if isinstance(e1, json.JSONDecodeError) and "'" in db_value:
                    logger.warning(
                        f"Failed initial JSON parse for key '{key}'. Attempting to replace single quotes. Error: {e1}"
                    )
                    try:
                        corrected_db_value = db_value.replace("'", '"')
                        parsed = json.loads(corrected_db_value)
                        if isinstance(parsed, dict):
                            parsed_dict = {str(k): float(v) for k, v in parsed.items()}
                        else:
                            logger.warning(
                                f"Parsed DB value (after quote replacement) for key '{key}' is not a dictionary type. Value: {corrected_db_value}"
                            )
                    except (json.JSONDecodeError, ValueError, TypeError) as e2:
                        logger.error(
                            f"Could not parse '{db_value}' as Dict[str, float] for key '{key}' even after replacing quotes: {e2}. Returning empty dict."
                        )
                else:
                    logger.error(
                        f"Could not parse '{db_value}' as Dict[str, float] for key '{key}': {e1}. Returning empty dict."
                    )
            return parsed_dict
        # 处理 List[Dict[str, str]]
        elif target_type == List[Dict[str, str]]:
            try:
                parsed = json.loads(db_value)
                if isinstance(parsed, list):
                    # 验证列表中的每个元素是否为字典，并且键和值都是字符串
                    valid = all(
                        isinstance(item, dict)
                        and all(isinstance(k, str) for k in item.keys())
                        and all(isinstance(v, str) for v in item.values())
                        for item in parsed
                    )
                    if valid:
                        return parsed
                    else:
                        logger.warning(
                            f"Invalid structure in List[Dict[str, str]] for key '{key}'. Value: {db_value}"
                        )
                        return []
                else:
                    logger.warning(
                        f"Parsed DB value for key '{key}' is not a list type. Value: {db_value}"
                    )
                    return []
            except json.JSONDecodeError:
                logger.error(
                    f"Could not parse '{db_value}' as JSON for List[Dict[str, str]] for key '{key}'. Returning empty list."
                )
                return []
            except Exception as e:
                logger.error(
                    f"Error parsing List[Dict[str, str]] for key '{key}': {e}. Value: {db_value}. Returning empty list."
                )
                return []
        # 处理 bool
        elif target_type == bool:
            return db_value.lower() in ("true", "1", "yes", "on")
        # 处理 int
        elif target_type == int:
            return int(db_value)
        # 处理 float
        elif target_type == float:
            return float(db_value)
        # 处理 str
        elif target_type == str:
            return str(db_value)
        # 默认为其他 pydantic 能直接处理的类型
        else:
            return db_value
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        logger.warning(
            f"Failed to parse db_value '{db_value}' for key '{key}' as type {target_type}: {e}. Using original string value."
        )
        return db_value  # 解析失败则返回原始字符串


async def sync_initial_settings():
    """
    应用启动时同步配置：
    1. 从数据库加载设置。
    2. 将数据库设置合并到内存 settings (数据库优先)。
    3. 将最终的内存 settings 同步回数据库。
    """
    logger = logging.getLogger(__name__)
    # 延迟导入以避免循环依赖和确保数据库连接已初始化
    from app.database.connection import database
    from app.database.models import Settings as SettingsModel

    global settings
    logger.info("Starting initial settings synchronization...")

    

    try:
        # 1. 从数据库加载设置
        db_settings_raw: List[Dict[str, Any]] = []
        try:
            query = select(SettingsModel.key, SettingsModel.value)
            results = await database.fetch_all(query)
            db_settings_raw = [
                {"key": row["key"], "value": row["value"]} for row in results
            ]
            logger.info(f"Fetched {len(db_settings_raw)} settings from database.")
        except Exception as e:
            logger.error(
                f"Failed to fetch settings from database: {e}. Proceeding with environment/dotenv settings."
            )
            # 即使数据库读取失败，也要继续执行，确保基于 env/dotenv 的配置能同步到数据库

        db_settings_map: Dict[str, str] = {
            s["key"]: s["value"] for s in db_settings_raw
        }

        # 2. 将数据库设置合并到内存 settings (数据库优先)
        updated_in_memory = False

        for key, db_value in db_settings_map.items():
            if key == "DATABASE_TYPE":
                logger.debug(
                    f"Skipping update of '{key}' in memory from database. "
                    "This setting is controlled by environment/dotenv."
                )
                continue
            if hasattr(settings, key):
                target_type = Settings.__annotations__.get(key)
                if target_type:
                    try:
                        parsed_db_value = _parse_db_value(key, db_value, target_type)
                        memory_value = getattr(settings, key)

                        # Special handling for GEMINI_BASE_URL to prioritize environment variable
                        if key == "GEMINI_BASE_URL" and settings.BASE_URL:
                            if parsed_db_value != [settings.BASE_URL]:
                                setattr(settings, key, [settings.BASE_URL])
                                logger.debug(
                                    f"Prioritizing environment BASE_URL for GEMINI_BASE_URL. Updated to {[settings.BASE_URL]}."
                                )
                                updated_in_memory = True
                            continue # Skip further processing for this key

                        # 比较解析后的值和内存中的值
                        # 注意：对于列表等复杂类型，直接比较可能不够健壮，但这里简化处理
                        if parsed_db_value != memory_value:
                            # 检查类型是否匹配，以防解析函数返回了不兼容的类型
                            type_match = False
                            if target_type == List[str] and isinstance(
                                parsed_db_value, list
                            ):
                                type_match = True
                            elif target_type == Dict[str, float] and isinstance(
                                parsed_db_value, dict
                            ):
                                type_match = True
                            elif target_type not in (
                                List[str],
                                Dict[str, float],
                            ) and isinstance(parsed_db_value, target_type):
                                type_match = True

                            if type_match:
                                setattr(settings, key, parsed_db_value)
                                logger.debug(
                                    f"Updated setting '{key}' in memory from database value ({target_type})."
                                )
                                updated_in_memory = True
                            else:
                                logger.warning(
                                    f"Parsed DB value type mismatch for key '{key}'. Expected {target_type}, got {type(parsed_db_value)}. Skipping update."
                                )

                    except Exception as e:
                        logger.error(
                            f"Error processing database setting for key '{key}': {e}"
                        )
            else:
                logger.warning(
                    f"Database setting '{key}' not found in Settings model definition. Ignoring."
                )

        # 如果内存中有更新，重新验证 Pydantic 模型（可选但推荐）
        if updated_in_memory:
            try:
                # 重新加载以确保类型转换和验证
                settings = Settings(**settings.model_dump())
                logger.info(
                    "Settings object re-validated after merging database values."
                )
            except ValidationError as e:
                logger.error(
                    f"Validation error after merging database settings: {e}. Settings might be inconsistent."
                )

        # 强制校验和修正 GEMINI_BASE_URL_SELECTION_STRATEGY
        valid_strategies = ["round_robin", "random", "consistency_hash_by_api_key"]
        if settings.GEMINI_BASE_URL_SELECTION_STRATEGY not in valid_strategies:
            logger.warning(
                f"Invalid GEMINI_BASE_URL_SELECTION_STRATEGY '{settings.GEMINI_BASE_URL_SELECTION_STRATEGY}' found. Forcing to 'round_robin'."
            )
            settings.GEMINI_BASE_URL_SELECTION_STRATEGY = "round_robin"

        # 强制校验和修正 GEMINI_BASE_URL
        default_gemini_base_url = f"https://generativelanguage.googleapis.com/{API_VERSION}"
        if not settings.GEMINI_BASE_URL or not all(url.startswith(("http://", "https://")) for url in settings.GEMINI_BASE_URL):
            logger.warning(
                f"Invalid GEMINI_BASE_URL '{settings.GEMINI_BASE_URL}' found. Forcing to default: '{default_gemini_base_url}'."
            )
            settings.GEMINI_BASE_URL = [default_gemini_base_url]

        # 3. 将最终的内存 settings 同步回数据库
        final_memory_settings = settings.model_dump()
        settings_to_update: List[Dict[str, Any]] = []
        settings_to_insert: List[Dict[str, Any]] = []
        now = datetime.datetime.now(datetime.timezone.utc)

        existing_db_keys = set(db_settings_map.keys())

        for key, value in final_memory_settings.items():
            if key == "DATABASE_TYPE":
                logger.debug(
                    f"Skipping synchronization of '{key}' to database. "
                    "This setting is controlled by environment/dotenv."
                )
                continue

            # 序列化值为字符串或 JSON 字符串
            if isinstance(value, (list, dict)):
                db_value = json.dumps(
                    value, ensure_ascii=False
                )
            elif isinstance(value, bool):
                db_value = str(value).lower()
            elif value is None:
                db_value = ""
            else:
                db_value = str(value)

            data = {
                "key": key,
                "value": db_value,
                "description": f"{key} configuration setting",
                "updated_at": now,
            }

            if key in existing_db_keys:
                # 仅当值与数据库中的不同时才更新
                if db_settings_map[key] != db_value:
                    settings_to_update.append(data)
            else:
                # 如果键不在数据库中，则插入
                data["created_at"] = now
                settings_to_insert.append(data)

        # 在事务中执行批量插入和更新
        if settings_to_insert or settings_to_update:
            try:
                async with database.transaction():
                    if settings_to_insert:
                        # 获取现有描述以避免覆盖
                        query_existing = select(
                            SettingsModel.key, SettingsModel.description
                        ).where(
                            SettingsModel.key.in_(
                                [s["key"] for s in settings_to_insert]
                            )
                        )
                        existing_desc = {
                            row["key"]: row["description"]
                            for row in await database.fetch_all(query_existing)
                        }
                        for item in settings_to_insert:
                            item["description"] = existing_desc.get(
                                item["key"], item["description"]
                            )

                        query_insert = insert(SettingsModel).values(settings_to_insert)
                        await database.execute(query=query_insert)
                        logger.info(
                            f"Synced (inserted) {len(settings_to_insert)} settings to database."
                        )

                    if settings_to_update:
                        # 获取现有描述以避免覆盖
                        query_existing = select(
                            SettingsModel.key, SettingsModel.description
                        ).where(
                            SettingsModel.key.in_(
                                [s["key"] for s in settings_to_update]
                            )
                        )
                        existing_desc = {
                            row["key"]: row["description"]
                            for row in await database.fetch_all(query_existing)
                        }

                        for setting_data in settings_to_update:
                            setting_data["description"] = existing_desc.get(
                                setting_data["key"], setting_data["description"]
                            )
                            query_update = (
                                update(SettingsModel)
                                .where(SettingsModel.key == setting_data["key"])
                                .values(
                                    value=setting_data["value"],
                                    description=setting_data["description"],
                                    updated_at=setting_data["updated_at"],
                                )
                            )
                            await database.execute(query=query_update)
                        logger.info(
                            f"Synced (updated) {len(settings_to_update)} settings to database."
                        )
            except Exception as e:
                logger.error(
                    f"Failed to sync settings to database during startup: {str(e)}"
                )
        else:
            logger.info(
                "No setting changes detected between memory and database during initial sync."
            )

        # 刷新日志等级
        log_level_str = final_memory_settings.get("LOG_LEVEL", "info").lower()
        new_level = LOG_LEVELS.get(log_level_str, logging.INFO)
        for logger_name, logger_instance in logging.root.manager.loggerDict.items():
            if isinstance(logger_instance, logging.Logger):
                logger_instance.setLevel(new_level)

    except Exception as e:
        logger.error(f"An unexpected error occurred during initial settings sync: {e}")
    

    logger.info("Initial settings synchronization finished.")
