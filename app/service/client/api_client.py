# app/services/chat/api_client.py

from typing import Dict, Any, AsyncGenerator, Optional
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


class GeminiApiClient(ApiClient):
    """Gemini API客户端"""

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout

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

    def _prepare_headers(self) -> Dict[str, str]:
        headers = {}
        if settings.CUSTOM_HEADERS:
            headers.update(settings.CUSTOM_HEADERS)
            logger.info(f"Using custom headers: {settings.CUSTOM_HEADERS}")
        return headers

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

        headers = self._prepare_headers()
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/models?key={api_key}&pageSize=1000"
            try:
                response = await client.get(url, headers=headers)
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
        
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")
            
        headers = self._prepare_headers()
        
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/models/{model}:generateContent?key={api_key}"
            
            try:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error_content = response.text
                    logger.error(f"API call failed - Status: {response.status_code}, Content: {error_content}")
                    raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
                
                response_data = response.json()
                
                # 检查响应结构的基本信息
                if not response_data.get("candidates"):
                    logger.warning("No candidates found in API response")
                
                return response_data
                
            except httpx.TimeoutException as e:
                logger.error(f"Request timeout: {e}")
                raise Exception(f"Request timeout: {e}")
            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                raise Exception(f"Request error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

    async def stream_generate_content(self, payload: Dict[str, Any], model: str, api_key: str) -> AsyncGenerator[str, None]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        model = self._get_real_model(model)
        
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        headers = self._prepare_headers()
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
            async with client.stream(method="POST", url=url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_content = await response.aread()
                    error_msg = error_content.decode("utf-8")
                    raise Exception(f"API call failed with status code {response.status_code}, {error_msg}")
                async for line in response.aiter_lines():
                    yield line

    async def count_tokens(self, payload: Dict[str, Any], model: str, api_key: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        model = self._get_real_model(model)

        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for counting tokens: {proxy_to_use}")

        headers = self._prepare_headers()
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/models/{model}:countTokens?key={api_key}"
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_content = response.text
                raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
            return response.json()

    async def embed_content(self, payload: Dict[str, Any], model: str, api_key: str) -> Dict[str, Any]:
        """单一嵌入内容生成"""
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        model = self._get_real_model(model)
        
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for embedding: {proxy_to_use}")

        headers = self._prepare_headers()
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/models/{model}:embedContent?key={api_key}"
            
            try:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error_content = response.text
                    logger.error(f"Embedding API call failed - Status: {response.status_code}, Content: {error_content}")
                    raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
                
                return response.json()
                
            except httpx.TimeoutException as e:
                logger.error(f"Embedding request timeout: {e}")
                raise Exception(f"Request timeout: {e}")
            except httpx.RequestError as e:
                logger.error(f"Embedding request error: {e}")
                raise Exception(f"Request error: {e}")
            except Exception as e:
                logger.error(f"Unexpected embedding error: {e}")
                raise

    async def batch_embed_contents(self, payload: Dict[str, Any], model: str, api_key: str) -> Dict[str, Any]:
        """批量嵌入内容生成"""
        timeout = httpx.Timeout(self.timeout, read=self.timeout)
        model = self._get_real_model(model)
        
        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for batch embedding: {proxy_to_use}")

        headers = self._prepare_headers()
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/models/{model}:batchEmbedContents?key={api_key}"
            
            try:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    error_content = response.text
                    logger.error(f"Batch embedding API call failed - Status: {response.status_code}, Content: {error_content}")
                    raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
                
                return response.json()
                
            except httpx.TimeoutException as e:
                logger.error(f"Batch embedding request timeout: {e}")
                raise Exception(f"Request timeout: {e}")
            except httpx.RequestError as e:
                logger.error(f"Batch embedding request error: {e}")
                raise Exception(f"Request error: {e}")
            except Exception as e:
                logger.error(f"Unexpected batch embedding error: {e}")
                raise


class OpenaiApiClient(ApiClient):
    """OpenAI API客户端"""

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        
    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {api_key}"}
        if settings.CUSTOM_HEADERS:
            headers.update(settings.CUSTOM_HEADERS)
            logger.info(f"Using custom headers: {settings.CUSTOM_HEADERS}")
        return headers

    async def get_models(self, api_key: str) -> Dict[str, Any]:
        timeout = httpx.Timeout(self.timeout, read=self.timeout)

        proxy_to_use = None
        if settings.PROXIES:
            if settings.PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY:
                proxy_to_use = settings.PROXIES[hash(api_key) % len(settings.PROXIES)]
            else:
                proxy_to_use = random.choice(settings.PROXIES)
            logger.info(f"Using proxy for getting models: {proxy_to_use}")

        headers = self._prepare_headers(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/openai/models"
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

        headers = self._prepare_headers(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/openai/chat/completions"
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

        headers = self._prepare_headers(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/openai/chat/completions"
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

        headers = self._prepare_headers(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/openai/embeddings"
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

        headers = self._prepare_headers(api_key)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_to_use) as client:
            url = f"{self.base_url}/openai/images/generations"
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_content = response.text
                raise Exception(f"API call failed with status code {response.status_code}, {error_content}")
            return response.json()