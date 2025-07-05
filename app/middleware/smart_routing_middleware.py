from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.config.config import settings
from app.log.logger import get_main_logger
import re

logger = get_main_logger()

class SmartRoutingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # 简化的路由规则 - 直接根据检测结果路由
        pass

    async def dispatch(self, request: Request, call_next):
        if not settings.URL_NORMALIZATION_ENABLED:
            return await call_next(request)
        logger.debug(f"request: {request}")
        original_path = str(request.url.path)
        method = request.method
        
        # 尝试修复URL
        fixed_path, fix_info = self.fix_request_url(original_path, method, request)

        if fixed_path != original_path:
            logger.info(f"URL fixed: {method} {original_path} → {fixed_path}")
            if fix_info:
                logger.debug(f"Fix details: {fix_info}")

            # 重写请求路径
            request.scope["path"] = fixed_path
            request.scope["raw_path"] = fixed_path.encode()
        
        return await call_next(request)

    def fix_request_url(self, path: str, method: str, request: Request) -> tuple:
        """简化的URL修复逻辑"""

        # 首先检查是否已经是正确的格式，如果是则不处理
        if self.is_already_correct_format(path):
            return path, None

        # 1. 最高优先级：包含generateContent → Gemini格式
        if "generatecontent" in path.lower() or "v1beta/models" in path.lower():
            return self.fix_gemini_by_operation(path, method, request)

        # 2. 第二优先级：包含/openai/ → OpenAI格式
        if "/openai/" in path.lower():
            return self.fix_openai_by_operation(path, method)

        # 3. 第三优先级：包含/v1/ → v1格式
        if "/v1/" in path.lower():
            return self.fix_v1_by_operation(path, method)

        # 4. 第四优先级：包含/chat/completions → chat功能
        if "/chat/completions" in path.lower():
            return "/v1/chat/completions", {"type": "v1_chat"}

        # 5. 默认：原样传递
        return path, None

    def is_already_correct_format(self, path: str) -> bool:
        """检查是否已经是正确的API格式"""
        # 检查是否已经是正确的端点格式
        correct_patterns = [
            r"^/v1beta/models/[^/:]+:(generate|streamGenerate)Content$",  # Gemini原生
            r"^/gemini/v1beta/models/[^/:]+:(generate|streamGenerate)Content$",  # Gemini带前缀
            r"^/v1beta/models$",  # Gemini模型列表
            r"^/gemini/v1beta/models$",  # Gemini带前缀的模型列表
            r"^/v1/(chat/completions|models|embeddings|images/generations|audio/speech)$",  # v1格式
            r"^/openai/v1/(chat/completions|models|embeddings|images/generations|audio/speech)$",  # OpenAI格式
            r"^/hf/v1/(chat/completions|models|embeddings|images/generations|audio/speech)$",  # HF格式
            r"^/vertex-express/v1beta/models/[^/:]+:(generate|streamGenerate)Content$",  # Vertex Express Gemini格式
            r"^/vertex-express/v1beta/models$",  # Vertex Express模型列表
            r"^/vertex-express/v1/(chat/completions|models|embeddings|images/generations)$",  # Vertex Express OpenAI格式
        ]

        for pattern in correct_patterns:
            if re.match(pattern, path):
                return True

        return False

    def fix_gemini_by_operation(
        self, path: str, method: str, request: Request
    ) -> tuple:
        """根据Gemini操作修复，考虑端点偏好"""
        if method == "GET":
            return "/v1beta/models", {
                "role": "gemini_models",
            }

        # 提取模型名称
        try:
            model_name = self.extract_model_name(path, request)
        except ValueError:
            # 无法提取模型名称，返回原路径不做处理
            return path, None

        # 检测是否为流式请求
        is_stream = self.detect_stream_request(path, request)

        # 检查是否有vertex-express偏好
        if "/vertex-express/" in path.lower():
            if is_stream:
                target_url = (
                    f"/vertex-express/v1beta/models/{model_name}:streamGenerateContent"
                )
            else:
                target_url = (
                    f"/vertex-express/v1beta/models/{model_name}:generateContent"
                )

            fix_info = {
                "rule": (
                    "vertex_express_generate"
                    if not is_stream
                    else "vertex_express_stream"
                ),
                "preference": "vertex_express_format",
                "is_stream": is_stream,
                "model": model_name,
            }
        else:
            # 标准Gemini端点
            if is_stream:
                target_url = f"/v1beta/models/{model_name}:streamGenerateContent"
            else:
                target_url = f"/v1beta/models/{model_name}:generateContent"

            fix_info = {
                "rule": "gemini_generate" if not is_stream else "gemini_stream",
                "preference": "gemini_format",
                "is_stream": is_stream,
                "model": model_name,
            }

        return target_url, fix_info

    def fix_openai_by_operation(self, path: str, method: str) -> tuple:
        """根据操作类型修复OpenAI格式"""
        if method == "POST":
            if "chat" in path.lower() or "completion" in path.lower():
                return "/openai/v1/chat/completions", {"type": "openai_chat"}
            elif "embedding" in path.lower():
                return "/openai/v1/embeddings", {"type": "openai_embeddings"}
            elif "image" in path.lower():
                return "/openai/v1/images/generations", {"type": "openai_images"}
            elif "audio" in path.lower():
                return "/openai/v1/audio/speech", {"type": "openai_audio"}
        elif method == "GET":
            if "model" in path.lower():
                return "/openai/v1/models", {"type": "openai_models"}

        return path, None

    def fix_v1_by_operation(self, path: str, method: str) -> tuple:
        """根据操作类型修复v1格式"""
        if method == "POST":
            if "chat" in path.lower() or "completion" in path.lower():
                return "/v1/chat/completions", {"type": "v1_chat"}
            elif "embedding" in path.lower():
                return "/v1/embeddings", {"type": "v1_embeddings"}
            elif "image" in path.lower():
                return "/v1/images/generations", {"type": "v1_images"}
            elif "audio" in path.lower():
                return "/v1/audio/speech", {"type": "v1_audio"}
        elif method == "GET":
            if "model" in path.lower():
                return "/v1/models", {"type": "v1_models"}

        return path, None

    def detect_stream_request(self, path: str, request: Request) -> bool:
        """检测是否为流式请求"""
        # 1. 路径中包含stream关键词
        if "stream" in path.lower():
            return True

        # 2. 查询参数
        if request.query_params.get("stream") == "true":
            return True

        return False

    def extract_model_name(self, path: str, request: Request) -> str:
        """从请求中提取模型名称，用于构建Gemini API URL"""
        # 1. 从请求体中提取
        try:
            if hasattr(request, "_body") and request._body:
                import json

                body = json.loads(request._body.decode())
                if "model" in body and body["model"]:
                    return body["model"]
        except Exception:
            pass

        # 2. 从查询参数中提取
        model_param = request.query_params.get("model")
        if model_param:
            return model_param

        # 3. 从路径中提取（用于已包含模型名称的路径）
        match = re.search(r"/models/([^/:]+)", path, re.IGNORECASE)
        if match:
            return match.group(1)

        # 4. 如果无法提取模型名称，抛出异常
        raise ValueError("Unable to extract model name from request")
