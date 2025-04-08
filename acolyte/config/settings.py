"""
应用配置管理
"""

import json
import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from acolyte.utils.logging import get_logger

# 获取配置模块的日志记录器
logger = get_logger("acolyte.config")


class LlmConfigModel(BaseModel):
    """LLM配置模型"""

    name: str
    api_key: str
    base_url: str
    model_name: str
    description: Optional[str] = None
    role: str = "normal"
    is_default: bool = False


class AppConfig(BaseModel):
    """应用配置模型"""

    database_url: str = "sqlite:///acolyte.db"
    default_prompt_version: Optional[str] = None
    # prompt_dir字段已移除，因为它与LLM配置无关，应该由PromptManager自行管理
    llm_configs: List[LlmConfigModel] = []


def get_config_path() -> Path:
    """获取配置文件路径"""
    # 首先检查环境变量
    config_path = os.environ.get("ACOLYTE_CONFIG_PATH")
    if config_path:
        return Path(config_path)

    # 然后检查用户目录
    user_config = Path.home() / ".config" / "acolyte" / "config.json"
    if user_config.exists():
        return user_config

    # 最后检查当前目录
    local_config = Path.cwd() / "acolyte_config.json"
    if local_config.exists():
        return local_config

    # 如果都没有找到，返回默认配置文件路径
    default_path = Path.home() / ".config" / "acolyte" / "config.json"
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return default_path


def load_config(verbose=False) -> AppConfig:
    """加载配置

    Args:
        verbose: 是否输出详细日志

    Returns:
        应用配置对象
    """
    config_path = get_config_path()
    logger.info(f"从 {config_path} 加载配置")

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                logger.debug(f"配置文件加载成功: {len(str(config_data))} 字节")

                # 尝试解析成配置对象
                config_obj = AppConfig(**config_data)
                logger.info(f"配置加载完成，包含 {len(config_obj.llm_configs)} 个LLM配置")
                return config_obj
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}", exc_info=True)
    else:
        logger.warning(f"配置文件 {config_path} 不存在，将使用默认配置")

    # 返回默认配置
    logger.info("返回默认配置")
    return AppConfig()


def save_config(config: AppConfig) -> bool:
    """保存配置"""
    config_path = get_config_path()
    logger.info(f"保存配置到 {config_path}")

    try:
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"确保配置目录存在: {config_path.parent}")

        # 将配置序列化为JSON并写入文件
        json_data = config.model_dump_json(indent=2)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(json_data)

        logger.info(f"配置文件保存成功: {len(json_data)} 字节")
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败: {str(e)}", exc_info=True)
        return False


# 提供全局配置实例
config = load_config(verbose=False)
