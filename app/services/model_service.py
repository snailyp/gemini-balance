from datetime import datetime, timezone
from typing import Dict, Any, List
from app.core.logger import get_model_logger
from app.core.config import settings

logger = get_model_logger()

class ModelService:
    def __init__(self):
        self.models = self._build_models_list(settings.AVAILABLE_MODELS)

    def _build_models_list(self, model_ids: List[str]) -> Dict[str, Any]:
        """根据配置的模型ID列表构建模型信息"""
        return {
            "data": [
                {
                    "id": model_id,
                    "object": "model",
                    "created": int(datetime.now(timezone.utc).timestamp()),
                    "owned_by": "openai",
                    "permission": [],
                    "root": model_id,
                    "parent": None,
                } for model_id in model_ids
            ],
            "object": "list",
            "success": True
        }

    def get_models(self) -> Dict[str, Any]:
        return self.models
