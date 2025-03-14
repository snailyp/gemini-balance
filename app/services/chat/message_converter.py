# app/services/chat/message_converter.py

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

SUPPORTED_ROLES = ["user", "model", "system"]


class MessageConverter(ABC):
    """消息转换器基类"""

    @abstractmethod
    def convert(self, messages: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        pass


def _convert_image(image_url: str) -> Dict[str, Any]:
    if image_url.startswith("data:image"):
        return {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image_url.split(",")[1]
            }
        }
    return {
        "image_url": {
            "url": image_url
        }
    }


class OpenAIMessageConverter(MessageConverter):
    """OpenAI消息格式转换器"""

    def convert(self, messages: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        converted_messages = []
        system_instruction_parts = []

        for idx, msg in enumerate(messages):
            role = msg.get("role", "")
            if role not in SUPPORTED_ROLES:
                if role == "tool":
                    role = "user"
                else:
                    # 如果是最后一条消息，则认为是用户消息
                    if idx == len(messages) - 1:
                        role = "user"
                    else:
                        role = "model"

            parts = []

            if role == "assistant" and "tool_calls" in msg:
                role = "model" 
                for tool_call in msg["tool_calls"]:
                    if tool_call["type"] == "function":
                        function_name = tool_call["function"]["name"]
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except:
                            arguments = tool_call["function"]["arguments"]
                        
                        parts.append({
                            "functionCall": {
                                "name": function_name,
                                "args": arguments
                            }
                        })
                        
            elif role == "tool" and "content" in msg and "tool_call_id" in msg:
                role = "user"
                tool_response_content = msg["content"]
                try:
                    if isinstance(tool_response_content, str):
                        tool_response_data = json.loads(tool_response_content)
                    else:
                        tool_response_data = tool_response_content
                except:
                    tool_response_data = tool_response_content

                function_name = ""
                for prev_msg in messages:
                    if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
                        for tool_call in prev_msg["tool_calls"]:
                            if tool_call.get("id") == msg["tool_call_id"]:
                                function_name = tool_call["function"]["name"]
                                break
                
                parts.append({
                    "functionResponse": {
                        "name": function_name,
                        "response": {
                            "name": function_name,
                            "content": tool_response_data
                        }
                    }
                })

            elif "content" in msg:
                if isinstance(msg["content"], str) and msg["content"]:
                    parts.append({"text": msg["content"]})
                elif isinstance(msg["content"], list):
                    for content in msg["content"]:
                        if isinstance(content, str) and content:
                            parts.append({"text": content})
                        elif isinstance(content, dict):
                            if content["type"] == "text" and content["text"]:
                                parts.append({"text": content["text"]})
                            elif content["type"] == "image_url":
                                parts.append(_convert_image(content["image_url"]["url"]))

            if parts:
                if role == "system":
                    system_instruction_parts.extend(parts)
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
        return converted_messages, system_instruction
