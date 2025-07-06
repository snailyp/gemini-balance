"""
配置服务模块
"""

import datetime
import json
from typing import Any, Dict, List

from dotenv import find_dotenv, load_dotenv
from fastapi import HTTPException
from sqlalchemy import insert, update

from app.config.config import Settings as ConfigSettings
from app.config.config import settings
from app.database.connection import database
from app.database.models import Settings
from app.database.services import settings_service
from app.log.logger import get_config_routes_logger
from app.service.key.key_manager import (
    get_key_manager_instance,
    reset_key_manager_instance,
)
from app.database.services import settings_service, api_key_service
from app.log.logger import get_config_routes_logger
from app.service.key.key_manager import (
    get_key_manager_instance,
    reset_key_manager_instance,
)
from app.service.model.model_service import ModelService

logger = get_config_routes_logger()


class ConfigService:
    """配置服务类，用于管理应用程序配置"""

    @staticmethod
    async def get_config() -> Dict[str, Any]:
        return settings.model_dump()

    @staticmethod
    async def update_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in config_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
                logger.debug(f"Updated setting in memory: {key}")

        # 重新验证 settings 对象以触发所有 field_validator
        try:
            settings.__init__(**settings.model_dump())
            logger.info("Settings object re-validated after in-memory update.")
        except Exception as e:
            logger.error(f"Error re-validating settings after update: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"配置验证失败: {str(e)}")

        # 获取现有设置
        existing_settings_raw: List[Dict[str, Any]] = await settings_service.get_all_settings()
        existing_settings_map: Dict[str, Dict[str, Any]] = {
            s["key"]: s for s in existing_settings_raw
        }
        existing_keys = set(existing_settings_map.keys())

        settings_to_update: List[Dict[str, Any]] = []
        settings_to_insert: List[Dict[str, Any]] = []
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

        # 准备要更新或插入的数据
        for key, value in config_data.items():
            # 处理不同类型的值
            if isinstance(value, list):
                db_value = json.dumps(value)
            elif isinstance(value, dict):
                db_value = json.dumps(value)
            elif isinstance(value, bool):
                db_value = str(value).lower()
            else:
                db_value = str(value)

            # 仅当值发生变化时才更新
            if key in existing_keys and existing_settings_map[key]["value"] == db_value:
                continue

            description = f"{key}配置项"

            data = {
                "key": key,
                "value": db_value,
                "description": description,
                "updated_at": now,
            }

            if key in existing_keys:
                data["description"] = existing_settings_map[key].get(
                    "description", description
                )
                settings_to_update.append(data)
            else:
                data["created_at"] = now
                settings_to_insert.append(data)

        # 在事务中执行批量插入和更新
        if settings_to_insert or settings_to_update:
            try:
                async with database.transaction():
                    if settings_to_insert:
                        query_insert = insert(Settings).values(settings_to_insert)
                        await database.execute(query=query_insert)
                        logger.info(
                            f"Bulk inserted {len(settings_to_insert)} settings."
                        )

                    if settings_to_update:
                        for setting_data in settings_to_update:
                            query_update = (
                                update(Settings)
                                .where(Settings.key == setting_data["key"])
                                .values(
                                    value=setting_data["value"],
                                    description=setting_data["description"],
                                    updated_at=setting_data["updated_at"],
                                )
                            )
                            await database.execute(query=query_update)
                        logger.info(f"Updated {len(settings_to_update)} settings.")
            except Exception as e:
                logger.error(f"Failed to bulk update/insert settings: {str(e)}")
                raise

        # 同步 API 密钥到 t_api_keys 表
        await api_key_service.sync_keys_from_config()

        # 重置并重新初始化 KeyManager
        try:
            await reset_key_manager_instance()
            await get_key_manager_instance()
            logger.info("KeyManager instance re-initialized with updated settings.")
        except Exception as e:
            logger.error(f"Failed to re-initialize KeyManager: {str(e)}")

        return await ConfigService.get_config()

    @staticmethod
    async def delete_key(key_to_delete: str) -> Dict[str, Any]:
        """删除单个API密钥"""
        # 确保 settings.API_KEYS 是一个列表
        if not isinstance(settings.API_KEYS, list):
            settings.API_KEYS = []

        original_keys_count = len(settings.API_KEYS)
        # 创建一个不包含待删除密钥的新列表
        updated_api_keys = [k for k in settings.API_KEYS if k != key_to_delete]

        if len(updated_api_keys) < original_keys_count:
            # 密钥已找到并从列表中移除
            settings.API_KEYS = updated_api_keys  # 首先更新内存中的 settings
            # 使用 update_config 持久化更改，它同时处理数据库和 KeyManager
            await ConfigService.update_config({"API_KEYS": settings.API_KEYS})
            logger.info(f"密钥 '{key_to_delete}' 已成功删除。")
            return {"success": True, "message": f"密钥 '{key_to_delete}' 已成功删除。"}
        else:
            # 未找到密钥
            logger.warning(f"尝试删除密钥 '{key_to_delete}'，但未找到该密钥。")
            return {"success": False, "message": f"未找到密钥 '{key_to_delete}'。"}

    @staticmethod
    async def delete_selected_keys(keys_to_delete: List[str]) -> Dict[str, Any]:
        """批量删除选定的API密钥"""
        if not isinstance(settings.API_KEYS, list):
            settings.API_KEYS = []

        deleted_count = 0
        not_found_keys: List[str] = []

        current_api_keys = list(settings.API_KEYS)
        keys_actually_removed: List[str] = []

        for key_to_del in keys_to_delete:
            if key_to_del in current_api_keys:
                current_api_keys.remove(key_to_del)
                keys_actually_removed.append(key_to_del)
                deleted_count += 1
            else:
                not_found_keys.append(key_to_del)

        if deleted_count > 0:
            settings.API_KEYS = current_api_keys
            await ConfigService.update_config({"API_KEYS": settings.API_KEYS})
            logger.info(
                f"成功删除 {deleted_count} 个密钥。密钥: {keys_actually_removed}"
            )
            message = f"成功删除 {deleted_count} 个密钥。"
            if not_found_keys:
                message += f" {len(not_found_keys)} 个密钥未找到: {not_found_keys}。"
            return {
                "success": True,
                "message": message,
                "deleted_count": deleted_count,
                "not_found_keys": not_found_keys,
            }
        else:
            message = "没有密钥被删除。"
            if not_found_keys:
                message = f"所有 {len(not_found_keys)} 个指定的密钥均未找到: {not_found_keys}。"
            elif not keys_to_delete:
                message = "未指定要删除的密钥。"
            logger.warning(message)
            return {
                "success": False,
                "message": message,
                "deleted_count": 0,
                "not_found_keys": not_found_keys,
            }

    @staticmethod
    async def reset_config() -> Dict[str, Any]:
        """
        重置配置：优先从系统环境变量加载，然后从 .env 文件加载，
        更新内存中的 settings 对象，并刷新 KeyManager。

        Returns:
            Dict[str, Any]: 重置后的配置字典
        """
        # 1. 重新加载配置对象，它应该处理环境变量和 .env 的优先级
        _reload_settings()
        logger.info(
            "Settings object reloaded, prioritizing system environment variables then .env file."
        )

        # 2. 重置并重新初始化 KeyManager
        try:
            await reset_key_manager_instance()
            # 确保使用更新后的 settings 中的 API_KEYS
            await get_key_manager_instance()
            logger.info("KeyManager instance re-initialized with reloaded settings.")
        except Exception as e:
            logger.error(f"Failed to re-initialize KeyManager during reset: {str(e)}")
            # 根据需要决定是否抛出异常或继续
            # 这里选择记录错误并继续

        # 3. 返回更新后的配置
        return await ConfigService.get_config()

    @staticmethod
    async def fetch_ui_models() -> List[Dict[str, Any]]:
        """获取用于UI显示的模型列表"""
        try:
            key_manager = await get_key_manager_instance()
            model_service = ModelService()

            api_key = await key_manager.get_first_valid_key()
            if not api_key:
                logger.error("No valid API keys available to fetch model list for UI.")
                raise HTTPException(
                    status_code=500,
                    detail="No valid API keys available to fetch model list.",
                )

            models = await model_service.get_gemini_openai_models(api_key)
            return models
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(
                f"Failed to fetch models for UI in ConfigService: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch models for UI: {str(e)}"
            )


# 重新加载配置的函数
def _reload_settings():
    """重新加载环境变量并更新配置"""
    # 显式加载 .env 文件，覆盖现有环境变量
    load_dotenv(find_dotenv(), override=True)
    # 更新现有 settings 对象的属性，而不是新建实例
    for key, value in ConfigSettings().model_dump().items():
        setattr(settings, key, value)
