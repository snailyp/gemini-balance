import base64
import json
import random
import string
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.config.config import settings
from app.utils.uploader import ImageUploaderFactory


class ResponseHandler(ABC):
    """响应处理器基类"""

    @abstractmethod
    def handle_response(
        self, response: Dict[str, Any], model: str, stream: bool = False
    ) -> Dict[str, Any]:
        pass


class GeminiResponseHandler(ResponseHandler):
    """Gemini响应处理器"""

    def __init__(self):
        self.thinking_first = True
        self.thinking_status = False

    def handle_response(
        self, response: Dict[str, Any], model: str, stream: bool = False, usage_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if stream:
            return _handle_gemini_stream_response(response, model, stream)
        return _handle_gemini_normal_response(response, model, stream)


def _handle_openai_stream_response(
    response: Dict[str, Any], model: str, finish_reason: str, usage_metadata: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    text, reasoning_content, tool_calls, _ = _extract_result(
        response, model, stream=True, gemini_format=False
    )
    if not text and not tool_calls and not reasoning_content:
        delta = {}
    else:
        delta = {"content": text, "reasoning_content": reasoning_content, "role": "assistant"}
        if tool_calls:
            delta["tool_calls"] = tool_calls
    template_chunk = {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    if usage_metadata:
        template_chunk["usage"] = {"prompt_tokens": usage_metadata.get("promptTokenCount", 0), "completion_tokens": usage_metadata.get("candidatesTokenCount",0), "total_tokens": usage_metadata.get("totalTokenCount", 0)}
    return template_chunk


def _handle_openai_normal_response(
    response: Dict[str, Any], model: str, finish_reason: str, usage_metadata: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    text, reasoning_content, tool_calls, _ = _extract_result(
        response, model, stream=False, gemini_format=False
    )
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text,
                    "reasoning_content": reasoning_content,
                    "tool_calls": tool_calls,
                },
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": usage_metadata.get("promptTokenCount", 0), "completion_tokens": usage_metadata.get("candidatesTokenCount",0), "total_tokens": usage_metadata.get("totalTokenCount", 0)},
    }


class OpenAIResponseHandler(ResponseHandler):
    """OpenAI响应处理器"""

    def __init__(self, config):
        self.config = config
        self.thinking_first = True
        self.thinking_status = False

    def handle_response(
        self,
        response: Dict[str, Any],
        model: str,
        stream: bool = False,
        finish_reason: str = None,
        usage_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if stream:
            return _handle_openai_stream_response(response, model, finish_reason, usage_metadata)
        return _handle_openai_normal_response(response, model, finish_reason, usage_metadata)

    def handle_image_chat_response(
        self, image_str: str, model: str, stream=False, finish_reason="stop"
    ):
        if stream:
            return _handle_openai_stream_image_response(image_str, model, finish_reason)
        return _handle_openai_normal_image_response(image_str, model, finish_reason)


def _handle_openai_stream_image_response(
    image_str: str, model: str, finish_reason: str
) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": image_str} if image_str else {},
                "finish_reason": finish_reason,
            }
        ],
    }


