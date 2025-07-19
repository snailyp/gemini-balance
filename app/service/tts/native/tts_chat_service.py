"""
原生Gemini TTS聊天服务扩展
继承自原始聊天服务，添加原生Gemini TTS支持（单人和多人），保持向后兼容
"""

import time
import datetime
from typing import Any, Dict
from app.service.chat.gemini_chat_service import GeminiChatService
from app.service.tts.native.tts_response_handler import TTSResponseHandler
from app.domain.gemini_models import GeminiRequest
from app.log.logger import get_gemini_logger
from app.database.services import add_request_log, add_error_log

logger = get_gemini_logger()


class TTSGeminiChatService(GeminiChatService):
    """
    支持TTS的Gemini聊天服务
    继承自原始的GeminiChatService，添加TTS功能
    """

    def __init__(self, base_url: str, key_manager):
        """
        初始化TTS聊天服务
        """
        super().__init__(base_url, key_manager)
        # 使用TTS响应处理器替换原始处理器
        self.response_handler = TTSResponseHandler()
        logger.info("TTS Gemini Chat Service initialized with multi-speaker TTS support")

    async def generate_content(
        self, model: str, request: GeminiRequest, api_key: str
    ) -> Dict[str, Any]:
        """
        生成内容，支持TTS
        """
        try:
            # 添加调试日志
            logger.info(f"TTS request model: {model}")
            logger.info(f"TTS request generationConfig: {request.generationConfig}")

            # 检查是否是TTS模型，如果是，需要特殊处理
            if "tts" in model.lower():
                logger.info("Detected TTS model, applying TTS-specific processing")
                # 对于TTS模型，我们需要确保正确的字段被传递
                response = await self._handle_tts_request(model, request, api_key)
                return response
            else:
                # 对于非TTS模型，使用父类的方法
                response = await super().generate_content(model, request, api_key)
                return response
        except Exception as e:
            logger.error(f"TTS API call failed with error: {e}")
            raise

    async def _handle_tts_request(self, model: str, request: GeminiRequest, api_key: str) -> Dict[str, Any]:
        """
        处理TTS特定的请求，包含完整的日志记录功能
        """
        # 记录开始时间和请求时间
        start_time = time.perf_counter()
        request_datetime = datetime.datetime.now()
        is_success = False
        status_code = None

        try:
            # 构建TTS专用的payload - 不包含tools和safetySettings
            from app.service.chat.gemini_chat_service import _filter_empty_parts

            request_dict = request.model_dump(exclude_none=False)

            # 构建TTS专用的简化payload
            payload = {
                "contents": _filter_empty_parts(request_dict.get("contents", [])),
                "generationConfig": request_dict.get("generationConfig", {}),
            }

            # 只在有systemInstruction时才添加
            if request_dict.get("systemInstruction"):
                payload["systemInstruction"] = request_dict.get("systemInstruction")

            # 确保 generationConfig 不为 None
            if payload["generationConfig"] is None:
                payload["generationConfig"] = {}

            # 从request.generationConfig直接获取TTS相关字段
            if request.generationConfig:
                # 添加TTS特定字段
                if request.generationConfig.responseModalities:
                    payload["generationConfig"]["responseModalities"] = request.generationConfig.responseModalities
                    logger.info(f"Added responseModalities: {request.generationConfig.responseModalities}")

                if request.generationConfig.speechConfig:
                    payload["generationConfig"]["speechConfig"] = request.generationConfig.speechConfig
                    logger.info(f"Added speechConfig: {request.generationConfig.speechConfig}")
            else:
                logger.warning("No generationConfig found in request, TTS fields may be missing")

            logger.info(f"TTS payload before API call: {payload}")

            # 调用API
            response = await self.api_client.generate_content(payload, model, api_key)

            # 如果到达这里，说明API调用成功
            is_success = True
            status_code = 200

            # 使用TTS响应处理器处理响应
            return self.response_handler.handle_response(response, model, False, None)

        except Exception as e:
            # 记录错误
            is_success = False
            error_msg = str(e)

            # 尝试从错误消息中提取状态码
            import re
            match = re.search(r"status code (\d+)", error_msg)
            if match:
                status_code = int(match.group(1))
            else:
                status_code = 500

            # 添加错误日志
            await add_error_log(
                gemini_key=api_key,
                model_name=model,
                error_type="tts-api-error",
                error_log=error_msg,
                error_code=status_code,
                request_msg=request.model_dump(exclude_none=False)
            )

            logger.error(f"TTS API call failed: {error_msg}")
            raise

        finally:
            # 记录请求日志
            end_time = time.perf_counter()
            latency_ms = int((end_time - start_time) * 1000)

            await add_request_log(
                model_name=model,
                api_key=api_key,
                is_success=is_success,
                status_code=status_code,
                latency_ms=latency_ms,
                request_time=request_datetime
            )
