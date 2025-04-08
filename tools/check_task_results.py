#!/usr/bin/env python
"""
检查任务结果
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import LlmConfig, Task, TaskResult


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python check_task_results.py <任务ID>")
        return

    try:
        task_id = int(sys.argv[1])
    except ValueError:
        print("错误: 任务ID必须是整数")
        return

    # 查询任务信息
    with db.session_scope() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            print(f"错误: 未找到ID为{task_id}的任务")
            return

        print("任务信息:")
        print(f"  ID: {task.id}")
        print(f"  状态: {task.status.value}")
        print(f"  处理模式: {task.processing_mode.value}")
        print(f"  创建时间: {task.created_at}")
        print(f"  更新时间: {task.updated_at}")
        print(f"  Prompt ID: {task.prompt_id}")
        print(f"  最终结果ID: {task.final_result_id}")

        # 查询任务关联的LLM
        llms = task.llm_configs
        print(f"关联的LLM ({len(llms)}个):")
        for llm in llms:
            print(f"  - {llm.name} (ID={llm.id}, 角色={llm.role.value})")

        # 查询任务结果
        results = session.query(TaskResult).filter(TaskResult.task_id == task_id).all()
        print(f"任务结果 ({len(results)}个):")
        for result in results:
            llm = session.query(LlmConfig).filter(LlmConfig.id == result.llm_id).first()
            llm_name = llm.name if llm else f"未知LLM (ID={result.llm_id})"

            print(f"  结果ID: {result.id}")
            print(f"  LLM: {llm_name}")
            print(f"  偏见指数: {result.bias_index}")
            print(f"  误导性指数: {result.misleading_index}")
            print(f"  隐藏意图指数: {result.hidden_intent_index}")
            print(f"  可信度分数: {result.credibility_score}")
            print(f"  是否为评议结果: {result.is_review_result}")
            print(f"  创建时间: {result.created_at}")

            if result.raw_response:
                print(f"  原始响应长度: {len(result.raw_response)} 字符")
                print(f"  原始响应片段: {result.raw_response[:100]}...")
            else:
                print("  无原始响应")

            print("  " + "-" * 40)


if __name__ == "__main__":
    main()
