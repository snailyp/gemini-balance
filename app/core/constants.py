"""
常量定义模块
"""

# API相关常量
API_VERSION = "v1beta"
DEFAULT_TIMEOUT = 300  # 秒
MAX_RETRIES = 3  # 最大重试次数

# 模型相关常量
SUPPORTED_ROLES = ["user", "model", "system"]
DEFAULT_MODEL = "gemini-1.5-flash"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TOP_P = 0.9
DEFAULT_TOP_K = 40
DEFAULT_FILTER_MODELS = [
        "gemini-1.0-pro-vision-latest", 
        "gemini-pro-vision", 
        "chat-bison-001", 
        "text-bison-001", 
        "embedding-gecko-001"
    ]
DEFAULT_CREATE_IMAGE_MODEL = "imagen-3.0-generate-002"

# 图像生成相关常量
VALID_IMAGE_RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9"]

# 上传提供商
UPLOAD_PROVIDERS = ["smms", "picgo", "cloudflare_imgbed", "s3"]
DEFAULT_UPLOAD_PROVIDER = "smms"

# 流式输出相关常量
DEFAULT_STREAM_MIN_DELAY = 0.016
DEFAULT_STREAM_MAX_DELAY = 0.024
DEFAULT_STREAM_SHORT_TEXT_THRESHOLD = 10
DEFAULT_STREAM_LONG_TEXT_THRESHOLD = 50
DEFAULT_STREAM_CHUNK_SIZE = 5

# 正则表达式模式
IMAGE_URL_PATTERN = r'!\[(.*?)\]\((.*?)\)'
DATA_URL_PATTERN = r'data:([^;]+);base64,(.+)'
