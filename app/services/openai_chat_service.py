# app/services/chat_service.py

import json
from typing import Dict, Any, AsyncGenerator, List, Union
from app.core.logger import get_openai_logger
from app.services.chat.message_converter import OpenAIMessageConverter
from app.services.chat.response_handler import OpenAIResponseHandler
from app.services.chat.api_client import GeminiApiClient
from app.schemas.openai_models import ChatRequest
from app.core.config import settings
from app.services.key_manager import KeyManager

logger = get_openai_logger()


def _has_image_parts(contents: List[Dict[str, Any]]) -> bool:
    """判断消息是否包含图片部分"""
    for content in contents:
        if "parts" in content:
            for part in content["parts"]:
                if "image_url" in part or "inline_data" in part:
                    return True
    return False


def _build_tools(
        request: ChatRequest, messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """构建工具"""
    tools = []
    model = request.model

    if (
        settings.TOOLS_CODE_EXECUTION_ENABLED
        and not (model.endswith("-search") or "-thinking" or "lite" in model)
        and not _has_image_parts(messages)
    ):
        tools.append({"code_execution": {}})
    if model.endswith("-search"):
        tools.append({"googleSearch": {}})
    return tools


def _get_safety_settings(model: str) -> List[Dict[str, str]]:
    """获取安全设置"""
    # if (
    #     "2.0" in model
    #     and "gemini-2.0-flash-thinking-exp" not in model
    #     and "gemini-2.0-pro-exp" not in model
    # ):
    if model == "gemini-2.0-flash-exp":
        return [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "OFF"},
        ]
    return [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
    ]


def _build_payload(
        request: ChatRequest, messages: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """构建请求payload"""
    return {
        "contents": messages,
        "generationConfig": {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
            "stopSequences": request.stop,
            "topP": request.top_p,
            "topK": request.top_k,
        },
        "tools": _build_tools(request, messages),
        "safetySettings": _get_safety_settings(request.model),
    }


class OpenAIChatService:
    """聊天服务"""

    def __init__(self, base_url: str, key_manager: KeyManager):
        self.message_converter = OpenAIMessageConverter()
        self.response_handler = OpenAIResponseHandler(config=None)
        self.api_client = GeminiApiClient(base_url)
        self.key_manager = key_manager

    async def create_chat_completion(
        self,
        request: ChatRequest,
        api_key: str,
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """创建聊天完成"""
        # 转换消息格式
        messages = self.message_converter.convert(request.messages)

        # 构建请求payload
        payload = _build_payload(request, messages)

        if request.stream:
            return self._handle_stream_completion(request.model, payload, api_key)
        return self._handle_normal_completion(request.model, payload, api_key)

    def _handle_normal_completion(
        self, model: str, payload: Dict[str, Any], api_key: str
    ) -> Dict[str, Any]:
        """处理普通聊天完成"""
        response = self.api_client.generate_content(payload, model, api_key)
        return self.response_handler.handle_response(
            response, model, stream=False, finish_reason="stop"
        )

    async def _handle_stream_completion(
        self, model: str, payload: Dict[str, Any], api_key: str
    ) -> AsyncGenerator[str, None]:
        """处理流式聊天完成，添加重试逻辑"""
        retries = 0
        max_retries = 3
        while retries < max_retries:
            try:
                async for line in self.api_client.stream_generate_content(
                    payload, model, api_key
                ):
                    # print(line)
                    if line.startswith("data:"):
                        chunk = json.loads(line[6:])
                        openai_chunk = self.response_handler.handle_response(
                            chunk, model, stream=True, finish_reason=None
                        )
                        if openai_chunk:
                            yield f"data: {json.dumps(openai_chunk)}\n\n"
                yield f"data: {json.dumps(self.response_handler.handle_response({}, model, stream=True, finish_reason='stop'))}\n\n"
                yield "data: [DONE]\n\n"
                logger.info("Streaming completed successfully")
                break  # 成功后退出循环
            except Exception as e:
                retries += 1
                logger.warning(
                    f"Streaming API call failed with error: {str(e)}. Attempt {retries} of {max_retries}"
                )
                api_key = await self.key_manager.handle_api_failure(api_key)
                logger.info(f"Switched to new API key: {api_key}")
                if retries >= max_retries:
                    logger.error(
                        f"Max retries ({max_retries}) reached for streaming. Raising error"
                    )
                    yield f"data: {json.dumps({'error': 'Streaming failed after retries'})}\n\n"
                    yield "data: [DONE]\n\n"
                    break
