import pytest
from unittest.mock import AsyncMock, MagicMock
import itertools
import logging
import re
import ast # For literal_eval
import os # Import os to set environment variables

# Read .env file content
env_content = """
# 数据库配置
DATABASE_TYPE=mysql
# SQLITE_DATABASE=default_db
MYSQL_HOST=mysql
# MYSQL_SOCKET=/run/mysqld/mysqld.sock
MYSQL_PORT=3306
MYSQL_USER=mysql_user
MYSQL_PASSWORD=mysql_password
MYSQL_DATABASE=mysql_database
API_KEYS=["AIzaSyAaQ4dA0TH6Ua2TuoiCf2xf7pobn5ZFekY","AIzaSyBPXOlsXdFdBKrPstTSgzpw9MnyFyUwZic"]

ALLOWED_TOKENS=["sk-Tkxzv6cgf8fDUq0UyTV78hQ8V5VuJ0fExIOuaOmEfrO07ELk"]
AUTH_TOKEN=sk-123456
# For Vertex AI Platform API Keys
VERTEX_API_KEYS=["AQ.Abxxxxxxxxxxxxxxxxxxx"]
# For Vertex AI Platform Express API Base URL
VERTEX_EXPRESS_BASE_URL=["https://aiplatform.googleapis.com/v1beta1/publishers/google"]
TEST_MODEL=gemini-1.5-flash
THINKING_MODELS=["gemini-2.5-pro","gemini-2.5-flash-preview-04-17"]
THINKING_BUDGET_MAP={"gemini-2.5-flash-preview-05-20": 50000}
IMAGE_MODELS=["gemini-2.-flash-exp"]
SEARCH_MODELS=["gemini-2.0-flash-exp","gemini-2.0-pro-exp"]
FILTERED_MODELS=["gemini-1.0-pro-vision-latest", "gemini-pro-vision", "chat-bison-001", "text-bison-001", "embedding-gecko-001"]
TOOLS_CODE_EXECUTION_ENABLED=false
SHOW_SEARCH_LINK=true
SHOW_THINKING_PROCESS=true
BASE_URL=["https://gateway.ai.cloudflare.com/v1/41bb81bef4b46b525314529224d1657b/gemini-balance/google-ai-studio/v1beta"]
GEMINI_BASE_URL=["https://gateway.ai.cloudflare.com/v1/41bb81bef4b46b525314529224d1657b/gemini-balance/google-ai-studio/v1beta"]
MAX_FAILURES=10
MAX_RETRIES=3
CHECK_INTERVAL_HOURS=1
TIMEZONE=Asia/Shanghai
# 请求超时时间（秒）
TIME_OUT=300
# 代理服务器配置 (支持 http 和 socks5)
# 示例: PROXIES=["http://user:pass@host:port", "socks5://host:port"]
PROXIES=[]
# 对同一个API_KEY使用代理列表中固定的IP策略
PROXIES_USE_CONSISTENCY_HASH_BY_API_KEY=true
#########################image_generate 相关配置###########################
PAID_KEY=AIzaSyxxxxxxxxxxxxxxxxxxx
CREATE_IMAGE_MODEL=imagen-3.0-generate-002
UPLOAD_PROVIDER=smms
SMMS_SECRET_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
PICGO_API_KEY=xxxx
CLOUDFLARE_IMGBED_URL=https://xxxxxxx.pages.dev/upload
CLOUDFLARE_IMGBED_AUTH_CODE=xxxxxxxxx
##########################################################################
#########################stream_optimizer 相关配置########################
STREAM_OPTIMIZER_ENABLED=false
STREAM_MIN_DELAY=0.016
STREAM_MAX_DELAY=0.024
STREAM_SHORT_TEXT_THRESHOLD=10
STREAM_LONG_TEXT_THRESHOLD=50
STREAM_CHUNK_SIZE=5
##########################################################################
######################### 日志配置 #######################################
# 日志级别 (debug, info, warning, error, critical)，默认为 info
LOG_LEVEL=info
# 是否开启自动删除错误日志
AUTO_DELETE_ERROR_LOGS_ENABLED=true
# 自动删除多少天前的错误日志 (1, 7, 30)
AUTO_DELETE_ERROR_LOGS_DAYS=7
# 是否开启自动删除请求日志
AUTO_DELETE_REQUEST_LOGS_ENABLED=false
# 自动删除多少天前的请求日志 (1, 7, 30)
AUTO_DELETE_REQUEST_LOGS_DAYS=30
##########################################################################

# 假流式配置 (Fake Streaming Configuration)
# 是否启用假流式输出
FAKE_STREAM_ENABLED=True
# 假流式发送空数据的间隔时间（秒）
FAKE_STREAM_EMPTY_DATA_INTERVAL_SECONDS=5

# 安全设置 (JSON 字符串格式)
# 注意：这里的示例值可能需要根据实际模型支持情况调整
SAFETY_SETTINGS=[{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"}, {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}]
"""

