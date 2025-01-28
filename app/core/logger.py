import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional
import platform

# ANSI转义序列颜色代码
COLORS = {
    'DEBUG': '\033[34m',  # 蓝色
    'INFO': '\033[32m',  # 绿色
    'WARNING': '\033[33m',  # 黄色
    'ERROR': '\033[31m',  # 红色
    'CRITICAL': '\033[1;31m'  # 红色加粗
}

# Windows系统启用ANSI支持
if platform.system() == 'Windows':
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


class ColoredFormatter(logging.Formatter):
    """
    自定义的日志格式化器,添加颜色支持
    """

    def format(self, record):
        # 获取对应级别的颜色代码
        color = COLORS.get(record.levelname, '')
        # 添加颜色代码和重置代码
        record.levelname = f"{color}{record.levelname}\033[0m"
        return super().format(record)


# 日志格式
FORMATTER = ColoredFormatter(
    "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)

# 日志级别映射
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class Logger:
    def __init__(self):
        pass

    _loggers: Dict[str, logging.Logger] = {}

    @staticmethod
    def setup_logger(
            name: str,
            level: str = "debug",
    ) -> logging.Logger:
        """
        设置并获取logger
        :param name: logger名称
        :param level: 日志级别
        :return: logger实例
        """
        if name in Logger._loggers:
            return Logger._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(LOG_LEVELS.get(level.lower(), logging.INFO))
        logger.propagate = False

        # 添加控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(FORMATTER)
        logger.addHandler(console_handler)

        # 创建日志目录
        LOG_DIR = os.getenv('LOG_DIR', 'logs')
        os.makedirs(LOG_DIR, exist_ok=True)

        try:
            # 尝试添加文件处理器
            log_file = os.path.join(LOG_DIR, f'{name}.log')
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(FORMATTER)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"无法创建日志文件处理器: {str(e)}")
            logger.warning("将只使用控制台日志输出")

        Logger._loggers[name] = logger
        return logger

    @staticmethod
    def get_logger(name: str) -> Optional[logging.Logger]:
        """
        获取已存在的logger
        :param name: logger名称
        :return: logger实例或None
        """
        return Logger._loggers.get(name)


# 预定义的loggers
def get_openai_logger():
    return Logger.setup_logger("openai")


def get_gemini_logger():
    return Logger.setup_logger("gemini")


def get_chat_logger():
    return Logger.setup_logger("chat")


def get_model_logger():
    return Logger.setup_logger("model")


def get_security_logger():
    return Logger.setup_logger("security")


def get_key_manager_logger():
    return Logger.setup_logger("key_manager")


def get_main_logger():
    return Logger.setup_logger("main")


def get_embeddings_logger():
    return Logger.setup_logger("embeddings")


def get_request_logger():
    return Logger.setup_logger("request")


def get_retry_logger():
    return Logger.setup_logger("retry")