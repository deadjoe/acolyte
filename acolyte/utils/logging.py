"""
统一日志系统
"""
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 日志级别映射
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# 默认日志级别
DEFAULT_LOG_LEVEL = "warning"  # 设置为debug以捕获所有日志

# 获取环境变量中指定的日志级别
ENV_LOG_LEVEL = os.environ.get("ACOLYTE_LOG_LEVEL", DEFAULT_LOG_LEVEL).lower()
LOG_LEVEL = LOG_LEVELS.get(ENV_LOG_LEVEL, logging.DEBUG)  # 如果环境变量不匹配，默认为DEBUG

# 是否输出到文件
LOG_TO_FILE = os.environ.get("ACOLYTE_LOG_TO_FILE", "0") == "1"

# 日志文件路径
if LOG_TO_FILE:
    LOG_DIR = Path(os.environ.get("ACOLYTE_LOG_DIR", Path.cwd()))
    LOG_FILE = LOG_DIR / f"acolyte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
else:
    LOG_FILE = None

# 日志格式
CONSOLE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"

# 设置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)

# 移除所有现有处理器
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(LOG_LEVEL)
console_formatter = logging.Formatter(CONSOLE_FORMAT, datefmt="%H:%M:%S")
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)

# 如果需要，创建文件处理器
if LOG_TO_FILE:
    # 确保日志目录存在
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(LOG_LEVEL)
    file_formatter = logging.Formatter(FILE_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # 记录日志文件位置
    root_logger.info(f"日志文件位置: {LOG_FILE}")


def get_logger(name):
    """获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)
