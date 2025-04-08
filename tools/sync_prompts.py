#!/usr/bin/env python
"""
显式同步prompt文件的工具
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.prompt.manager import PromptManager


def main():
    """主函数"""
    # 显式设置prompt目录为项目根目录下的prompt目录
    prompt_dir = os.path.join(project_root, "prompt")

    print(f"使用prompt目录: {prompt_dir}")
    prompt_manager = PromptManager(prompt_dir=prompt_dir)

    # 检查目录中是否有.md文件
    md_files = list(Path(prompt_dir).glob("*.md"))
    print(f"找到 {len(md_files)} 个.md文件: {[f.name for f in md_files]}")

    # 同步prompt文件
    prompt_manager.sync_prompt_files_to_db()
    print("Prompt同步完成")


if __name__ == "__main__":
    main()
