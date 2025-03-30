#!/usr/bin/env python
"""
转换配置文件格式
"""
import json
import os
from pathlib import Path
from typing import List

from pydantic import BaseModel


class LlmConfigModel(BaseModel):
    """LLM配置模型"""
    name: str
    api_key: str
    base_url: str
    model_name: str
    description: str = None
    role: str = "normal"
    is_default: bool = False


class AppConfig(BaseModel):
    """应用配置模型"""
    database_url: str = "sqlite:///acolyte.db"
    default_prompt_version: str = ""  # 空字符串而不是None
    llm_configs: List[LlmConfigModel] = []


def main():
    """主函数"""
    config_path = Path.home() / ".config" / "acolyte" / "config.json"
    
    # 读取现有配置
    with open(config_path, "r", encoding="utf-8") as f:
        old_config = json.load(f)
    
    # 转换为新格式
    new_config = AppConfig(
        database_url="sqlite:///acolyte.db",
        default_prompt_version="",
        llm_configs=[]
    )
    
    if "llms" in old_config:
        for name, llm_data in old_config["llms"].items():
            # 确保name字段正确
            llm_data["name"] = name
            # 添加到新配置
            new_config.llm_configs.append(LlmConfigModel(**llm_data))
    
    # 保存新配置
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_config.model_dump_json(indent=2))
    
    print(f"配置已转换并保存到 {config_path}")


if __name__ == "__main__":
    main()