def parse_env_content(content):
    parsed_data = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            # Attempt to parse lists and other Python literals
            if value.startswith('[') and value.endswith(']'):
                try:
                    parsed_data[key] = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    parsed_data[key] = value
            elif value.startswith('{') and value.endswith('}'):
                try:
                    parsed_data[key] = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    parsed_data[key] = value
            else:
                parsed_data[key] = value
    return parsed_data

env_vars = parse_env_content(env_content)

# Set environment variables before importing any app modules
for key, value in env_vars.items():
    # Convert lists/dicts back to string representation for environment variables
    if isinstance(value, (list, dict)):
        os.environ[key] = str(value)
    else:
        os.environ[key] = value

# Now import the modules that depend on settings
from app.service.key.key_manager import KeyManager
from app.handler.retry_handler import RetryHandler
from app.exception.exceptions import ServiceUnavailableError
from app.config.config import settings # Import the actual settings object after env vars are set


@pytest.fixture
def mock_api_key_service():
    service = AsyncMock()
    service.get_all_keys.return_value = []
    service.mark_key_as_limited.return_value = None
    service.reset_key_status_to_active.return_value = None
    service.is_key_active.return_value = True
    service.mark_key_as_banned.return_value = None # Add mock for mark_key_as_banned
    return service

@pytest.fixture
async def key_manager_instance(mock_api_key_service):
    km = KeyManager()
    km.api_keys = ["key1", "key2", "key3"]
    km.key_failure_counts = {"key1": 0, "key2": 0, "key3": 0}
    km.key_cycle = itertools.cycle(km.api_keys)
    km.MAX_FAILURES = settings.MAX_FAILURES # Use actual settings value
    km.GEMINI_RPM_LIMIT = settings.GEMINI_RPM_LIMIT # Use actual settings value
    km.api_key_service = mock_api_key_service # Assign the mocked service
    yield km

