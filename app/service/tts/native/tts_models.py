"""
原生Gemini TTS扩展数据模型
继承自原始模型，添加原生Gemini TTS相关字段，保持向后兼容
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.domain.gemini_models import GenerationConfig as BaseGenerationConfig


class TTSGenerationConfig(BaseGenerationConfig):
    """
    支持TTS的生成配置类
    继承自原始的GenerationConfig，添加TTS相关字段
    """
    # TTS 相关配置
    responseModalities: Optional[List[str]] = None
    speechConfig: Optional[Dict[str, Any]] = None


class MultiSpeakerVoiceConfig(BaseModel):
    """多人语音配置"""
    speakerVoiceConfigs: List[Dict[str, Any]]


class SpeechConfig(BaseModel):
    """语音配置"""
    multiSpeakerVoiceConfig: Optional[MultiSpeakerVoiceConfig] = None
    voiceConfig: Optional[Dict[str, Any]] = None


class TTSRequest(BaseModel):
    """TTS请求模型"""
    contents: List[Dict[str, Any]]
    generationConfig: TTSGenerationConfig
