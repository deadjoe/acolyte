"""
应用配置管理
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
    if verbose:
        print(f"从 {config_path} 加载配置")
    
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                if verbose:
                    print(f"配置文件内容: {json.dumps(config_data, ensure_ascii=False, indent=2)[:200]}...")
                config_obj = AppConfig(**config_data)
                if verbose:
                    print(f"配置加载完成，包含 {len(config_obj.llm_configs)} 个LLM配置")
                return config_obj
        except Exception as e:
            if verbose:
                print(f"加载配置文件失败: {e}")
    else:
        if verbose:
            print(f"配置文件 {config_path} 不存在")
    
    # 返回默认配置
    if verbose:
        print("返回默认配置")
    return AppConfig()


def save_config(config: AppConfig) -> bool:
    """保存配置"""
    config_path = get_config_path()
    
    try:
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config.model_dump_json(indent=2))
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False


# 提供全局配置实例
config = load_config(verbose=False)