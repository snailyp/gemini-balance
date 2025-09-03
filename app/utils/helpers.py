"""
通用工具函数模块
"""

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.config.config import Settings
from app.core.constants import DATA_URL_PATTERN, IMAGE_URL_PATTERN, VALID_IMAGE_RATIOS

helper_logger = logging.getLogger("app.utils")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VERSION_FILE_PATH = PROJECT_ROOT / "VERSION"


def extract_mime_type_and_data(base64_string: str) -> Tuple[Optional[str], str]:
    """
    从 base64 字符串中提取 MIME 类型和数据

    Args:
        base64_string: 可能包含 MIME 类型信息的 base64 字符串

    Returns:
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


def convert_image_to_base64(url: str) -> str:
    """
    将图片URL转换为base64编码

    Args:
        url: 图片URL

    Returns:
        str: base64编码的图片数据

    Raises:
        Exception: 如果获取图片失败
    """
    response = requests.get(url)
    if response.status_code == 200:
        # 将图片内容转换为base64
        img_data = base64.b64encode(response.content).decode("utf-8")
        return img_data
    else:
        raise Exception(f"Failed to fetch image: {response.status_code}")


def format_json_response(data: Dict[str, Any], indent: int = 2) -> str:
    """
    格式化JSON响应

    Args:
        data: 要格式化的数据
        indent: 缩进空格数

    Returns:
        str: 格式化后的JSON字符串
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


def parse_prompt_parameters(
    prompt: str, default_ratio: str = "1:1"
) -> Tuple[str, int, str]:
    """
    从prompt中解析参数

    支持的格式:
    - {n:数量} 例如: {n:2} 生成2张图片
    - {ratio:比例} 例如: {ratio:16:9} 使用16:9比例

    Args:
        prompt: 提示文本
        default_ratio: 默认比例

    Returns:
        tuple: (清理后的提示文本, 图片数量, 比例)
    """
    # 默认值
    n = 1
    aspect_ratio = default_ratio

    # 解析n参数
    n_match = re.search(r"{n:(\d+)}", prompt)
    if n_match:
        n = int(n_match.group(1))
        if n < 1 or n > 4:
            raise ValueError(f"Invalid n value: {n}. Must be between 1 and 4.")
        prompt = prompt.replace(n_match.group(0), "").strip()

    # 解析ratio参数
    ratio_match = re.search(r"{ratio:(\d+:\d+)}", prompt)
    if ratio_match:
        aspect_ratio = ratio_match.group(1)
        if aspect_ratio not in VALID_IMAGE_RATIOS:
            raise ValueError(
                f"Invalid ratio: {aspect_ratio}. Must be one of: {', '.join(VALID_IMAGE_RATIOS)}"
            )
        prompt = prompt.replace(ratio_match.group(0), "").strip()

    return prompt, n, aspect_ratio


def extract_image_urls_from_markdown(text: str) -> List[str]:
    """
    从Markdown文本中提取图片URL

    Args:
        text: Markdown文本

    Returns:
        List[str]: 图片URL列表
    """
    pattern = IMAGE_URL_PATTERN
    matches = re.findall(pattern, text)
    return [match[1] for match in matches]


def is_valid_api_key(key: str) -> bool:
    """
    检查API密钥格式是否有效

    Args:
        key: API密钥

    Returns:
        bool: 如果密钥格式有效则返回True
    """
    # 检查Gemini API密钥格式
    if key.startswith("AIza"):
        return len(key) >= 30

    # 检查OpenAI API密钥格式
    if key.startswith("sk-"):
        return len(key) >= 30

    return False


def redact_key_for_logging(key: str) -> str:
    """
    Redacts API key for secure logging by showing only first and last 6 characters.

    Args:
        key: API key to redact

    Returns:
        str: Redacted key in format "first6...last6" or descriptive placeholder for edge cases
    """
    if not key:
        return key

    if len(key) <= 12:
        return f"{key[:3]}...{key[-3:]}"
    else:
        return f"{key[:6]}...{key[-6:]}"


def get_current_version(default_version: str = "0.0.0") -> str:
    """Reads the current version from the VERSION file."""
    version_file = VERSION_FILE_PATH
    try:
        with version_file.open("r", encoding="utf-8") as f:
            version = f.read().strip()
        if not version:
            helper_logger.warning(
                f"VERSION file ('{version_file}') is empty. Using default version '{default_version}'."
            )
            return default_version
        return version
    except FileNotFoundError:
        helper_logger.warning(
            f"VERSION file not found at '{version_file}'. Using default version '{default_version}'."
        )
        return default_version
    except IOError as e:
        helper_logger.error(
            f"Error reading VERSION file ('{version_file}'): {e}. Using default version '{default_version}'."
        )
        return default_version


def is_image_upload_configured(settings: Settings) -> bool:
    """Return True only if a valid upload provider is selected and all required settings for that provider are present."""

    provider = (getattr(settings, "UPLOAD_PROVIDER", "") or "").strip().lower()
    if provider == "smms":
        return bool(getattr(settings, "SMMS_SECRET_TOKEN", ""))
    if provider == "picgo":
        return bool(getattr(settings, "PICGO_API_KEY", ""))
    if provider == "aliyun_oss":
        return all(
            [
                getattr(settings, "OSS_ACCESS_KEY", ""),
                getattr(settings, "OSS_ACCESS_KEY_SECRET", ""),
                getattr(settings, "OSS_BUCKET_NAME", ""),
                getattr(settings, "OSS_ENDPOINT", ""),
                getattr(settings, "OSS_REGION", "")
            ]
        )
    if provider == "cloudflare_imgbed":
        return all(
            [
                getattr(settings, "CLOUDFLARE_IMGBED_URL", ""),
                getattr(settings, "CLOUDFLARE_IMGBED_AUTH_CODE", ""),
            ]
        )
    return False
