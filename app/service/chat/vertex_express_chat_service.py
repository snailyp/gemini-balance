# app/services/chat_service.py

import json
import re
import datetime
import time
from typing import Any, AsyncGenerator, Dict, List
from app.config.config import settings
from app.core.constants import GEMINI_2_FLASH_EXP_SAFETY_SETTINGS
from app.domain.gemini_models import GeminiRequest
from app.handler.response_handler import GeminiResponseHandler
from app.handler.stream_optimizer import gemini_optimizer
from app.log.logger import get_gemini_logger
from app.service.client.api_client import GeminiApiClient
from app.service.key.key_manager import KeyManager
from app.database.services import add_error_log, add_request_log

logger = get_gemini_logger()


def _has_image_parts(contents: List[Dict[str, Any]]) -> bool:
    """判断消息是否包含图片部分"""
    for content in contents:
        if "parts" in content:
            for part in content["parts"]:
                if "image_url" in part or "inline_data" in part:
                    return True
    return False


def _clean_json_schema_properties(obj: Any) -> Any:
    """清理JSON Schema中Gemini API不支持的字段"""
    if not isinstance(obj, dict):
        return obj
    
    # Gemini API不支持的JSON Schema字段
    unsupported_fields = {
        "exclusiveMaximum", "exclusiveMinimum", "const", "examples", 
        "contentEncoding", "contentMediaType", "if", "then", "else",
        "allOf", "anyOf", "oneOf", "not", "definitions", "$schema",
        "$id", "$ref", "$comment", "readOnly", "writeOnly"
    }
    
    cleaned = {}
    for key, value in obj.items():
        if key in unsupported_fields:
            continue
        if isinstance(value, dict):
            cleaned[key] = _clean_json_schema_properties(value)
        elif isinstance(value, list):
            cleaned[key] = [_clean_json_schema_properties(item) for item in value]
        else:
            cleaned[key] = value
    
    return cleaned


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
                    # 清理每个函数声明中的不支持字段
                    cleaned_functions = []
                    for func in v:
                        if isinstance(func, dict):
                            cleaned_func = _clean_json_schema_properties(func)
                            cleaned_functions.append(cleaned_func)
                        else:
                            cleaned_functions.append(func)
                    functions.extend(cleaned_functions)
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
    if model == "gemini-2.0-flash-exp":
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
            if settings.SHOW_THINKING_PROCESS:
                payload["generationConfig"]["thinkingConfig"] = {
                    "thinkingBudget": settings.THINKING_BUDGET_MAP.get(model,1000),
                    "includeThoughts": True
                }
            else:
                payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": settings.THINKING_BUDGET_MAP.get(model,1000)}

    return payload


class GeminiChatService:
    """聊天服务"""

    def __init__(self, base_url: str, key_manager: KeyManager):
        self.api_client = GeminiApiClient(base_url, settings.TIME_OUT)
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

    def _create_char_response(
        self, original_response: Dict[str, Any], text: str
    ) -> Dict[str, Any]:
        """创建包含指定文本的响应"""
        response_copy = json.loads(json.dumps(original_response))  # 深拷贝
        if response_copy.get("candidates") and response_copy["candidates"][0].get(
            "content", {}
        ).get("parts"):
            response_copy["candidates"][0]["content"]["parts"][0]["text"] = text
        return response_copy

    async def generate_content(
        self, model: str, request: GeminiRequest, api_key: str
    ) -> Dict[str, Any]:
        """生成内容"""
        payload = _build_payload(model, request)
        start_time = time.perf_counter()
        request_datetime = datetime.datetime.now()
        is_success = False
        status_code = None
        response = None

        try:
            response = await self.api_client.generate_content(payload, model, api_key)
            is_success = True
            status_code = 200
            return self.response_handler.handle_response(response, model, stream=False)
        except Exception as e:
            is_success = False
            error_log_msg = str(e)
            logger.error(f"Normal API call failed with error: {error_log_msg}")
            match = re.search(r"status code (\d+)", error_log_msg)
            if match:
                status_code = int(match.group(1))
            else:
                status_code = 500

            await add_error_log(
                gemini_key=api_key,
                model_name=model,
                error_type="gemini-chat-non-stream",
                error_log=error_log_msg,
                error_code=status_code,
                request_msg=payload
            )
            raise e
        finally:
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

    async def stream_generate_content(
        self, model: str, request: GeminiRequest, api_key: str
    ) -> AsyncGenerator[str, None]:
        """流式生成内容"""
        retries = 0
        max_retries = settings.MAX_RETRIES
        payload = _build_payload(model, request)
        is_success = False
        status_code = None
        final_api_key = api_key

        while retries < max_retries:
            request_datetime = datetime.datetime.now()
            start_time = time.perf_counter()
            current_attempt_key = api_key
            final_api_key = current_attempt_key # Update final key used
            try:
                async for line in self.api_client.stream_generate_content(
                    payload, model, current_attempt_key
                ):
                    # print(line)
                    if line.startswith("data:"):
                        line = line[6:]
                        response_data = self.response_handler.handle_response(
                            json.loads(line), model, stream=True
                        )
                        text = self._extract_text_from_response(response_data)
                        # 如果有文本内容，且开启了流式输出优化器，则使用流式输出优化器处理
                        if text and settings.STREAM_OPTIMIZER_ENABLED:
                            # 使用流式输出优化器处理文本输出
                            async for (
                                optimized_chunk
                            ) in gemini_optimizer.optimize_stream_output(
                                text,
                                lambda t: self._create_char_response(response_data, t),
                                lambda c: "data: " + json.dumps(c) + "\n\n",
                            ):
                                yield optimized_chunk
                        else:
                            # 如果没有文本内容（如工具调用等），整块输出
                            yield "data: " + json.dumps(response_data) + "\n\n"
                logger.info("Streaming completed successfully")
                is_success = True
                status_code = 200
                break
            except Exception as e:
                retries += 1
                is_success = False
                error_log_msg = str(e)
                logger.warning(
                    f"Streaming API call failed with error: {error_log_msg}. Attempt {retries} of {max_retries}"
                )
                match = re.search(r"status code (\d+)", error_log_msg)
                if match:
                    status_code = int(match.group(1))
                else:
                    status_code = 500

                await add_error_log(
                    gemini_key=current_attempt_key,
                    model_name=model,
                    error_type="gemini-chat-stream",
                    error_log=error_log_msg,
                    error_code=status_code,
                    request_msg=payload
                )

                api_key = await self.key_manager.handle_api_failure(current_attempt_key, retries)
                if api_key:
                    logger.info(f"Switched to new API key: {api_key}")
                else:
                    logger.error(f"No valid API key available after {retries} retries.")
                    break

                if retries >= max_retries:
                    logger.error(
                        f"Max retries ({max_retries}) reached for streaming."
                    )
                    break
            finally:
                end_time = time.perf_counter()
                latency_ms = int((end_time - start_time) * 1000)
                await add_request_log(
                    model_name=model,
                    api_key=final_api_key,
                    is_success=is_success,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    request_time=request_datetime
                )
