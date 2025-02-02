import httpx
from typing import Dict, Any, List
from app.core.logger import get_embeddings_logger
from app.services.key_manager import KeyManager
from app.schemas.openai_models import EmbeddingRequest
from app.core.config import settings

logger = get_embeddings_logger()

class EmbeddingService:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager

    async def create_embedding(self, request: EmbeddingRequest) -> Dict[str, Any]:
        """创建文本嵌入"""
        try:
            # 获取下一个可用的API密钥配置
            key_config = await self.key_manager.get_next_working_key_config()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key_config.key}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.BASE_URL}/embeddings",
                    headers=headers,
                    json={
                        "input": request.input,
                        "model": request.model
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Embedding request failed with status {response.status_code}: {response.text}")
                    # 处理API密钥失败
                    await self.key_manager.handle_api_failure(key_config.key)
                    # 重试请求
                    return await self.create_embedding(request)
                
                return response.json()

        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            # 处理API密钥失败
            if 'key_config' in locals():
                await self.key_manager.handle_api_failure(key_config.key)
            raise
