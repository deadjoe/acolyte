#!/usr/bin/env python
"""
检查数据库中的prompt记录
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import Prompt


def main():
    """主函数"""
    with db.session_scope() as session:
        prompts = session.query(Prompt).all()
        
        print(f"数据库中共有 {len(prompts)} 条Prompt记录")
        
        for prompt in prompts:
            print(f"ID: {prompt.id}, 版本: {prompt.version}, 目标: {prompt.model_target}")
            print(f"描述: {prompt.description}")
            print(f"文件路径: {prompt.file_path}")
            print(f"内容长度: {len(prompt.content) if prompt.content else 0} 字符")
            print(f"创建时间: {prompt.created_at}")
            print(f"是否激活: {prompt.is_active}")
            print("-" * 40)


if __name__ == "__main__":
    main()