def _handle_openai_normal_image_response(
    image_str: str, model: str, finish_reason: str
) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": image_str},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _extract_result(
    response: Dict[str, Any],
    model: str,
    stream: bool = False,
    gemini_format: bool = False,
) -> tuple[str, Optional[str], List[Dict[str, Any]], Optional[bool]]:
    text, reasoning_content, tool_calls, thought = "", "", [], None
    if stream:
        if response.get("candidates"):
            candidate = response["candidates"][0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            if not parts:
                return "", None, [], None
            if "text" in parts[0]:
                text = parts[0].get("text")
                if "thought" in parts[0]:
                    if not gemini_format and settings.SHOW_THINKING_PROCESS:
                        reasoning_content = text
                        text = ""
                    thought = parts[0].get("thought")
            elif "executableCode" in parts[0]:
                text = _format_code_block(parts[0]["executableCode"])
            elif "codeExecution" in parts[0]:
                text = _format_code_block(parts[0]["codeExecution"])
            elif "executableCodeResult" in parts[0]:
                text = _format_execution_result(parts[0]["executableCodeResult"])
            elif "codeExecutionResult" in parts[0]:
                text = _format_execution_result(parts[0]["codeExecutionResult"])
            elif "inlineData" in parts[0]:
                text = _extract_image_data(parts[0])
            else:
                text = ""
            text = _add_search_link_text(model, candidate, text)
            tool_calls = _extract_tool_calls(parts, gemini_format)
    else:
        if response.get("candidates"):
            candidate = response["candidates"][0]
            text, reasoning_content = "", ""
            if "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        if "thought" in part and settings.SHOW_THINKING_PROCESS:
                            reasoning_content += part["text"]
                        else:
                            text += part["text"]
                        if "thought" in part and thought is None:
                            thought = part.get("thought")
                    elif "inlineData" in part:
                        text += _extract_image_data(part)

            text = _add_search_link_text(model, candidate, text)
            tool_calls = _extract_tool_calls(
                candidate["content"]["parts"], gemini_format
            )
        else:
            text = "暂无返回"
    return text, reasoning_content, tool_calls, thought


def _extract_image_data(part: dict) -> str:
    image_uploader = None
    if settings.UPLOAD_PROVIDER == "smms":
        image_uploader = ImageUploaderFactory.create(
            provider=settings.UPLOAD_PROVIDER, api_key=settings.SMMS_SECRET_TOKEN
        )
    elif settings.UPLOAD_PROVIDER == "picgo":
        image_uploader = ImageUploaderFactory.create(
            provider=settings.UPLOAD_PROVIDER, api_key=settings.PICGO_API_KEY
        )
    elif settings.UPLOAD_PROVIDER == "cloudflare_imgbed":
        image_uploader = ImageUploaderFactory.create(
            provider=settings.UPLOAD_PROVIDER,
            base_url=settings.CLOUDFLARE_IMGBED_URL,
            auth_code=settings.CLOUDFLARE_IMGBED_AUTH_CODE,
            upload_folder=settings.CLOUDFLARE_IMGBED_UPLOAD_FOLDER,
        )
    current_date = time.strftime("%Y/%m/%d")
    filename = f"{current_date}/{uuid.uuid4().hex[:8]}.png"
    base64_data = part["inlineData"]["data"]
    # 将base64_data转成bytes数组
    bytes_data = base64.b64decode(base64_data)
    upload_response = image_uploader.upload(bytes_data, filename)
    if upload_response.success:
        text = f"\n\n![image]({upload_response.data.url})\n\n"
    else:
        text = ""
    return text


def _extract_tool_calls(
    parts: List[Dict[str, Any]], gemini_format: bool
) -> List[Dict[str, Any]]:
    """提取工具调用信息"""
    if not parts or not isinstance(parts, list):
        return []

    letters = string.ascii_lowercase + string.digits

    tool_calls = list()
    for i in range(len(parts)):
        part = parts[i]
        if not part or not isinstance(part, dict):
            continue

        item = part.get("functionCall", {})
        if not item or not isinstance(item, dict):
            continue

        if gemini_format:
            tool_calls.append(part)
        else:
            id = f"call_{''.join(random.sample(letters, 32))}"
            name = item.get("name", "")
            arguments = json.dumps(item.get("args", None) or {})

            tool_calls.append(
                {
                    "index": i,
                    "id": id,
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
            )

    return tool_calls


def _handle_gemini_stream_response(
    response: Dict[str, Any], model: str, stream: bool
) -> Dict[str, Any]:
    text, reasoning_content, tool_calls, thought = _extract_result(
        response, model, stream=stream, gemini_format=True
    )
    if tool_calls:
        content = {"parts": tool_calls, "role": "model"}
    else:
        part = {"text": text}
        if thought is not None:
            part["thought"] = thought
        content = {"parts": [part], "role": "model"}
    response["candidates"][0]["content"] = content
    return response


def _handle_gemini_normal_response(
    response: Dict[str, Any], model: str, stream: bool
) -> Dict[str, Any]:
    text, reasoning_content, tool_calls, thought = _extract_result(
        response, model, stream=stream, gemini_format=True
    )
    parts = []
    if tool_calls:
        parts = tool_calls
    else:
        if thought is not None:
            parts.append({"text": reasoning_content,"thought": thought})
        part = {"text": text}
        parts.append(part)
    content = {"parts": parts, "role": "model"}
    response["candidates"][0]["content"] = content
    return response


def _format_code_block(code_data: dict) -> str:
    """格式化代码块输出"""
    language = code_data.get("language", "").lower()
    code = code_data.get("code", "").strip()
    return f"""\n\n---\n\n【代码执行】\n```{language}\n{code}\n```\n"""


def _add_search_link_text(model: str, candidate: dict, text: str) -> str:
    if (
        settings.SHOW_SEARCH_LINK
        and model.endswith("-search")
        and "groundingMetadata" in candidate
        and "groundingChunks" in candidate["groundingMetadata"]
    ):
        grounding_chunks = candidate["groundingMetadata"]["groundingChunks"]
        text += "\n\n---\n\n"
        text += "**【引用来源】**\n\n"
        for _, grounding_chunk in enumerate(grounding_chunks, 1):
            if "web" in grounding_chunk:
                text += _create_search_link(grounding_chunk["web"])
        return text
    else:
        return text


def _create_search_link(grounding_chunk: dict) -> str:
    return f'\n- [{grounding_chunk["title"]}]({grounding_chunk["uri"]})'


def _format_execution_result(result_data: dict) -> str:
    """格式化执行结果输出"""
    outcome = result_data.get("outcome", "")
    output = result_data.get("output", "").strip()
    return f"""\n【执行结果】\n> outcome: {outcome}\n\n【输出结果】\n```plaintext\n{output}\n```\n\n---\n\n"""
