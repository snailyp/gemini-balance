import asyncio
import json
import datetime
import time
from typing import Any, AsyncGenerator, Dict, List

from app.config.config import settings
from app.core.constants import GEMINI_2_FLASH_EXP_SAFETY_SETTINGS
from app.domain.gemini_models import GeminiRequest
from app.exception.exceptions import DownstreamApiError, ServiceUnavailableError
from app.handler.response_handler import GeminiResponseHandler
from app.handler.stream_optimizer import gemini_optimizer
from app.log.logger import get_gemini_logger
from app.service.client.api_client import GeminiApiClient
from app.service.key.key_manager import KeyManager
from app.database.services import error_log_service, request_log_service

logger = get_gemini_logger()


def _has_image_parts(contents: List[Dict[str, Any]]) -> bool:
    """判断消息是否包含图片部分"""
    for content in contents:
        if "parts" in content:
            for part in content["parts"]:
                if "image_url" in part or "inline_data" in part:
                    return True
    return False


def _build_tools(model: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """构建工具"""
    
    def _merge_tools(tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        record = dict()
        for item in tools:
            if not item or not isinstance(item, dict):
                continue

            for k, v in item.items():
                if k == "functionDeclarations" and v and isinstance(v, list):
                    functions = record.get("functionDeclarations", [])
                    functions.extend(v)
                    record["functionDeclarations"] = functions
                else:
                    record[k] = v
        return record

    tool = dict()
    if payload and isinstance(payload, dict) and "tools" in payload:
        if payload.get("tools") and isinstance(payload.get("tools"), dict):
            payload["tools"] = [payload.get("tools")]
        items = payload.get("tools", [])
        if items and isinstance(items, list):
            tool.update(_merge_tools(items))

    if (
        settings.TOOLS_CODE_EXECUTION_ENABLED
        and not (model.endswith("-search") or "-thinking" in model)
        and not _has_image_parts(payload.get("contents", []))
    ):
        tool["codeExecution"] = {}
    if model.endswith("-search"):
        tool["googleSearch"] = {}

    # 解决 "Tool use with function calling is unsupported" 问题
    if tool.get("functionDeclarations"):
        tool.pop("googleSearch", None)
        tool.pop("codeExecution", None)

    return [tool] if tool else []


def _get_safety_settings(model: str) -> List[Dict[str, str]]:
    """获取安全设置"""
    if model == "gemini-2.0-flash-exp" or model == "gemini-2.5-pro":
        return GEMINI_2_FLASH_EXP_SAFETY_SETTINGS
    return settings.SAFETY_SETTINGS


def _build_payload(model: str, request: GeminiRequest) -> Dict[str, Any]:
    """构建请求payload"""
    request_dict = request.model_dump()
    if request.generationConfig:
        if request.generationConfig.maxOutputTokens is None:
            # 如果未指定最大输出长度，则不传递该字段，解决截断的问题
            request_dict["generationConfig"].pop("maxOutputTokens")
    
    payload = {
        "contents": request_dict.get("contents", []),
        "tools": _build_tools(model, request_dict),
        "safetySettings": _get_safety_settings(model),
        "generationConfig": request_dict.get("generationConfig"),
        "systemInstruction": request_dict.get("systemInstruction"),
    }

    if model.endswith("-image") or model.endswith("-image-generation"):
        payload.pop("systemInstruction")
        payload["generationConfig"]["responseModalities"] = ["Text", "Image"]
    
    # 处理思考配置：优先使用客户端提供的配置，否则使用默认配置
    client_thinking_config = None
    if request.generationConfig and request.generationConfig.thinkingConfig:
        client_thinking_config = request.generationConfig.thinkingConfig
    
    if client_thinking_config is not None:
        # 客户端提供了思考配置，直接使用
        payload["generationConfig"]["thinkingConfig"] = client_thinking_config
    else:
        # 客户端没有提供思考配置，使用默认配置    
        if model.endswith("-non-thinking"):
            payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0} 
        elif model in settings.THINKING_BUDGET_MAP:
            payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": settings.THINKING_BUDGET_MAP.get(model,1000)}

    return payload


class GeminiChatService:
    """聊天服务"""

    def __init__(self, base_url: List[str], key_manager: KeyManager):
        self.base_url = base_url
        self.api_client = GeminiApiClient(base_url, settings.GEMINI_BASE_URL_SELECTION_STRATEGY, settings.TIME_OUT)
        self.key_manager = key_manager
        self.response_handler = GeminiResponseHandler()

    def _extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """从响应中提取文本内容"""
        if not response.get("candidates"):
            return ""
        candidate = response["candidates"][0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        if parts and "text" in parts[0]:
            return parts[0].get("text", "")
        return ""

    def _create_char_response(self, original_response: Dict[str, Any], text: str) -> Dict[str, Any]:
        """创建包含指定文本的响应"""
        response_copy = json.loads(json.dumps(original_response))
        if response_copy.get("candidates") and response_copy["candidates"][0].get("content", {}).get("parts"):
            response_copy["candidates"][0]["content"]["parts"][0]["text"] = text
        return response_copy

    async def generate_content(self, model: str, request: GeminiRequest) -> Dict[str, Any]:
        """生成内容"""
        payload = _build_payload(model, request)
        last_exception = None

        for attempt in range(settings.MAX_RETRIES):
            current_api_key = None
            try:
                current_api_key = await self.key_manager.get_key_with_token(model)
                
                request_datetime = datetime.datetime.now()
                start_time = time.perf_counter()
                
                response = await self.api_client.generate_content(payload, model, current_api_key)
                
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                await request_log_service.add_log(
                    model_name=model, api_key=current_api_key, is_success=True,
                    status_code=200, latency_ms=latency_ms, request_time=request_datetime
                )
                return self.response_handler.handle_response(response, model, stream=False)

            except DownstreamApiError as e:
                last_exception = e
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                logger.error(f"Attempt {attempt + 1}/{settings.MAX_RETRIES} with key ...{current_api_key[-4:]} failed with status code {e.status_code}: {e.detail}")

                await error_log_service.add_log(
                    gemini_key=current_api_key, model_name=model, error_type="gemini-chat-non-stream",
                    error_log=e.detail, error_code=e.status_code, request_msg=payload
                )
                await request_log_service.add_log(
                    model_name=model, api_key=current_api_key, is_success=False,
                    status_code=e.status_code, latency_ms=latency_ms, request_time=request_datetime
                )

                if 400 <= e.status_code < 500 and e.status_code != 429:
                    # Client-side error (e.g., bad request). Retrying won't help.
                    raise e
                
                # For 5xx errors or 429 (though 429 should be rare now), penalize and retry
                await self.key_manager.handle_api_failure(current_api_key, status_code=e.status_code)
                logger.warning("Trying next available key...")

            except ServiceUnavailableError as e:
                # Raised by get_key_with_token if no keys are available
                logger.error("No available API keys for the request.")
                raise e from last_exception

        logger.error("All retry attempts failed.")
        raise ServiceUnavailableError("All retry attempts failed to process the request.") from last_exception

    async def stream_generate_content(self, model: str, request: GeminiRequest) -> AsyncGenerator[str, None]:
        """流式生成内容"""
        payload = _build_payload(model, request)
        last_exception = None
        
        for attempt in range(settings.MAX_RETRIES):
            current_api_key = None
            try:
                current_api_key = await self.key_manager.get_key_with_token(model)
                
                request_datetime = datetime.datetime.now()
                start_time = time.perf_counter()
                is_success = False
                status_code = None

                async for line in self.api_client.stream_generate_content(payload, model, current_api_key):
                    if line.startswith("data:"):
                        line = line[6:]
                    
                    json_objects = []
                    decoder = json.JSONDecoder()
                    idx = 0
                    while idx < len(line):
                        try:
                            obj, end = decoder.raw_decode(line[idx:])
                            json_objects.append(obj)
                            idx += end
                            while idx < len(line) and line[idx].isspace():
                                idx += 1
                        except json.JSONDecodeError:
                            logger.warning(f"Non-JSON data in stream: {line[idx:]}")
                            break
                    
                    for response_data in json_objects:
                        response_data = self.response_handler.handle_response(response_data, model, stream=True)
                        text = self._extract_text_from_response(response_data)
                        
                        if text and settings.STREAM_OPTIMIZER_ENABLED:
                            async for optimized_chunk in gemini_optimizer.optimize_stream_output(
                                text,
                                lambda t: self._create_char_response(response_data, t),
                                lambda c: "data: " + json.dumps(c) + "\n\n",
                            ):
                                yield optimized_chunk
                        else:
                            yield "data: " + json.dumps(response_data) + "\n\n"
                
                is_success = True
                status_code = 200
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                await request_log_service.add_log(
                    model_name=model, api_key=current_api_key, is_success=is_success,
                    status_code=status_code, latency_ms=latency_ms, request_time=request_datetime
                )
                return # Successful stream, exit generator

            except DownstreamApiError as e:
                last_exception = e
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                logger.warning(f"Streaming API call failed on attempt {attempt + 1}/{settings.MAX_RETRIES} with key ...{current_api_key[-4:]}: {e.detail}")
                
                await error_log_service.add_log(
                    gemini_key=current_api_key, model_name=model, error_type="gemini-chat-stream",
                    error_log=e.detail, error_code=e.status_code, request_msg=payload
                )
                await request_log_service.add_log(
                    model_name=model, api_key=current_api_key, is_success=False,
                    status_code=e.status_code, latency_ms=latency_ms, request_time=request_datetime
                )

                if 400 <= e.status_code < 500 and e.status_code != 429:
                    raise e

                await self.key_manager.handle_api_failure(current_api_key, status_code=e.status_code)
                logger.info("Trying next available key for stream...")

            except ServiceUnavailableError as e:
                logger.error("No available API keys for the streaming request.")
                raise e from last_exception
        
        logger.error("All retry attempts failed for the streaming request.")
        raise ServiceUnavailableError("All available keys failed to process the streaming request.") from last_exception
