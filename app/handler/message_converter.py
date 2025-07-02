import base64
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import requests

from app.core.constants import (
    AUDIO_FORMAT_TO_MIMETYPE,
    DATA_URL_PATTERN,
    IMAGE_URL_PATTERN,
    MAX_AUDIO_SIZE_BYTES,
    MAX_VIDEO_SIZE_BYTES,
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_ROLES,
    SUPPORTED_VIDEO_FORMATS,
    VIDEO_FORMAT_TO_MIMETYPE,
)
from app.log.logger import get_message_converter_logger

logger = get_message_converter_logger()


class MessageConverter(ABC):
    """消息转换器基类"""

    @abstractmethod
    def convert(
        self, messages: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        pass


def _get_mime_type_and_data(base64_string):
    """
    从 base64 字符串中提取 MIME 类型和数据。

    参数:
        base64_string (str): 可能包含 MIME 类型信息的 base64 字符串

    返回:
        tuple: (mime_type, encoded_data)
    """
    # 检查字符串是否以 "data:" 格式开始
    if base64_string.startswith("data:"):
        # 提取 MIME 类型和数据
        pattern = DATA_URL_PATTERN
        match = re.match(pattern, base64_string)
        if match:
            mime_type = (
                "image/jpeg" if match.group(1) == "image/jpg" else match.group(1)
            )
            encoded_data = match.group(2)
            return mime_type, encoded_data

    # 如果不是预期格式，假定它只是数据部分
    return None, base64_string


def _convert_image(image_url: str) -> Dict[str, Any]:
    if image_url.startswith("data:image"):
        mime_type, encoded_data = _get_mime_type_and_data(image_url)
        return {"inline_data": {"mime_type": mime_type, "data": encoded_data}}
    else:
        encoded_data = _convert_image_to_base64(image_url)
        return {"inline_data": {"mime_type": "image/png", "data": encoded_data}}


def _convert_image_to_base64(url: str) -> str:
    """
    将图片URL转换为base64编码
    Args:
        url: 图片URL
    Returns:
        str: base64编码的图片数据
    """
    response = requests.get(url)
    if response.status_code == 200:
        # 将图片内容转换为base64
        img_data = base64.b64encode(response.content).decode("utf-8")
        return img_data
    else:
        raise Exception(f"Failed to fetch image: {response.status_code}")


def _process_text_with_image(text: str) -> List[Dict[str, Any]]:
    """
    处理可能包含图片URL的文本，提取图片并转换为base64

    Args:
        text: 可能包含图片URL的文本

    Returns:
        List[Dict[str, Any]]: 包含文本和图片的部分列表
    """
    parts = []
    img_url_match = re.search(IMAGE_URL_PATTERN, text)
    if img_url_match:
        # 提取URL
        img_url = img_url_match.group(2)
        # 将URL对应的图片转换为base64
        try:
            base64_data = _convert_image_to_base64(img_url)
            parts.append(
                {"inline_data": {"mimeType": "image/png", "data": base64_data}}
            )
        except Exception:
            # 如果转换失败，回退到文本模式
            parts.append({"text": text})
    else:
        # 没有图片URL，作为纯文本处理
        parts.append({"text": text})
    return parts


class OpenAIMessageConverter(MessageConverter):
    """OpenAI消息格式转换器"""

    def _validate_media_data(
        self, format: str, data: str, supported_formats: List[str], max_size: int
    ) -> tuple[Optional[str], Optional[str]]:
        """Validates format and size of Base64 media data."""
        if format.lower() not in supported_formats:
            logger.error(
                f"Unsupported media format: {format}. Supported: {supported_formats}"
            )
            raise ValueError(f"Unsupported media format: {format}")

        try:
            decoded_data = base64.b64decode(data, validate=True)
            if len(decoded_data) > max_size:
                logger.error(
                    f"Media data size ({len(decoded_data)} bytes) exceeds limit ({max_size} bytes)."
                )
                raise ValueError(
                    f"Media data size exceeds limit of {max_size // 1024 // 1024}MB"
                )
            return data
        except base64.binascii.Error as e:
            logger.error(f"Invalid Base64 data provided: {e}")
            raise ValueError("Invalid Base64 data")
        except Exception as e:
            logger.error(f"Error validating media data: {e}")
            raise

    def convert(
        self, messages: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        converted_messages = []
        system_instruction_parts = []

        for idx, msg in enumerate(messages):
            role = msg.get("role", "")
            parts = []

            if "content" in msg and isinstance(msg["content"], list):
                for content_item in msg["content"]:
                    if not isinstance(content_item, dict):
                        logger.warning(
                            f"Skipping unexpected content item format: {type(content_item)}"
                        )
                        continue

                    content_type = content_item.get("type")

                    if content_type == "text" and content_item.get("text"):
                        parts.append({"text": content_item["text"]})
                    elif content_type == "image_url" and content_item.get(
                        "image_url", {}
                    ).get("url"):
                        try:
                            parts.append(
                                _convert_image(content_item["image_url"]["url"])
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to convert image URL {content_item['image_url']['url']}: {e}"
                            )
                            parts.append(
                                {
                                    "text": f"[Error processing image: {content_item['image_url']['url']}]"
                                }
                            )
                    elif content_type == "input_audio" and content_item.get(
                        "input_audio"
                    ):
                        audio_info = content_item["input_audio"]
                        audio_data = audio_info.get("data")
                        audio_format = audio_info.get("format", "").lower()

                        if not audio_data or not audio_format:
                            logger.warning(
                                "Skipping audio part due to missing data or format."
                            )
                            continue

                        try:
                            validated_data = self._validate_media_data(
                                audio_format,
                                audio_data,
                                SUPPORTED_AUDIO_FORMATS,
                                MAX_AUDIO_SIZE_BYTES,
                            )

                            # Get MIME type
                            mime_type = AUDIO_FORMAT_TO_MIMETYPE.get(audio_format)
                            if not mime_type:
                                # Should not happen if format validation passed, but double-check
                                logger.error(
                                    f"Could not find MIME type for supported format: {audio_format}"
                                )
                                raise ValueError(
                                    f"Internal error: MIME type mapping missing for {audio_format}"
                                )

                            parts.append(
                                {
                                    "inline_data": {
                                        "mimeType": mime_type,
                                        "data": validated_data,  # Use the validated Base64 data
                                    }
                                }
                            )
                            logger.debug(
                                f"Successfully added audio part (format: {audio_format})"
                            )

                        except ValueError as e:
                            logger.error(
                                f"Skipping audio part due to validation error: {e}"
                            )
                            parts.append({"text": f"[Error processing audio: {e}]"})
                        except Exception:
                            logger.exception("Unexpected error processing audio part.")
                            parts.append(
                                {"text": "[Unexpected error processing audio]"}
                            )

                    elif content_type == "input_video" and content_item.get(
                        "input_video"
                    ):
                        video_info = content_item["input_video"]
                        video_data = video_info.get("data")
                        video_format = video_info.get("format", "").lower()

                        if not video_data or not video_format:
                            logger.warning(
                                "Skipping video part due to missing data or format."
                            )
                            continue

                        try:
                            validated_data = self._validate_media_data(
                                video_format,
                                video_data,
                                SUPPORTED_VIDEO_FORMATS,
                                MAX_VIDEO_SIZE_BYTES,
                            )
                            mime_type = VIDEO_FORMAT_TO_MIMETYPE.get(video_format)
                            if not mime_type:
                                raise ValueError(
                                    f"Internal error: MIME type mapping missing for {video_format}"
                                )

                            parts.append(
                                {
                                    "inline_data": {
                                        "mimeType": mime_type,
                                        "data": validated_data,
                                    }
                                }
                            )
                            logger.debug(
                                f"Successfully added video part (format: {video_format})"
                            )

                        except ValueError as e:
                            logger.error(
                                f"Skipping video part due to validation error: {e}"
                            )
                            parts.append({"text": f"[Error processing video: {e}]"})
                        except Exception:
                            logger.exception("Unexpected error processing video part.")
                            parts.append(
                                {"text": "[Unexpected error processing video]"}
                            )

                    else:
                        # Log unrecognized but present types
                        if content_type:
                            logger.warning(
                                f"Unsupported content type or missing data in structured content: {content_type}"
                            )

            elif (
                "content" in msg and isinstance(msg["content"], str) and msg["content"]
            ):
                parts.extend(_process_text_with_image(msg["content"]))
            elif "tool_calls" in msg and isinstance(msg["tool_calls"], list):
                # Keep existing tool call processing
                for tool_call in msg["tool_calls"]:
                    function_call = tool_call.get("function", {})
                    # Sanitize arguments loading
                    arguments_str = function_call.get("arguments", "{}")
                    try:
                        function_call["args"] = json.loads(arguments_str)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to decode tool call arguments: {arguments_str}"
                        )
                        function_call["args"] = {}
                    if "arguments" in function_call:
                        if "arguments" in function_call:
                            del function_call["arguments"]

                    parts.append({"functionCall": function_call})

            if role not in SUPPORTED_ROLES:
                if role == "tool":
                    role = "user"
                else:
                    # 如果是最后一条消息，则认为是用户消息
                    if idx == len(messages) - 1:
                        role = "user"
                    else:
                        role = "model"
            if parts:
                if role == "system":
                    text_only_parts = [p for p in parts if "text" in p]
                    if len(text_only_parts) != len(parts):
                        logger.warning(
                            "Non-text parts found in system message; discarding them."
                        )
                    if text_only_parts:
                        system_instruction_parts.extend(text_only_parts)

                else:
                    converted_messages.append({"role": role, "parts": parts})

        system_instruction = (
            None
            if not system_instruction_parts
            else {
                "role": "system",
                "parts": system_instruction_parts,
            }
        )

        # If there are system instructions but no other messages, add a user message with a placeholder text
        # This is a workaround for APIs that require 'contents' to be non-empty and parts must not be empty
        if not converted_messages and system_instruction:
            converted_messages.append({"role": "user", "parts": [{"text": " "}]})

        return converted_messages, system_instruction
