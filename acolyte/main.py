"""
Acolyte应用启动入口
"""

import os
import socket
import sys
from pathlib import Path

import uvicorn

from acolyte.utils.logging import LOG_LEVELS, get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


def main():
    """启动API服务"""
    # 检查日志级别配置
    log_level = os.environ.get("ACOLYTE_LOG_LEVEL", "info").lower()
    if log_level not in LOG_LEVELS:
        # 这里不能直接使用logger，因为logger还未配置
        # 使用标准输出打印警告，然后在日志系统初始化后再记录
        sys.stderr.write(f"警告: 无效的日志级别 '{log_level}', 使用默认级别 'info'\n")
        log_level = "info"

    # 设置环境变量以启用日志记录
    os.environ["ACOLYTE_LOG_LEVEL"] = log_level

    # 检查是否启用文件日志
    log_to_file = os.environ.get("ACOLYTE_LOG_TO_FILE", "0")
    if log_to_file == "1":
        log_dir = os.environ.get("ACOLYTE_LOG_DIR", str(Path.cwd()))
        logger.info(f"日志将写入目录: {log_dir}")

    # 记录启动环境信息
    logger.info("=" * 40)
    logger.info("Acolyte内容分析评估系统启动")
    logger.info("-" * 40)
    logger.info(f"应用版本: 0.1.0")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"系统平台: {sys.platform}")
    logger.info(f"主机名: {socket.gethostname()}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"日志级别: {log_level}")
    logger.info("=" * 40)

    # 获取端口
    port = int(os.environ.get("ACOLYTE_PORT", "8000"))

    try:
        # 启动API服务
        logger.info(f"启动API服务于: http://0.0.0.0:{port}")
        uvicorn.run(
            "acolyte.api.app:app",
            host="0.0.0.0",
            port=port,
            reload=False,  # 设置为False避免多个进程并行运行
            log_level="error",  # 只显示错误日志，不显示访问日志
        )
    except Exception as e:
        logger.critical(f"启动API服务失败: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