class TestKeyManager:
    @pytest.mark.asyncio
    async def test_handle_api_failure_increments_count(self, key_manager_instance):
        km = key_manager_instance
        initial_failure_count = km.key_failure_counts["key1"]
        
        result = await km.handle_api_failure("key1", status_code=500)
        
        assert km.key_failure_counts["key1"] == initial_failure_count + 1
        assert result == "key1" # Key should still be returned as it's not limited yet

    @pytest.mark.asyncio
    async def test_handle_api_failure_marks_key_limited_and_returns_new_key(self, key_manager_instance, mock_api_key_service):
        km = key_manager_instance
        km.key_failure_counts["key1"] = km.MAX_FAILURES - 1 # One failure away from limit
        
        # Mock get_next_working_key to return a new key
        km.get_next_working_key = AsyncMock(return_value="key2")

        result = await km.handle_api_failure("key1", status_code=500)
        
        assert km.key_failure_counts["key1"] == km.MAX_FAILURES
        mock_api_key_service.mark_key_as_limited.assert_called_with("key1")
        assert "key1" not in km.api_keys # Should be removed from active keys
        assert result == "key2" # Should return the next working key

    @pytest.mark.asyncio
    async def test_handle_api_failure_returns_none_if_no_new_key(self):
        km = key_manager_instance
        km.key_failure_counts["key1"] = km.MAX_FAILURES - 1 # One failure away from limit
        
        # Mock get_next_working_key to raise ServiceUnavailableError
        km.get_next_working_key = AsyncMock(side_effect=ServiceUnavailableError("No active keys"))

        result = await km.handle_api_failure("key1", status_code=500)
        
        assert km.key_failure_counts["key1"] == km.MAX_FAILURES
        mock_api_key_service.mark_key_as_limited.assert_called_with("key1")
        assert "key1" not in km.api_keys
        assert result is None # Should return None

    @pytest.mark.asyncio
    async def test_handle_api_failure_with_403_status_code(self):
        km = key_manager_instance
        initial_failure_count = km.key_failure_counts["key1"]
        
        result = await km.handle_api_failure("key1", status_code=403)
        
        # Failure count should not increment for 403
        assert km.key_failure_counts["key1"] == initial_failure_count
        mock_api_key_service.mark_key_as_banned.assert_called_with("key1") # Should call mark_key_as_banned
        assert "key1" not in km.api_keys # Should be removed from active keys
        assert result is None # Should return None

class TestRetryHandler:
    @pytest.mark.asyncio
    async def test_retry_handler_switches_key_on_failure(self):
        handler = RetryHandler(key_arg="api_key")
        
        mock_func = AsyncMock(side_effect=[Exception("API error"), "Success"])
        mock_key_manager = AsyncMock()
        mock_key_manager.handle_api_failure.return_value = "new_key_value" # Simulate new key
        
        @handler
        async def test_api_call(api_key: str, key_manager: KeyManager):
            return await mock_func()

        result = await test_api_call(api_key="old_key_value", key_manager=mock_key_manager)
        
        mock_func.assert_called_with() # Should be called twice
        mock_key_manager.handle_api_failure.assert_called_once_with("old_key_value", status_code=None) # status_code is None by default
        assert result == "Success"

    @pytest.mark.asyncio
    async def test_retry_handler_raises_exception_after_max_retries(self):
        handler = RetryHandler(key_arg="api_key")
        
        mock_func = AsyncMock(side_effect=[Exception("API error")] * settings.MAX_RETRIES) # Use actual settings value
        mock_key_manager = AsyncMock()
        mock_key_manager.handle_api_failure.return_value = None # Simulate no new key available
        
        @handler
        async def test_api_call(api_key: str, key_manager: KeyManager):
            return await mock_func()

        with pytest.raises(Exception, match="API error"):
            await test_api_call(api_key="old_key_value", key_manager=mock_key_manager)
        
        assert mock_func.call_count == settings.MAX_RETRIES # Use actual settings value
        assert mock_key_manager.handle_api_failure.call_count == settings.MAX_RETRIES # Use actual settings value

    @pytest.mark.asyncio
    async def test_retry_handler_logs_new_key_correctly(self, caplog):
        handler = RetryHandler(key_arg="api_key")
        
        mock_func = AsyncMock(side_effect=[Exception("API error"), "Success"])
        mock_key_manager = AsyncMock()
        mock_key_manager.handle_api_failure.return_value = "AIzaSyCw28NOr-yVNiZ27yk9NRxncGcbUo75M5c" # Simulate new key
        
        @handler
        async def test_api_call(api_key: str, key_manager: KeyManager):
            return await mock_func()

        with caplog.at_level(logging.INFO):
            await test_api_call(api_key="old_key_value", key_manager=mock_key_manager)
            assert "Switched to new API key: 5M5c" in caplog.text
