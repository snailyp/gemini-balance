"""
原生Gemini TTS响应处理器扩展
继承自原始响应处理器，添加原生Gemini TTS支持，保持向后兼容
"""

from typing import Any, Dict, Optional
from app.handler.response_handler import GeminiResponseHandler
from app.log.logger import get_gemini_logger

logger = get_gemini_logger()


class TTSResponseHandler(GeminiResponseHandler):
    """
    支持TTS的响应处理器
    继承自原始的GeminiResponseHandler，添加TTS响应处理
    """

    def handle_response(
        self, response: Dict[str, Any], model: str, stream: bool = False, usage_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理响应，支持TTS音频数据
        """
        # 检查是否是TTS响应（包含音频数据）
        if self._is_tts_response(response):
            logger.info("Detected TTS response with audio data, returning original response")
            return response
        
        # 对于非TTS响应，使用父类的处理方法
        return super().handle_response(response, model, stream, usage_metadata)

    def _is_tts_response(self, response: Dict[str, Any]) -> bool:
        """
        检查是否是TTS响应
        """
        try:
            if (response.get("candidates") and
                len(response["candidates"]) > 0 and
                response["candidates"][0].get("content") and
                response["candidates"][0]["content"].get("parts") and
                len(response["candidates"][0]["content"]["parts"]) > 0):
                
                parts = response["candidates"][0]["content"]["parts"]
                for part in parts:
                    if "inlineData" in part:
                        mime_type = part["inlineData"].get("mimeType", "")
                        if mime_type.startswith("audio/"):
                            return True
            return False
        except Exception as e:
            logger.warning(f"Error checking TTS response: {e}")
            return False
