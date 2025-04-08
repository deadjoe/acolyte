#!/usr/bin/env python
"""
直接处理测试任务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import Task, TaskStatus
from acolyte.core.task.processor import TaskProcessor


async def process_task(task_id):
    """处理指定ID的任务

    Args:
        task_id: 任务ID
    """
    # 获取任务信息
    with db.session_scope() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            print(f"错误: 未找到ID为{task_id}的任务")
            return

        print(
            f"找到任务: ID={task.id}, 状态={task.status.value}, 模式={task.processing_mode.value}"
        )

    # 创建任务处理器
    processor = TaskProcessor()

    # 处理任务
    print(f"开始处理任务 {task_id}...")
    result = await processor.process_task(task_id)

    print(f"任务处理完成: {result}")

    # 获取更新后的任务状态
    with db.session_scope() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        print(f"任务状态: {task.status.value}")

        if task.final_result_id:
            print(f"最终结果ID: {task.final_result_id}")


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python process_test_task.py <任务ID>")
        return

    try:
        task_id = int(sys.argv[1])
    except ValueError:
        print("错误: 任务ID必须是整数")
        return

    # 运行异步函数
    asyncio.run(process_task(task_id))


if __name__ == "__main__":
    main()
