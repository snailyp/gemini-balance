import asyncio
from itertools import cycle
from typing import Dict, List, Optional
from app.core.config import APIKeyConfig
from app.core.logger import get_key_manager_logger

logger = get_key_manager_logger()


class KeyManager:
    def __init__(self, api_key_configs: List[APIKeyConfig]):
        if not api_key_configs:
            logger.error("没有提供有效的API密钥配置")
            raise ValueError("API密钥配置列表不能为空")

        self.api_key_configs = api_key_configs
        self.key_config_cycle = cycle(api_key_configs)
        self.key_cycle_lock = asyncio.Lock()
        self.failure_count_lock = asyncio.Lock()
        self.key_failure_counts: Dict[str, int] = {config.key: 0 for config in api_key_configs}
        self.MAX_FAILURES = 10

    async def get_next_key_config(self) -> APIKeyConfig:
        """获取下一个API key配置"""
        async with self.key_cycle_lock:
            return next(self.key_config_cycle)

    async def is_key_valid(self, key: str) -> bool:
        """检查key是否有效"""
        async with self.failure_count_lock:
            return self.key_failure_counts[key] < self.MAX_FAILURES

    async def reset_failure_counts(self):
        """重置所有key的失败计数"""
        async with self.failure_count_lock:
            for key in self.key_failure_counts:
                self.key_failure_counts[key] = 0

    async def get_next_working_key_config(self) -> APIKeyConfig:
        """获取下一个可用的API key配置"""
        initial_config = await self.get_next_key_config()
        current_config = initial_config

        while True:
            if await self.is_key_valid(current_config.key):
                return current_config

            current_config = await self.get_next_key_config()
            if current_config.key == initial_config.key:
                return current_config

    async def handle_api_failure(self, api_key: str) -> APIKeyConfig:
        """处理API调用失败"""
        async with self.failure_count_lock:
            self.key_failure_counts[api_key] += 1
            if self.key_failure_counts[api_key] >= self.MAX_FAILURES:
                logger.warning(
                    f"API key {api_key} has failed {self.MAX_FAILURES} times"
                )

        return await self.get_next_working_key_config()

    async def get_keys_by_status(self) -> dict:
        """获取分类后的API key列表"""
        valid_keys = []
        invalid_keys = []
        
        async with self.failure_count_lock:
            for config in self.api_key_configs:
                key_info = {
                    "key": config.key
                }
                if self.key_failure_counts[config.key] < self.MAX_FAILURES:
                    valid_keys.append(key_info)
                else:
                    invalid_keys.append(key_info)
        
        return {
            "valid_keys": valid_keys,
            "invalid_keys": invalid_keys
        }
