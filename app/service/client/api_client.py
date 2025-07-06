# app/services/chat/api_client.py

from typing import Dict, Any, AsyncGenerator, Optional, List
import httpx
import random
from abc import ABC, abstractmethod
from app.config.config import settings
from app.exception.exceptions import DownstreamApiError
from app.log.logger import get_api_client_logger
from app.core.constants import DEFAULT_TIMEOUT
from app.service.key.key_manager import get_key_manager_instance

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
        logger.debug(f"GeminiApiClient __init__ received base_urls: {self.base_urls}")
        self._round_robin_iterator = itertools.cycle(self.base_urls)

    def _select_base_url(self, api_key: str) -> str:
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
        """Gets the list of available Gemini models, with pre-request key validation."""
        key_manager = await get_key_manager_instance()

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
            url = f"{base_url}/models?key={api_key}&pageSize=1000"
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to get model list: {e.response.status_code}")
                logger.error(e.response.text)
                if e.response.status_code == 403 and "API_KEY_INVALID" in e.response.text:
                    logger.warning(f"Deactivating invalid API key: {api_key[-4:]}")
                    await key_manager.handle_api_failure(api_key)
                return None
            except httpx.RequestError as e:
                logger.error(f"Request for model list failed: {e}")
                return None
            
    async def generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> Dict[str, Any]:
        key_manager = await get_key_manager_instance()

        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        model = self._get_real_model(model)
        base_url = self._select_base_url(api_key)
        logger.debug(f"Type of base_url: {type(base_url)}, Value of base_url: {base_url}")

        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")
            
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{base_url}/models/{model}:generateContent?key={api_key}"
            logger.debug(f"Final request URL: {url}")
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400 and "API_KEY_INVALID" in e.response.text:
                    logger.warning(f"Deactivating invalid API key: {api_key[-4:]}")
                    await key_manager.handle_api_failure(api_key)
                elif e.response.status_code == 403:
                    await key_manager.handle_api_failure(api_key)
                raise DownstreamApiError(status_code=e.response.status_code, detail=e.response.text)

    async def stream_generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> AsyncGenerator[str, None]:
        key_manager = await get_key_manager_instance()

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
            try:
                async with client.stream(method="POST", url=url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        logger.debug(f"Raw stream line: {line}")
                        yield line
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400 and "API_KEY_INVALID" in e.response.text:
                    logger.warning(f"Deactivating invalid API key: {api_key[-4:]}")
                    await key_manager.handle_api_failure(api_key)
                elif e.response.status_code == 403:
                    await key_manager.handle_api_failure(api_key)
                error_msg = e.response.text
                raise DownstreamApiError(status_code=e.response.status_code, detail=error_msg)


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
        key_manager = await get_key_manager_instance()

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
            url = f"{base_url}/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.warning(f"Deactivating invalid OpenAI key: {api_key[-4:]}")
                    await key_manager.handle_api_failure(api_key)
                raise Exception(f"API call failed with status code {e.response.status_code}, {e.response.text}")

    async def generate_content(self, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        key_manager = await get_key_manager_instance()

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
            url = f"{base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    logger.warning(f"Deactivating invalid OpenAI key: {api_key[-4:]}")
                    await key_manager.handle_api_failure(api_key)
                raise Exception(f"API call failed with status code {e.response.status_code}, {e.response.text}")

    async def stream_generate_content(self, payload: Dict[str, Any], api_key: str) -> AsyncGenerator[str, None]:
        key_manager = await get_key_manager_instance()

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
            url = f"{base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                async with client.stream(method="POST", url=url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        yield line
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    logger.warning(f"Deactivating invalid OpenAI key: {api_key[-4:]}")
                    await key_manager.handle_api_failure(api_key)
                error_content = await e.response.aread()
                error_msg = error_content.decode("utf-8")
                raise Exception(f"API call failed with status code {e.response.status_code}, {error_msg}")

    async def create_embeddings(self, input: str, model: str, api_key: str) -> Dict[str, Any]:
        key_manager = await get_key_manager_instance()

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
            url = f"{base_url}/embeddings"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "input": input,
                "model": model,
            }
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.warning(f"Deactivating invalid OpenAI key: {api_key[-4:]}")
                    await key_manager.handle_api_failure(api_key)
                raise Exception(f"API call failed with status code {e.response.status_code}, {e.response.text}")

    async def generate_images(self, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        key_manager = await get_key_manager_instance()

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
            url = f"{base_url}/images/generations"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    logger.warning(f"Deactivating invalid OpenAI key: {api_key[-4:]}")
                    await key_manager.handle_api_failure(api_key)
                raise Exception(f"API call failed with status code {e.response.status_code}, {e.response.text}")
