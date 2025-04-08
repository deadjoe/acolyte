#!/usr/bin/env python
"""
检查数据库中的LLM配置记录
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import LlmConfig


def main():
    """主函数"""
    with db.session_scope() as session:
        llms = session.query(LlmConfig).all()

        print(f"数据库中共有 {len(llms)} 条LLM配置记录")

        for llm in llms:
            print(f"ID: {llm.id}, 名称: {llm.name}")
            print(f"模型: {llm.model_name}")
            print(f"角色: {llm.role.value}")
            print(f"默认: {'是' if llm.is_default else '否'}")
            print(f"创建时间: {llm.created_at}")
            print("-" * 40)


if __name__ == "__main__":
    main()
