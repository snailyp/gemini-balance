from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config.config import settings
from app.log.logger import get_model_logger
from app.service.client.api_client import GeminiApiClient

logger = get_model_logger()


class ModelService:
    async def get_gemini_models(self, api_key: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Instantiating GeminiApiClient with settings.GEMINI_BASE_URL: {settings.GEMINI_BASE_URL}")
        api_client = GeminiApiClient(base_urls=settings.GEMINI_BASE_URL, selection_strategy=settings.GEMINI_BASE_URL_SELECTION_STRATEGY)
        logger.debug(f"GeminiApiClient initialized with base_urls: {settings.GEMINI_BASE_URL}, selection_strategy: {settings.GEMINI_BASE_URL_SELECTION_STRATEGY}")
        gemini_models = await api_client.get_models(api_key)

        if gemini_models is None:
            logger.error("从 API 客户端获取模型列表失败。")
            return None

        try:
            filtered_models_list = []
            for model in gemini_models.get("models", []):
                model_id = model["name"].split("/")[-1]
                if model_id not in settings.FILTERED_MODELS:
                    filtered_models_list.append(model)
                else:
                    logger.debug(f"Filtered out model: {model_id}")

            gemini_models["models"] = filtered_models_list
            return gemini_models
        except Exception as e:
            logger.error(f"处理模型列表时出错: {e}")
            return None

    async def get_gemini_openai_models(self, api_key: str) -> Optional[Dict[str, Any]]:
        """获取 Gemini 模型并转换为 OpenAI 格式"""
        gemini_models = await self.get_gemini_models(api_key)
        if gemini_models is None:
            return None
        
        return await self.convert_to_openai_models_format(gemini_models)

    async def convert_to_openai_models_format(
        self, gemini_models: Dict[str, Any]
    ) -> Dict[str, Any]:
        openai_format = {"object": "list", "data": [], "success": True}

        for model in gemini_models.get("models", []):
            model_id = model["name"].split("/")[-1]
            openai_model = {
                "id": model_id,
                "object": "model",
                "created": int(datetime.now(timezone.utc).timestamp()),
                "owned_by": "google",
                "permission": [],
                "root": model["name"],
                "parent": None,
            }
            openai_format["data"].append(openai_model)

            if model_id in settings.SEARCH_MODELS:
                search_model = openai_model.copy()
                search_model["id"] = f"{model_id}-search"
                openai_format["data"].append(search_model)
            if model_id in settings.IMAGE_MODELS:
                image_model = openai_model.copy()
                image_model["id"] = f"{model_id}-image"
                openai_format["data"].append(image_model)
            if model_id in settings.THINKING_MODELS:
                non_thinking_model = openai_model.copy()
                non_thinking_model["id"] = f"{model_id}-non-thinking"
                openai_format["data"].append(non_thinking_model)

        if settings.CREATE_IMAGE_MODEL:
            image_model = openai_model.copy()
            image_model["id"] = f"{settings.CREATE_IMAGE_MODEL}-chat"
            openai_format["data"].append(image_model)
        return openai_format

    async def check_model_support(self, model: str) -> bool:
        if not model or not isinstance(model, str):
            return False

        model = model.strip()
        if model.endswith("-search"):
            model = model[:-7]
            return model in settings.SEARCH_MODELS
        if model.endswith("-image"):
            model = model[:-6]
            return model in settings.IMAGE_MODELS

        return model not in settings.FILTERED_MODELS
