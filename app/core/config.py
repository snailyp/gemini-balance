from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class APIKeyConfig(BaseModel):
    key: str
    base_url: Optional[str] = "https://api.openai.com/v1"


class Settings(BaseSettings):
    API_KEYS: List[Dict[str, str]]  # 支持包含代理地址的API密钥配置
    ALLOWED_TOKENS: List[str]
    AUTH_TOKEN: str = ""
    AVAILABLE_MODELS: List[str] = [
        "gpt-4-turbo-preview",
        "gpt-4",
        "gpt-3.5-turbo",
        "text-embedding-3-small"
    ]
    api_key_configs: List[APIKeyConfig] = Field(default_factory=list)  # 添加字段定义

    def __init__(self):
        super().__init__()
        if not self.AUTH_TOKEN:
            self.AUTH_TOKEN = self.ALLOWED_TOKENS[0] if self.ALLOWED_TOKENS else ""
        
        # 转换API密钥配置
        for key_config in self.API_KEYS:
            if isinstance(key_config, str):
                # 如果是字符串，使用默认base_url
                self.api_key_configs.append(APIKeyConfig(key=key_config))
            elif isinstance(key_config, dict):
                # 如果是字典，包含key和base_url
                self.api_key_configs.append(APIKeyConfig(**key_config))

    class Config:
        env_file = ".env"


settings = Settings()
