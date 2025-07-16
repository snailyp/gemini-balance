import datetime
import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, Union

from app.domain.claude_models import ClaudeChatRequest
from app.domain.gemini_models import GenerationConfig, GeminiRequest
from app.handler.message_converter import ClaudeMessageConverter
from app.log.logger import get_claude_compatible_logger
from app.service.chat.gemini_chat_service import GeminiChatService

logger = get_claude_compatible_logger()


def _convert_gemini_response_to_claude(
    gemini_response: Dict[str, Any], model: str
) -> Dict[str, Any]:
    """将单个Gemini响应转换为Claude格式。"""
    request_id = f"req_{uuid.uuid4()}"

    text_content = ""
    # 提取文本内容
    if gemini_response.get("candidates"):
        candidate = gemini_response["candidates"][0]
        if candidate.get("content", {}).get("parts"):
            text_content = candidate["content"]["parts"][0].get("text", "")

    # 映射停止原因
    stop_reason_map = {
        "STOP": "end_turn",
        "MAX_TOKENS": "max_tokens",
        "SAFETY": "stop_sequence",  # Claude没有完全对应的安全停止原因，使用stop_sequence
        "RECITATION": "stop_sequence",
        "OTHER": "stop_sequence",
    }
    gemini_finish_reason = gemini_response.get("candidates", [{}])[0].get(
        "finishReason", "OTHER"
    )
    claude_stop_reason = stop_reason_map.get(gemini_finish_reason, "stop_sequence")

    # 提取使用量
    input_tokens = gemini_response.get("usageMetadata", {}).get("promptTokenCount", 0)
    output_tokens = gemini_response.get("usageMetadata", {}).get(
        "candidatesTokenCount", 0
    )

    return {
        "id": request_id,
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": text_content}],
        "model": model,
        "stop_reason": claude_stop_reason,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


async def _convert_gemini_stream_to_claude(
    gemini_stream: AsyncGenerator[str, None], model: str
) -> AsyncGenerator[str, None]:
    """将Gemini流式响应转换为Claude流式格式。"""
    request_id = f"req_{uuid.uuid4()}"

    # 1. 发送 message_start 事件
    yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': request_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': model, 'stop_reason': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"

    full_text = ""
    async for line in gemini_stream:
        if not line.strip():
            continue
        if line.startswith("data:"):
            try:
                data_str = line[5:].strip()
                gemini_chunk = json.loads(data_str)

                if gemini_chunk.get("candidates"):
                    candidate = gemini_chunk["candidates"][0]
                    if candidate.get("content", {}).get("parts"):
                        text_chunk = candidate["content"]["parts"][0].get("text", "")
                        if text_chunk:
                            full_text += text_chunk
                            # 2. 发送 content_block_delta
                            delta_event = {
                                "type": "content_block_delta",
                                "index": 0,
                                "delta": {"type": "text_delta", "text": text_chunk},
                            }
                            yield f"event: content_block_delta\ndata: {json.dumps(delta_event)}\n\n"
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode stream chunk: {line}")
                continue

    # 3. 发送 message_stop
    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"


class ClaudeCompatibleService:
    def __init__(self, gemini_chat_service: GeminiChatService):
        self.gemini_chat_service = gemini_chat_service
        self.message_converter = ClaudeMessageConverter()

    async def create_chat_completion(
        self,
        request: ClaudeChatRequest,
        api_key: str,
    ) -> Union[Dict[str, Any], AsyncGenerator[str, None]]:
        """
        接收Claude格式的请求，转换为Gemini格式，调用Gemini服务，然后将结果转换回Claude格式。
        """
        # 1. 将Claude请求转换为Gemini格式
        gemini_contents, gemini_system_instruction = self.message_converter.convert(
            request.messages, request.system
        )

        # 2. 构建GeminiRequest
        generation_config = GenerationConfig(
            temperature=request.temperature,
            topP=request.top_p,
            topK=request.top_k,
            maxOutputTokens=request.max_tokens,
            stopSequences=request.stop_sequences,
        )

        gemini_request = GeminiRequest(
            contents=gemini_contents,
            systemInstruction=gemini_system_instruction,
            generationConfig=generation_config,
        )

        # 3. 调用Gemini服务
        # ----------------------Claude Code请求抓包-----------------------------------------
        # contents=[GeminiContent(role='user', parts=[{'text': 'Please write a 5-10 word title the following conversation:\n\nUser: hi\n\nRespond with the title for the conversation and nothing else.'}])] tools=[] safetySettings=None generationConfig=GenerationConfig(stopSequences=None, responseMimeType=None, responseSchema=None, candidateCount=1, maxOutputTokens=512, temperature=0.0, topP=None, topK=None, presencePenalty=None, frequencyPenalty=None, responseLogprobs=None, logprobs=None, thinkingConfig=None, responseModalities=None, speechConfig=None) systemInstruction=SystemInstruction(role='system', parts=[{'text': [SystemContent(type='text', text='Summarize this coding conversation in under 50 characters.\nCapture the main task, key files, problems addressed, and current status.')]}])
        # ----------------------Claude Code抓包结束-----------------------------------------
        # 由于Claude Code未指定模型它的模型，无法做映射，这里强制使用 gemini-pro 模型
        gemini_model = "gemini-2.5-pro"

        if request.stream:
            gemini_stream = self.gemini_chat_service.stream_generate_content(
                model=gemini_model, request=gemini_request, api_key=api_key
            )
            # 4a. 将Gemini流转换为Claude流
            return _convert_gemini_stream_to_claude(gemini_stream, request.model)
        else:
            gemini_response = await self.gemini_chat_service.generate_content(
                model=gemini_model, request=gemini_request, api_key=api_key
            )
            # 4b. 将Gemini响应转换为Claude响应
            return _convert_gemini_response_to_claude(gemini_response, request.model)
