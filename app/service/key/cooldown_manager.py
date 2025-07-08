import time
from typing import Dict, List
import asyncio

from app.config.config import settings
from app.log.logger import get_key_manager_logger

logger = get_key_manager_logger()


class CooldownManager:
    """管理API密钥的冷却时间，特别是针对429错误。"""

    def __init__(self):
        # 存储每个key的冷却截止时间 (timestamp)
        self.key_cooldown_until: Dict[str, float] = {}
        # 存储每个key当前的冷却等级
        self.key_cooldown_level: Dict[str, int] = {}
        # 从配置中获取冷却时长列表（分钟）
        self.cooldown_durations_minutes: List[int] = settings.COOLDOWN_DURATIONS_MINUTES
        self.lock = asyncio.Lock()

    async def handle_429_failure(self, api_key: str):
        """
        处理一个key的429失败。
        这会根据key当前的冷却等级，为其设置一个更长的冷却时间。
        """
        async with self.lock:
            # 获取当前key的冷却等级，如果不存在则从0开始
            current_level = self.key_cooldown_level.get(api_key, 0)

            # 从配置列表中获取当前的冷却时长（分钟）
            cooldown_minutes = self.cooldown_durations_minutes[current_level]
            
            # 计算冷却截止的Unix时间戳
            cooldown_seconds = cooldown_minutes * 60
            self.key_cooldown_until[api_key] = time.time() + cooldown_seconds

            # 更新key的冷却等级，如果达到最高等级，则循环回0
            next_level = (current_level + 1) % len(self.cooldown_durations_minutes)
            self.key_cooldown_level[api_key] = next_level

            # 获取下一次冷却的时长用于日志记录
            next_cooldown_minutes = self.cooldown_durations_minutes[next_level]

            logger.info(
                f"API key '{api_key}' received a 429 error. "
                f"It is now in cooldown for {cooldown_minutes} minutes. "
                f"Next cooldown level will be {next_level} ({next_cooldown_minutes} minutes)."
            )
            logger.info(
                f"API密钥 '{api_key}' 收到 429 错误，已进入冷却状态，时长: {cooldown_minutes} 分钟。 "
                f"下一次冷却等级为 {next_level} ({next_cooldown_minutes}分钟)。"
            )

    async def is_key_in_cooldown(self, api_key: str) -> bool:
        """检查一个key当前是否处于冷却状态。"""
        async with self.lock:
            cooldown_until = self.key_cooldown_until.get(api_key)
            
            if cooldown_until and time.time() < cooldown_until:
                # 如果key在冷却期内
                return True
            
            # 如果key不在冷却期内，或者冷却时间已过，则清理旧状态
            if cooldown_until:
                del self.key_cooldown_until[api_key]
                # 注意：我们保留 cooldown_level，以便下次失败时能进入下一等级
            
            return False