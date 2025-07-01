import asyncio
import json
import random
import itertools
from typing import Any, Dict, List
import logging

# 模拟日志记录器，以便在测试中捕获调试信息
class TestLogger:
    def __init__(self, name="test_logger"):
        self.name = name
    def debug(self, msg):
        print(f"DEBUG [{self.name}]: {msg}")
    def info(self, msg):
        print(f"INFO [{self.name}]: {msg}")
    def warning(self, msg):
        print(f"WARNING [{self.name}]: {msg}")
    def error(self, msg):
        print(f"ERROR [{self.name}]: {msg}")

# 模拟 app.service.client.api_client 中的 GeminiApiClient
class MockGeminiApiClient:
    def __init__(self, base_urls: List[str], selection_strategy: str, timeout: int = 300):
        self.base_urls = base_urls
        self.selection_strategy = selection_strategy
        self.timeout = timeout
        logger = TestLogger("api_client_init") # 使用模拟日志器
        logger.debug(f"MockGeminiApiClient __init__ received base_urls: {self.base_urls} (type: {type(self.base_urls)})")
        
        # 确保 self.base_urls 始终是列表，即使传入的是字符串
        if isinstance(self.base_urls, str):
            logger.warning(f"base_urls received as string: '{self.base_urls}'. Converting to list.")
            self.base_urls = [self.base_urls]
        elif not isinstance(self.base_urls, list):
            logger.error(f"base_urls received unexpected non-list type: {type(self.base_urls)}. Forcing to empty list.")
            self.base_urls = []

        # 确保列表中的每个元素都是字符串
        self.base_urls = [str(url) for url in self.base_urls]

        if not self.base_urls:
            logger.error("No valid base URLs after initialization. Defaulting to a fallback URL.")
            self.base_urls = ["https://generativelanguage.googleapis.com/v1beta"] # 提供一个最终的备用URL

        self._round_robin_iterator = itertools.cycle(self.base_urls)

    def _select_base_url(self, api_key: str) -> str:
        logger = TestLogger("api_client_select_url") # 使用模拟日志器
        logger.debug(f"Selecting base URL from: {self.base_urls}, strategy: {self.selection_strategy}")
        if not self.base_urls:
            raise ValueError("No base URLs configured for Gemini API client.")

        selected_url: str
        if self.selection_strategy == "round_robin":
            selected_url = next(self._round_robin_iterator)
        elif self.selection_strategy == "random":
            selected_url = random.choice(self.base_urls)
        elif self.selection_strategy == "consistency_hash_by_api_key":
            selected_url = self.base_urls[hash(api_key) % len(self.base_urls)]
        else:
            logger.warning(f"Unknown base URL selection strategy: {self.selection_strategy}. Falling back to round_robin.")
            selected_url = next(self._round_robin_iterator)
        logger.debug(f"Returning selected base URL from _select_base_url: {selected_url}")
        return selected_url

async def run_test():
    print("--- Test Scenario 1: Invalid base_url and selection_strategy ---")
    base_urls_1 = ["h"] # Simulate corrupted URL
    selection_strategy_1 = "300" # Simulate invalid strategy

    api_client_1 = MockGeminiApiClient(
        base_urls=base_urls_1,
        selection_strategy=selection_strategy_1
    )

    dummy_api_key = "test_api_key_1"
    selected_base_url_1 = api_client_1._select_base_url(dummy_api_key)
    print(f"DEBUG [test_runner]: Final selected base URL from client 1: {selected_base_url_1}")
    assert selected_base_url_1 == "h", f"Expected 'h', got {selected_base_url_1}"
    print("Assertion passed for Scenario 1: selected_base_url is 'h'")

    model_name = "gemini-1.5-flash"
    final_url_1 = f"{selected_base_url_1}/models/{model_name}:generateContent?key={dummy_api_key}"
    print(f"DEBUG [test_runner]: Constructed final URL 1: {final_url_1}")
    assert final_url_1 == "h/models/gemini-1.5-flash:generateContent?key=test_api_key_1", f"Expected 'h/models/gemini-1.5-flash:generateContent?key=test_api_key_1', got {final_url_1}"
    print("Assertion passed for Scenario 1: constructed URL is correct")


    print("\n--- Test Scenario 2: Correct base_url and selection_strategy ---")
    base_urls_2 = ["https://generativelanguage.googleapis.com/v1beta"]
    selection_strategy_2 = "round_robin"

    api_client_2 = MockGeminiApiClient(
        base_urls=base_urls_2,
        selection_strategy=selection_strategy_2
    )

    dummy_api_key = "test_api_key_2"
    selected_base_url_2 = api_client_2._select_base_url(dummy_api_key)
    print(f"DEBUG [test_runner]: Final selected base URL from client 2: {selected_base_url_2}")
    assert selected_base_url_2 == "https://generativelanguage.googleapis.com/v1beta", f"Expected 'https://generativelanguage.googleapis.com/v1beta', got {selected_base_url_2}"
    print("Assertion passed for Scenario 2: selected_base_url is correct")

    final_url_2 = f"{selected_base_url_2}/models/{model_name}:generateContent?key={dummy_api_key}"
    print(f"DEBUG [test_runner]: Constructed final URL 2: {final_url_2}")
    assert final_url_2 == "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=test_api_key_2", f"Expected 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=test_api_key_2', got {final_url_2}"
    print("Assertion passed for Scenario 2: constructed URL is correct")


if __name__ == "__main__":
    asyncio.run(run_test())