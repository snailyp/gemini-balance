# app/services/chat/api_client.py

from typing import Dict, Any, AsyncGenerator, Optional, List
import httpx
import random
from abc import ABC, abstractmethod
from app.config.config import settings
from app.log.logger import get_api_client_logger
from app.core.constants import DEFAULT_TIMEOUT

logger = get_api_client_logger()

class ApiClient(ABC):
    """API客户端基类"""

    @abstractmethod
    async def generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def stream_generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> AsyncGenerator[str, None]:
        pass


import itertools

class GeminiApiClient(ApiClient):
    """Gemini API客户端"""

    def __init__(self, base_urls: List[str], selection_strategy: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_urls = base_urls
        self.selection_strategy = selection_strategy
        self.timeout = timeout
        self._round_robin_iterator = itertools.cycle(self.base_urls)

    def _select_base_url(self, api_key: str) -> str:
        if not self.base_urls:
            raise ValueError("No base URLs configured for Gemini API client.")

        if self.selection_strategy == "round_robin":
            return next(self._round_robin_iterator)
        elif self.selection_strategy == "random":
            return random.choice(self.base_urls)
        elif self.selection_strategy == "consistency_hash_by_api_key":
            return self.base_urls[hash(api_key) % len(self.base_urls)]
        else:
            logger.warning(f"Unknown base URL selection strategy: {self.selection_strategy}. Falling back to round_robin.")
            return next(self._round_robin_iterator)

    def _get_real_model(self, model: str) -> str:
        if model.endswith("-search"):
            model = model[:-7]
        if model.endswith("-image"):
            model = model[:-6]
        if model.endswith("-non-thinking"):
            model = model[:-13]
        if "-search" in model and "-non-thinking" in model:
            model = model[:-20]
        return model

    async def get_models(self, api_key: str) -> Optional[Dict[str, Any]]:
        """获取可用的 Gemini 模型列表"""
        timeout = httpx.Timeout(timeout=5)
        
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        base_url = self._select_base_url(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/models?key={api_key}"
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"获取模型列表失败: {e.response.status_code}")
                logger.error(e.response.text)
                return None
            except httpx.RequestError as e:
                logger.error(f"请求模型列表失败: {e}")
                return None
            
    async def generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        model = self._get_real_model(model)
        base_url = self._select_base_url(api_key)

        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")
            
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/models/{model}:generateContent?key={api_key}"
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                error_content = response.text
                raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
            return response.json()

    async def stream_generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> AsyncGenerator[str, None]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        model = self._get_real_model(model)
        base_url = self._select_base_url(api_key)
        
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
            async with client.stream(method="POST", url=url, json=payload) as response:
                if response.status_code != 200:
                    error_content = await response.aread()
                    error_msg = error_content.decode("utf-8")
                    raise Exception(f"API call failed with status code {response.status_code}, {error_msg}")
                async for line in response.aiter_lines():
                    yield line


class OpenaiApiClient(ApiClient):
    """OpenAI API客户端"""

    def __init__(self, base_urls: List[str], selection_strategy: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_urls = base_urls
        self.selection_strategy = selection_strategy
        self.timeout = timeout
        self._round_robin_iterator = itertools.cycle(self.base_urls)

    def _select_base_url(self, api_key: str) -> str:
        if not self.base_urls:
            raise ValueError("No base URLs configured for OpenAI API client.")

        if self.selection_strategy == "round_robin":
            return next(self._round_robin_iterator)
        elif self.selection_strategy == "random":
            return random.choice(self.base_urls)
        elif self.selection_strategy == "consistency_hash_by_api_key":
            return self.base_urls[hash(api_key) % len(self.base_urls)]
        else:
            logger.warning(f"Unknown base URL selection strategy: {self.selection_strategy}. Falling back to round_robin.")
            return next(self._round_robin_iterator)
        
    async def get_models(self, api_key: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)

        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        base_url = self._select_base_url(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/models" # Changed from /openai/models to /models
            headers = {"Authorization": f"Bearer {api_key}"}
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                error_content = response.text
                raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
            return response.json()

    async def generate_content(self, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        logger.info(f"settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY: {settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY}")
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        base_url = self._select_base_url(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/chat/completions" # Changed from /openai/chat/completions to /chat/completions
            headers = {"Authorization": f"Bearer {api_key}"}
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_content = response.text
                raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
            return response.json()

    async def stream_generate_content(self, payload: Dict[str, Any], api_key: str) -> AsyncGenerator[str, None]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        base_url = self._select_base_url(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/chat/completions" # Changed from /openai/chat/completions to /chat/completions
            headers = {"Authorization": f"Bearer {api_key}"}
            async with client.stream(method="POST", url=url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_content = await response.aread()
                    error_msg = error_content.decode("utf-8")
                    raise Exception(f"API call failed with status code {response.status_code}, {error_msg}")
                async for line in response.aiter_lines():
                    yield line
    
    async def create_embeddings(self, input: str, model: str, api_key: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        base_url = self._select_base_url(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/embeddings" # Changed from /openai/embeddings to /embeddings
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "input": input,
                "model": model,
            }
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_content = response.text
                raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
            return response.json()
                    
    async def generate_images(self, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)

        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        base_url = self._select_base_url(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/images/generations" # Changed from /openai/images/generations to /images/generations
            headers = {"Authorization": f"Bearer {api_key}"}
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_content = response.text
                raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
            return response.json()
