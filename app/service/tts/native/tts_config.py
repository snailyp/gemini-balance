"""
TTS扩展配置
控制是否启用TTS功能
"""

import os
from typing import Union
from app.service.chat.gemini_chat_service import GeminiChatService
from app.service.tts.native.tts_chat_service import TTSGeminiChatService


class TTSConfig:
    """TTS配置管理"""
    
    @staticmethod
    def is_tts_enabled() -> bool:
        """
        检查是否启用TTS功能
        通过环境变量 ENABLE_TTS 控制，默认为 False
        """
        return os.getenv("ENABLE_TTS", "false").lower() in ("true", "1", "yes", "on")
    
    @staticmethod
    def get_chat_service(base_url: str, key_manager) -> Union[GeminiChatService, TTSGeminiChatService]:
        """
        工厂方法：根据配置返回合适的聊天服务
        """
        if TTSConfig.is_tts_enabled():
            return TTSGeminiChatService(base_url, key_manager)
        else:
            return GeminiChatService(base_url, key_manager)


# 便捷函数
def create_chat_service(base_url: str, key_manager) -> Union[GeminiChatService, TTSGeminiChatService]:
    """创建聊天服务实例"""
    return TTSConfig.get_chat_service(base_url, key_manager)
