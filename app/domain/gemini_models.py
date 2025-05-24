from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.core.constants import DEFAULT_TEMPERATURE, DEFAULT_TOP_K, DEFAULT_TOP_P


class SafetySetting(BaseModel):
    category: Optional[
        Literal[
            "HARM_CATEGORY_HATE_SPEECH",
            "HARM_CATEGORY_DANGEROUS_CONTENT",
            "HARM_CATEGORY_HARASSMENT",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "HARM_CATEGORY_CIVIC_INTEGRITY",
        ]
    ] = None
    threshold: Optional[
        Literal[
            "HARM_BLOCK_THRESHOLD_UNSPECIFIED",
            "BLOCK_LOW_AND_ABOVE",
            "BLOCK_MEDIUM_AND_ABOVE",
            "BLOCK_ONLY_HIGH",
            "BLOCK_NONE",
            "OFF",
        ]
    ] = None


class GenerationConfig(BaseModel):
    stopSequences: Optional[List[str]] = None
    responseMimeType: Optional[str] = None
    responseSchema: Optional[Dict[str, Any]] = None
    candidateCount: Optional[int] = 1
    maxOutputTokens: Optional[int] = None
    temperature: Optional[float] = DEFAULT_TEMPERATURE
    topP: Optional[float] = DEFAULT_TOP_P
    topK: Optional[int] = DEFAULT_TOP_K
    presencePenalty: Optional[float] = None
    frequencyPenalty: Optional[float] = None
    responseLogprobs: Optional[bool] = None
    logprobs: Optional[int] = None
    thinkingConfig: Optional[Dict[str, Any]] = None


class SystemInstruction(BaseModel):
    role: str = "system"
    parts: List[Dict[str, Any]] | Dict[str, Any]


class GeminiContent(BaseModel):
    role: str
    parts: List[Dict[str, Any]]


class GeminiRequest(BaseModel):
    contents: List[GeminiContent] = []
    tools: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = []
    safetySettings: Optional[List[SafetySetting]] = Field(
        default=None, alias="safety_settings"
    )
    generationConfig: Optional[GenerationConfig] = Field(
        default=None, alias="generation_config"
    )
    systemInstruction: Optional[SystemInstruction] = Field(
        default=None, alias="system_instruction"
    )

    class Config:
        populate_by_name = True


class ResetSelectedKeysRequest(BaseModel):
    keys: List[str]
    key_type: str


class VerifySelectedKeysRequest(BaseModel):
    keys: List[str]
