from pydantic_settings import BaseSettings
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field, field_validator
import json
import logging

logger = logging.getLogger(__name__)

class APIKeyConfig(BaseModel):
    key: str

class Settings(BaseSettings):
    API_KEYS: List[Union[Dict[str, str], str]] = []
    ALLOWED_TOKENS: List[str] = []
    AUTH_TOKEN: str = ""
    BASE_URL: str = "https://api.openai.com/v1"
    AVAILABLE_MODELS: List[str] = [
        "gpt-4-turbo-preview",
        "gpt-4",
        "gpt-3.5-turbo",
        "text-embedding-3-small"
    ]
    api_key_configs: List[APIKeyConfig] = Field(default_factory=list)

    @field_validator("API_KEYS", "ALLOWED_TOKENS", "AVAILABLE_MODELS", mode="before")
    @classmethod
    def validate_json_string(cls, v):
        if isinstance(v, str):
            try:
                # 移除可能的多余空白字符
                v = v.strip()
                if not v:
                    return []
                return json.loads(v)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {str(e)}, 值: {v}")
                return []
        return v

    def __init__(self):
        try:
            super().__init__()
            if not self.AUTH_TOKEN:
                self.AUTH_TOKEN = self.ALLOWED_TOKENS[0] if self.ALLOWED_TOKENS else ""
            
            # 转换API密钥配置
            for key_config in self.API_KEYS:
                try:
                    if isinstance(key_config, str):
                        # 如果是字符串，只使用key
                        self.api_key_configs.append(APIKeyConfig(key=key_config))
                    elif isinstance(key_config, dict):
                        # 如果是字典，只使用key
                        self.api_key_configs.append(APIKeyConfig(key=key_config["key"]))
                except Exception as e:
                    logger.error(f"处理API密钥配置时出错: {str(e)}")
                    continue
            
            if not self.api_key_configs:
                logger.warning("没有有效的API密钥配置")
        except Exception as e:
            logger.error(f"初始化设置时出错: {str(e)}")
            raise

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False  # 环境变量名不区分大小写


settings = Settings()
