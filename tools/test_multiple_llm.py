#!/usr/bin/env python
"""
测试多LLM任务
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import Task, ProcessingMode, TaskStatus, LlmConfig


def main():
    """主函数"""
    # 读取测试文件
    test_file_path = project_root / "tests" / "texts" / "test_1.txt"
    
    with open(test_file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    print(f"读取测试文件: {test_file_path}")
    print(f"内容长度: {len(content)} 字符")
    
    # 创建测试任务
    with db.session_scope() as session:
        # 获取可用的LLM
        llm_configs = session.query(LlmConfig).all()
        
        if not llm_configs:
            print("错误: 未找到可用的LLM配置")
            return
            
        print(f"找到 {len(llm_configs)} 个LLM配置:")
        for llm in llm_configs:
            print(f"  - {llm.name} (ID={llm.id}, 角色={llm.role.value})")
            
        # 获取所有普通角色的LLM
        normal_llms = [llm for llm in llm_configs if llm.role.value == "normal"]
        
        # 获取prompt ID
        prompt_id = 1  # 我们知道ID为1
        
        # 创建多LLM任务
        test_task = Task(
            content=content,
            processing_mode=ProcessingMode.MULTIPLE,
            status=TaskStatus.PENDING,
            prompt_id=prompt_id
        )
        
        # 关联LLM
        if len(normal_llms) > 0:
            # 最多使用2个LLM
            test_task.llm_configs = normal_llms[:2]
            
            session.add(test_task)
            session.flush()
            
            task_llms = [llm.name for llm in test_task.llm_configs]
            print(f"创建了测试任务: ID={test_task.id}, 模式={test_task.processing_mode.value}")
            print(f"使用LLM: {', '.join(task_llms)}")
            print(f"使用Prompt ID: {prompt_id}")
        else:
            print("错误: 未找到普通角色的LLM")


if __name__ == "__main__":
    main()