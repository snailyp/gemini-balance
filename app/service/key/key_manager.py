import asyncio
import json
import os
import random
import time
from itertools import cycle
from typing import Dict, Union, Tuple

from app.config.config import settings
from app.log.logger import get_key_manager_logger
from app.utils.helpers import redact_key_for_logging

logger = get_key_manager_logger()


class KeyManager:
    def __init__(self, api_keys: list, vertex_api_keys: list):
        self.api_keys = api_keys
        self.vertex_api_keys = vertex_api_keys
        self.key_cycle = cycle(api_keys)
        self.vertex_key_cycle = cycle(vertex_api_keys)
        self.key_cycle_lock = asyncio.Lock()
        self.vertex_key_cycle_lock = asyncio.Lock()
        self.failure_count_lock = asyncio.Lock()
        self.vertex_failure_count_lock = asyncio.Lock()
        
        # 原有的失败计数器
        self.key_failure_counts: Dict[str, int] = {key: 0 for key in api_keys}
        self.vertex_key_failure_counts: Dict[str, int] = {
            key: 0 for key in vertex_api_keys
        }
        
        # 贝叶斯统计数据 (alpha, beta) 表示 Beta(alpha, beta) 分布参数
        self.bayesian_stats_lock = asyncio.Lock()
        self.vertex_bayesian_stats_lock = asyncio.Lock()
        self.key_stats: Dict[str, Tuple[int, int]] = {}
        self.vertex_key_stats: Dict[str, Tuple[int, int]] = {}
        
        self.MAX_FAILURES = settings.MAX_FAILURES
        self.paid_key = settings.PAID_KEY
        
        # 初始化贝叶斯统计
        self._init_bayesian_stats()

    def _init_bayesian_stats(self):
        """初始化贝叶斯统计数据的基本结构（实际数据由持久化层恢复）"""
        # 初始化普通API keys的贝叶斯统计（使用默认值，将被持久化层覆盖）
        for key in self.api_keys:
            # 从现有失败计数迁移作为默认值: alpha=1, beta=1+failures
            alpha = settings.BAYESIAN_ALPHA_PRIOR
            beta = settings.BAYESIAN_BETA_PRIOR + self.key_failure_counts.get(key, 0)
            self.key_stats[key] = (alpha, beta)
        
        # 初始化Vertex API keys的贝叶斯统计（使用默认值，将被持久化层覆盖）
        for key in self.vertex_api_keys:
            # 从现有失败计数迁移作为默认值
            alpha = settings.BAYESIAN_ALPHA_PRIOR
            beta = settings.BAYESIAN_BETA_PRIOR + self.vertex_key_failure_counts.get(key, 0)
            self.vertex_key_stats[key] = (alpha, beta)
        
        logger.debug(f"Pre-initialized Bayesian stats structure for {len(self.key_stats)} API keys and {len(self.vertex_key_stats)} Vertex keys")

    def _load_bayesian_stats(self, file_path: str) -> dict:
        """从文件加载贝叶斯统计数据"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load Bayesian stats from {file_path}: {e}")
        return {}

    def _save_bayesian_stats(self, file_path: str = "bayesian_key_stats.json"):
        """保存贝叶斯统计数据到文件"""
        try:
            stats = {
                "key_stats": {k: list(v) for k, v in self.key_stats.items()},
                "vertex_key_stats": {k: list(v) for k, v in self.vertex_key_stats.items()},
                "timestamp": time.time()
            }
            with open(file_path, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.debug(f"Saved Bayesian stats to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save Bayesian stats to {file_path}: {e}")

    async def get_paid_key(self) -> str:
        return self.paid_key

    async def get_next_key(self) -> str:
        """获取下一个API key"""
        async with self.key_cycle_lock:
            return next(self.key_cycle)

    async def get_next_vertex_key(self) -> str:
        """获取下一个 Vertex Express API key"""
        async with self.vertex_key_cycle_lock:
            return next(self.vertex_key_cycle)

    async def is_key_valid(self, key: str) -> bool:
        """检查key是否有效"""
        async with self.failure_count_lock:
            return self.key_failure_counts[key] < self.MAX_FAILURES

    async def is_vertex_key_valid(self, key: str) -> bool:
        """检查 Vertex key 是否有效"""
        async with self.vertex_failure_count_lock:
            return self.vertex_key_failure_counts[key] < self.MAX_FAILURES

    async def reset_failure_counts(self):
        """重置所有key的失败计数"""
        async with self.failure_count_lock:
            for key in self.key_failure_counts:
                self.key_failure_counts[key] = 0

    async def reset_vertex_failure_counts(self):
        """重置所有 Vertex key 的失败计数"""
        async with self.vertex_failure_count_lock:
            for key in self.vertex_key_failure_counts:
                self.vertex_key_failure_counts[key] = 0

    async def reset_key_failure_count(self, key: str) -> bool:
        """重置指定key的失败计数"""
        async with self.failure_count_lock:
            if key in self.key_failure_counts:
                self.key_failure_counts[key] = 0
                logger.info(f"Reset failure count for key: {redact_key_for_logging(key)}")
                return True
            logger.warning(
                f"Attempt to reset failure count for non-existent key: {key}"
            )
            return False

    async def reset_vertex_key_failure_count(self, key: str) -> bool:
        """重置指定 Vertex key 的失败计数"""
        async with self.vertex_failure_count_lock:
            if key in self.vertex_key_failure_counts:
                self.vertex_key_failure_counts[key] = 0
                logger.info(f"Reset failure count for Vertex key: {redact_key_for_logging(key)}")
                return True
            logger.warning(
                f"Attempt to reset failure count for non-existent Vertex key: {key}"
            )
            return False

    async def get_next_working_key(self) -> str:
        """获取下一可用的API key"""
        initial_key = await self.get_next_key()
        current_key = initial_key

        while True:
            if await self.is_key_valid(current_key):
                return current_key

            current_key = await self.get_next_key()
            if current_key == initial_key:
                return current_key

    async def get_next_working_vertex_key(self) -> str:
        """获取下一可用的 Vertex Express API key"""
        initial_key = await self.get_next_vertex_key()
        current_key = initial_key

        while True:
            if await self.is_vertex_key_valid(current_key):
                return current_key

            current_key = await self.get_next_vertex_key()
            if current_key == initial_key:
                return current_key

    async def handle_api_failure(self, api_key: str, retries: int) -> str:
        """处理API调用失败"""
        # 更新原有失败计数
        async with self.failure_count_lock:
            self.key_failure_counts[api_key] += 1
            if self.key_failure_counts[api_key] >= self.MAX_FAILURES:
                logger.warning(
                    f"API key {redact_key_for_logging(api_key)} has failed {self.MAX_FAILURES} times"
                )
        
        # 更新贝叶斯统计 (失败: beta += 1)
        await self.update_key_failure(api_key)
        
        if retries < settings.MAX_RETRIES:
            return await self.get_next_working_key()
        else:
            return ""

    async def handle_vertex_api_failure(self, api_key: str, retries: int) -> str:
        """处理 Vertex Express API 调用失败"""
        # 更新原有失败计数
        async with self.vertex_failure_count_lock:
            self.vertex_key_failure_counts[api_key] += 1
            if self.vertex_key_failure_counts[api_key] >= self.MAX_FAILURES:
                logger.warning(
                    f"Vertex Express API key {redact_key_for_logging(api_key)} has failed {self.MAX_FAILURES} times"
                )
        
        # 更新贝叶斯统计 (失败: beta += 1)
        await self.update_vertex_key_failure(api_key)

    def get_fail_count(self, key: str) -> int:
        """获取指定密钥的失败次数"""
        return self.key_failure_counts.get(key, 0)

    def get_vertex_fail_count(self, key: str) -> int:
        """获取指定 Vertex 密钥的失败次数"""
        return self.vertex_key_failure_counts.get(key, 0)

    async def get_all_keys_with_fail_count(self) -> dict:
        """获取所有API key及其失败次数"""
        all_keys = {}
        async with self.failure_count_lock:
            for key in self.api_keys:
                all_keys[key] = self.key_failure_counts.get(key, 0)
        
        valid_keys = {k: v for k, v in all_keys.items() if v < self.MAX_FAILURES}
        invalid_keys = {k: v for k, v in all_keys.items() if v >= self.MAX_FAILURES}
        
        return {"valid_keys": valid_keys, "invalid_keys": invalid_keys, "all_keys": all_keys}

    async def get_keys_by_status(self) -> dict:
        """获取分类后的API key列表，包括失败次数"""
        valid_keys = {}
        invalid_keys = {}

        async with self.failure_count_lock:
            for key in self.api_keys:
                fail_count = self.key_failure_counts[key]
                if fail_count < self.MAX_FAILURES:
                    valid_keys[key] = fail_count
                else:
                    invalid_keys[key] = fail_count

        return {"valid_keys": valid_keys, "invalid_keys": invalid_keys}

    async def get_vertex_keys_by_status(self) -> dict:
        """获取分类后的 Vertex Express API key 列表，包括失败次数"""
        valid_keys = {}
        invalid_keys = {}

        async with self.vertex_failure_count_lock:
            for key in self.vertex_api_keys:
                fail_count = self.vertex_key_failure_counts[key]
                if fail_count < self.MAX_FAILURES:
                    valid_keys[key] = fail_count
                else:
                    invalid_keys[key] = fail_count
        return {"valid_keys": valid_keys, "invalid_keys": invalid_keys}

    async def get_first_valid_key(self) -> str:
        """获取第一个有效的API key"""
        async with self.failure_count_lock:
            for key in self.key_failure_counts:
                if self.key_failure_counts[key] < self.MAX_FAILURES:
                    return key
        if self.api_keys:
            return self.api_keys[0]
        if not self.api_keys:
            logger.warning("API key list is empty, cannot get first valid key.")
            return ""
        return self.api_keys[0]

    async def get_random_valid_key(self) -> str:
        """获取随机的有效API key (已弃用，使用get_bayesian_key代替)"""
        logger.warning("get_random_valid_key is deprecated, using get_bayesian_key instead")
        return await self.get_bayesian_key()

    async def get_bayesian_key(self) -> str:
        """使用贝叶斯Thompson Sampling获取最优API key"""
        valid_keys = []
        sampled_scores = []
        
        async with self.bayesian_stats_lock:
            # 过滤出有效的keys (beta值未达到失效阈值)
            for key in self.api_keys:
                if key in self.key_stats:
                    alpha, beta = self.key_stats[key]
                    # 使用原有的MAX_FAILURES逻辑，但基于beta值判断
                    failure_count = beta - settings.BAYESIAN_BETA_PRIOR
                    if failure_count < self.MAX_FAILURES:
                        valid_keys.append(key)
                        # Thompson Sampling: 从Beta分布采样
                        try:
                            if alpha > 0 and beta > 0:
                                sampled_prob = random.betavariate(alpha, beta)
                            else:
                                # 防止参数异常，使用均匀分布
                                sampled_prob = random.random()
                            sampled_scores.append(sampled_prob)
                        except ValueError:
                            # betavariate参数异常时的fallback
                            sampled_scores.append(random.random())
                else:
                    # 如果key不在统计中，给予默认概率
                    valid_keys.append(key)
                    sampled_scores.append(0.5)
        
        if valid_keys and sampled_scores:
            # 选择采样概率最高的key
            best_idx = sampled_scores.index(max(sampled_scores))
            selected_key = valid_keys[best_idx]
            logger.debug(f"Bayesian selection: chose key {redact_key_for_logging(selected_key)} "
                        f"with sampled prob {sampled_scores[best_idx]:.4f}")
            return selected_key
        
        # 如果没有有效的key，返回第一个key作为fallback
        if self.api_keys:
            logger.warning("No valid keys available for Bayesian selection, returning first key as fallback.")
            return self.api_keys[0]
        
        logger.warning("API key list is empty, cannot perform Bayesian key selection.")
        return ""

    async def get_bayesian_vertex_key(self) -> str:
        """使用贝叶斯Thompson Sampling获取最优Vertex API key"""
        valid_keys = []
        sampled_scores = []
        
        async with self.vertex_bayesian_stats_lock:
            # 过滤出有效的vertex keys
            for key in self.vertex_api_keys:
                if key in self.vertex_key_stats:
                    alpha, beta = self.vertex_key_stats[key]
                    # 使用原有的MAX_FAILURES逻辑，但基于beta值判断
                    failure_count = beta - settings.BAYESIAN_BETA_PRIOR
                    if failure_count < self.MAX_FAILURES:
                        valid_keys.append(key)
                        # Thompson Sampling: 从Beta分布采样
                        try:
                            if alpha > 0 and beta > 0:
                                sampled_prob = random.betavariate(alpha, beta)
                            else:
                                sampled_prob = random.random()
                            sampled_scores.append(sampled_prob)
                        except ValueError:
                            sampled_scores.append(random.random())
                else:
                    valid_keys.append(key)
                    sampled_scores.append(0.5)
        
        if valid_keys and sampled_scores:
            # 选择采样概率最高的key
            best_idx = sampled_scores.index(max(sampled_scores))
            selected_key = valid_keys[best_idx]
            logger.debug(f"Bayesian Vertex selection: chose key {redact_key_for_logging(selected_key)} "
                        f"with sampled prob {sampled_scores[best_idx]:.4f}")
            return selected_key
        
        # 如果没有有效的key，返回第一个key作为fallback
        if self.vertex_api_keys:
            logger.warning("No valid Vertex keys available for Bayesian selection, returning first key as fallback.")
            return self.vertex_api_keys[0]
        
        logger.warning("Vertex API key list is empty, cannot perform Bayesian key selection.")
        return ""

    async def update_key_success(self, api_key: str):
        """更新API key成功统计 (alpha += 1)"""
        async with self.bayesian_stats_lock:
            if api_key in self.key_stats:
                alpha, beta = self.key_stats[api_key]
                self.key_stats[api_key] = (alpha + 1, beta)
                logger.debug(f"Updated success for key {redact_key_for_logging(api_key)}: alpha={alpha+1}, beta={beta}")
            else:
                # 如果key不在统计中，初始化
                self.key_stats[api_key] = (settings.BAYESIAN_ALPHA_PRIOR + 1, settings.BAYESIAN_BETA_PRIOR)
                logger.debug(f"Initialized and updated success for new key {redact_key_for_logging(api_key)}")
        
        # 触发周期性保存
        await _auto_save_bayesian_stats(self)

    async def update_key_failure(self, api_key: str):
        """更新API key失败统计 (beta += 1)"""
        async with self.bayesian_stats_lock:
            if api_key in self.key_stats:
                alpha, beta = self.key_stats[api_key]
                self.key_stats[api_key] = (alpha, beta + 1)
                logger.debug(f"Updated failure for key {redact_key_for_logging(api_key)}: alpha={alpha}, beta={beta+1}")
            else:
                # 如果key不在统计中，初始化
                self.key_stats[api_key] = (settings.BAYESIAN_ALPHA_PRIOR, settings.BAYESIAN_BETA_PRIOR + 1)
                logger.debug(f"Initialized and updated failure for new key {redact_key_for_logging(api_key)}")
        
        # 触发周期性保存
        await _auto_save_bayesian_stats(self)

    async def update_vertex_key_success(self, api_key: str):
        """更新Vertex API key成功统计 (alpha += 1)"""
        async with self.vertex_bayesian_stats_lock:
            if api_key in self.vertex_key_stats:
                alpha, beta = self.vertex_key_stats[api_key]
                self.vertex_key_stats[api_key] = (alpha + 1, beta)
                logger.debug(f"Updated Vertex success for key {redact_key_for_logging(api_key)}: alpha={alpha+1}, beta={beta}")
            else:
                # 如果key不在统计中，初始化
                self.vertex_key_stats[api_key] = (settings.BAYESIAN_ALPHA_PRIOR + 1, settings.BAYESIAN_BETA_PRIOR)
                logger.debug(f"Initialized and updated Vertex success for new key {redact_key_for_logging(api_key)}")
        
        # 触发周期性保存
        await _auto_save_bayesian_stats(self)

    async def update_vertex_key_failure(self, api_key: str):
        """更新Vertex API key失败统计 (beta += 1)"""
        async with self.vertex_bayesian_stats_lock:
            if api_key in self.vertex_key_stats:
                alpha, beta = self.vertex_key_stats[api_key]
                self.vertex_key_stats[api_key] = (alpha, beta + 1)
                logger.debug(f"Updated Vertex failure for key {redact_key_for_logging(api_key)}: alpha={alpha}, beta={beta+1}")
            else:
                # 如果key不在统计中，初始化
                self.vertex_key_stats[api_key] = (settings.BAYESIAN_ALPHA_PRIOR, settings.BAYESIAN_BETA_PRIOR + 1)
                logger.debug(f"Initialized and updated Vertex failure for new key {redact_key_for_logging(api_key)}")
        
        # 触发周期性保存
        await _auto_save_bayesian_stats(self)


_singleton_instance = None
_singleton_lock = asyncio.Lock()
_preserved_failure_counts: Union[Dict[str, int], None] = None
_preserved_vertex_failure_counts: Union[Dict[str, int], None] = None
_preserved_old_api_keys_for_reset: Union[list, None] = None
_preserved_vertex_old_api_keys_for_reset: Union[list, None] = None
_preserved_next_key_in_cycle: Union[str, None] = None
_preserved_vertex_next_key_in_cycle: Union[str, None] = None

# 贝叶斯统计的全局保存变量
_preserved_bayesian_stats: Union[Dict[str, Tuple[int, int]], None] = None
_preserved_vertex_bayesian_stats: Union[Dict[str, Tuple[int, int]], None] = None
_last_stats_save_time: float = 0


async def get_key_manager_instance(
    api_keys: list = None, vertex_api_keys: list = None
) -> KeyManager:
    """
    获取 KeyManager 单例实例。

    如果尚未创建实例，将使用提供的 api_keys,vertex_api_keys 初始化 KeyManager。
    如果已创建实例，则忽略 api_keys 参数，返回现有单例。
    如果在重置后调用，会尝试恢复之前的状态（失败计数、循环位置）。
    """
    global _singleton_instance, _preserved_failure_counts, _preserved_vertex_failure_counts, _preserved_old_api_keys_for_reset, _preserved_vertex_old_api_keys_for_reset, _preserved_next_key_in_cycle, _preserved_vertex_next_key_in_cycle

    async with _singleton_lock:
        if _singleton_instance is None:
            if api_keys is None:
                raise ValueError(
                    "API keys are required to initialize or re-initialize the KeyManager instance."
                )
            if vertex_api_keys is None:
                raise ValueError(
                    "Vertex Express API keys are required to initialize or re-initialize the KeyManager instance."
                )

            if not api_keys:
                logger.warning(
                    "Initializing KeyManager with an empty list of API keys."
                )
            if not vertex_api_keys:
                logger.warning(
                    "Initializing KeyManager with an empty list of Vertex Express API keys."
                )

            _singleton_instance = KeyManager(api_keys, vertex_api_keys)
            logger.info(
                f"KeyManager instance created/re-created with {len(api_keys)} API keys and {len(vertex_api_keys)} Vertex Express API keys."
            )
            
            # 恢复贝叶斯统计
            await _restore_bayesian_stats(_singleton_instance)

            # 1. 恢复失败计数
            if _preserved_failure_counts:
                current_failure_counts = {
                    key: 0 for key in _singleton_instance.api_keys
                }
                for key, count in _preserved_failure_counts.items():
                    if key in current_failure_counts:
                        current_failure_counts[key] = count
                _singleton_instance.key_failure_counts = current_failure_counts
                logger.info("Inherited failure counts for applicable keys.")
            _preserved_failure_counts = None

            if _preserved_vertex_failure_counts:
                current_vertex_failure_counts = {
                    key: 0 for key in _singleton_instance.vertex_api_keys
                }
                for key, count in _preserved_vertex_failure_counts.items():
                    if key in current_vertex_failure_counts:
                        current_vertex_failure_counts[key] = count
                _singleton_instance.vertex_key_failure_counts = (
                    current_vertex_failure_counts
                )
                logger.info("Inherited failure counts for applicable Vertex keys.")
            _preserved_vertex_failure_counts = None

            # 2. 调整 key_cycle 的起始点
            start_key_for_new_cycle = None
            if (
                _preserved_old_api_keys_for_reset
                and _preserved_next_key_in_cycle
                and _singleton_instance.api_keys
            ):
                try:
                    start_idx_in_old = _preserved_old_api_keys_for_reset.index(
                        _preserved_next_key_in_cycle
                    )

                    for i in range(len(_preserved_old_api_keys_for_reset)):
                        current_old_key_idx = (start_idx_in_old + i) % len(
                            _preserved_old_api_keys_for_reset
                        )
                        key_candidate = _preserved_old_api_keys_for_reset[
                            current_old_key_idx
                        ]
                        if key_candidate in _singleton_instance.api_keys:
                            start_key_for_new_cycle = key_candidate
                            break
                except ValueError:
                    logger.warning(
                        f"Preserved next key '{_preserved_next_key_in_cycle}' not found in preserved old API keys. "
                        "New cycle will start from the beginning of the new list."
                    )
                except Exception as e:
                    logger.error(
                        f"Error determining start key for new cycle from preserved state: {e}. "
                        "New cycle will start from the beginning."
                    )

            if start_key_for_new_cycle and _singleton_instance.api_keys:
                try:
                    target_idx = _singleton_instance.api_keys.index(
                        start_key_for_new_cycle
                    )
                    for _ in range(target_idx):
                        next(_singleton_instance.key_cycle)
                    logger.info(
                        f"Key cycle in new instance advanced. Next call to get_next_key() will yield: {start_key_for_new_cycle}"
                    )
                except ValueError:
                    logger.warning(
                        f"Determined start key '{start_key_for_new_cycle}' not found in new API keys during cycle advancement. "
                        "New cycle will start from the beginning."
                    )
                except StopIteration:
                    logger.error(
                        "StopIteration while advancing key cycle, implies empty new API key list previously missed."
                    )
                except Exception as e:
                    logger.error(
                        f"Error advancing new key cycle: {e}. Cycle will start from beginning."
                    )
            else:
                if _singleton_instance.api_keys:
                    logger.info(
                        "New key cycle will start from the beginning of the new API key list (no specific start key determined or needed)."
                    )
                else:
                    logger.info(
                        "New key cycle not applicable as the new API key list is empty."
                    )

            # 清理所有保存的状态
            _preserved_old_api_keys_for_reset = None
            _preserved_next_key_in_cycle = None

            # 3. 调整 vertex_key_cycle 的起始点
            start_key_for_new_vertex_cycle = None
            if (
                _preserved_vertex_old_api_keys_for_reset
                and _preserved_vertex_next_key_in_cycle
                and _singleton_instance.vertex_api_keys
            ):
                try:
                    start_idx_in_old = _preserved_vertex_old_api_keys_for_reset.index(
                        _preserved_vertex_next_key_in_cycle
                    )

                    for i in range(len(_preserved_vertex_old_api_keys_for_reset)):
                        current_old_key_idx = (start_idx_in_old + i) % len(
                            _preserved_vertex_old_api_keys_for_reset
                        )
                        key_candidate = _preserved_vertex_old_api_keys_for_reset[
                            current_old_key_idx
                        ]
                        if key_candidate in _singleton_instance.vertex_api_keys:
                            start_key_for_new_vertex_cycle = key_candidate
                            break
                except ValueError:
                    logger.warning(
                        f"Preserved next key '{_preserved_vertex_next_key_in_cycle}' not found in preserved old Vertex Express API keys. "
                        "New cycle will start from the beginning of the new list."
                    )
                except Exception as e:
                    logger.error(
                        f"Error determining start key for new Vertex key cycle from preserved state: {e}. "
                        "New cycle will start from the beginning."
                    )

            if start_key_for_new_vertex_cycle and _singleton_instance.vertex_api_keys:
                try:
                    target_idx = _singleton_instance.vertex_api_keys.index(
                        start_key_for_new_vertex_cycle
                    )
                    for _ in range(target_idx):
                        next(_singleton_instance.vertex_key_cycle)
                    logger.info(
                        f"Vertex key cycle in new instance advanced. Next call to get_next_vertex_key() will yield: {start_key_for_new_vertex_cycle}"
                    )
                except ValueError:
                    logger.warning(
                        f"Determined start key '{start_key_for_new_vertex_cycle}' not found in new Vertex Express API keys during cycle advancement. "
                        "New cycle will start from the beginning."
                    )
                except StopIteration:
                    logger.error(
                        "StopIteration while advancing Vertex key cycle, implies empty new Vertex Express API key list previously missed."
                    )
                except Exception as e:
                    logger.error(
                        f"Error advancing new Vertex key cycle: {e}. Cycle will start from beginning."
                    )
            else:
                if _singleton_instance.vertex_api_keys:
                    logger.info(
                        "New Vertex key cycle will start from the beginning of the new Vertex Express API key list (no specific start key determined or needed)."
                    )
                else:
                    logger.info(
                        "New Vertex key cycle not applicable as the new Vertex Express API key list is empty."
                    )

            # 清理所有保存的状态
            _preserved_vertex_old_api_keys_for_reset = None
            _preserved_vertex_next_key_in_cycle = None

        # 定期保存贝叶斯统计
        await _auto_save_bayesian_stats(_singleton_instance)
        
        return _singleton_instance


async def reset_key_manager_instance():
    """
    重置 KeyManager 单例实例。
    将保存当前实例的状态（失败计数、旧 API keys、下一个 key 提示）
    以供下一次 get_key_manager_instance 调用时恢复。
    """
    global _singleton_instance, _preserved_failure_counts, _preserved_vertex_failure_counts, _preserved_old_api_keys_for_reset, _preserved_vertex_old_api_keys_for_reset, _preserved_next_key_in_cycle, _preserved_vertex_next_key_in_cycle, _preserved_bayesian_stats, _preserved_vertex_bayesian_stats
    async with _singleton_lock:
        if _singleton_instance:
            # 0. 保存贝叶斯统计
            async with _singleton_instance.bayesian_stats_lock:
                _preserved_bayesian_stats = _singleton_instance.key_stats.copy()
            async with _singleton_instance.vertex_bayesian_stats_lock:
                _preserved_vertex_bayesian_stats = _singleton_instance.vertex_key_stats.copy()
            
            # 1. 保存失败计数
            _preserved_failure_counts = _singleton_instance.key_failure_counts.copy()
            _preserved_vertex_failure_counts = (
                _singleton_instance.vertex_key_failure_counts.copy()
            )

            # 2. 保存旧的 API keys 列表
            _preserved_old_api_keys_for_reset = _singleton_instance.api_keys.copy()
            _preserved_vertex_old_api_keys_for_reset = (
                _singleton_instance.vertex_api_keys.copy()
            )

            # 3. 保存 key_cycle 的下一个 key 提示
            try:
                if _singleton_instance.api_keys:
                    _preserved_next_key_in_cycle = (
                        await _singleton_instance.get_next_key()
                    )
                else:
                    _preserved_next_key_in_cycle = None
            except StopIteration:
                logger.warning(
                    "Could not preserve next key hint: key cycle was empty or exhausted in old instance."
                )
                _preserved_next_key_in_cycle = None
            except Exception as e:
                logger.error(f"Error preserving next key hint during reset: {e}")
                _preserved_next_key_in_cycle = None

            # 4. 保存 vertex_key_cycle 的下一个 key 提示
            try:
                if _singleton_instance.vertex_api_keys:
                    _preserved_vertex_next_key_in_cycle = (
                        await _singleton_instance.get_next_vertex_key()
                    )
                else:
                    _preserved_vertex_next_key_in_cycle = None
            except StopIteration:
                logger.warning(
                    "Could not preserve next key hint: Vertex key cycle was empty or exhausted in old instance."
                )
                _preserved_vertex_next_key_in_cycle = None
            except Exception as e:
                logger.error(f"Error preserving next key hint during reset: {e}")
                _preserved_vertex_next_key_in_cycle = None

            _singleton_instance = None
            logger.info(
                "KeyManager instance has been reset. State (failure counts, old keys, next key hint) preserved for next instantiation."
            )
        else:
            logger.info(
                "KeyManager instance was not set (or already reset), no reset action performed."
            )


async def _restore_bayesian_stats(instance: KeyManager):
    """恢复贝叶斯统计数据到KeyManager实例"""
    global _preserved_bayesian_stats, _preserved_vertex_bayesian_stats
    
    try:
        # 标记是否有全局状态恢复
        has_preserved_state = bool(_preserved_bayesian_stats or _preserved_vertex_bayesian_stats)
        
        # 首先尝试从全局变量恢复（重置后的状态）
        if _preserved_bayesian_stats:
            async with instance.bayesian_stats_lock:
                for key in instance.api_keys:
                    if key in _preserved_bayesian_stats:
                        instance.key_stats[key] = _preserved_bayesian_stats[key]
            logger.info(f"Restored Bayesian stats for {len(_preserved_bayesian_stats)} API keys from preserved state")
            _preserved_bayesian_stats = None
        
        if _preserved_vertex_bayesian_stats:
            async with instance.vertex_bayesian_stats_lock:
                for key in instance.vertex_api_keys:
                    if key in _preserved_vertex_bayesian_stats:
                        instance.vertex_key_stats[key] = _preserved_vertex_bayesian_stats[key]
            logger.info(f"Restored Vertex Bayesian stats for {len(_preserved_vertex_bayesian_stats)} Vertex keys from preserved state")
            _preserved_vertex_bayesian_stats = None
        
        # 如果没有全局状态，尝试从文件加载
        if not has_preserved_state:
            loaded_stats = instance._load_bayesian_stats("bayesian_key_stats.json")
            if loaded_stats:
                async with instance.bayesian_stats_lock:
                    key_stats = loaded_stats.get("key_stats", {})
                    for key in instance.api_keys:
                        if key in key_stats:
                            instance.key_stats[key] = tuple(key_stats[key])
                
                async with instance.vertex_bayesian_stats_lock:
                    vertex_key_stats = loaded_stats.get("vertex_key_stats", {})
                    for key in instance.vertex_api_keys:
                        if key in vertex_key_stats:
                            instance.vertex_key_stats[key] = tuple(vertex_key_stats[key])
                
                logger.info(f"Loaded Bayesian stats from file: {len(key_stats)} API keys, {len(vertex_key_stats)} Vertex keys")
            else:
                logger.info("No saved Bayesian stats found, using initialized defaults")
                
    except Exception as e:
        logger.error(f"Error restoring Bayesian stats: {e}")


async def _auto_save_bayesian_stats(instance: KeyManager):
    """自动保存贝叶斯统计数据（如果距离上次保存超过间隔时间）"""
    global _last_stats_save_time
    
    current_time = time.time()
    if current_time - _last_stats_save_time >= settings.BAYESIAN_STATS_DUMP_INTERVAL:
        try:
            instance._save_bayesian_stats("bayesian_key_stats.json")
            _last_stats_save_time = current_time
            logger.debug(f"Auto-saved Bayesian stats at {current_time}")
        except Exception as e:
            logger.error(f"Error auto-saving Bayesian stats: {e}")


async def save_bayesian_stats_on_shutdown():
    """在应用关闭时强制保存贝叶斯统计数据"""
    global _singleton_instance
    
    if _singleton_instance:
        try:
            _singleton_instance._save_bayesian_stats("bayesian_key_stats.json")
            logger.info("Saved Bayesian stats on shutdown")
        except Exception as e:
            logger.error(f"Error saving Bayesian stats on shutdown: {e}")
    else:
        logger.warning("No KeyManager instance to save stats from")
