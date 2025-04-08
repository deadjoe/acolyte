#!/usr/bin/env python
"""
显示任务结果内容
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import TaskResult


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python show_result.py <结果ID>")
        return

    try:
        result_id = int(sys.argv[1])
    except ValueError:
        print("错误: 结果ID必须是整数")
        return

    # 获取结果
    with db.session_scope() as session:
        result = session.query(TaskResult).filter(TaskResult.id == result_id).first()
        if not result:
            print(f"错误: 未找到ID为{result_id}的结果")
            return

        print(f"任务ID: {result.task_id}")
        print(f"LLM ID: {result.llm_id}")
        print(f"创建时间: {result.created_at}")
        print(f"偏见指数: {result.bias_index}")
        print(f"误导性指数: {result.misleading_index}")
        print(f"隐藏意图指数: {result.hidden_intent_index}")
        print(f"可信度分数: {result.credibility_score}")
        print(f"是否为评议结果: {result.is_review_result}")
        print("\n原始响应:")
        print("=" * 50)
        print(result.raw_response)
        print("=" * 50)


if __name__ == "__main__":
    main()
