#!/usr/bin/env python
"""
直接在数据库中创建测试任务
"""
import sys
from pathlib import Path
import uuid

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
        default_llm = session.query(LlmConfig).filter(LlmConfig.is_default == True).first()
        if not default_llm:
            print("错误: 未找到默认LLM配置")
            return
            
        # 获取prompt ID
        prompt_id = 1  # 我们知道ID为1
        
        # 创建单LLM任务
        test_task = Task(
            content=content,
            processing_mode=ProcessingMode.SINGLE,
            status=TaskStatus.PENDING,
            prompt_id=prompt_id
        )
        
        # 关联LLM
        test_task.llm_configs = [default_llm]
        
        session.add(test_task)
        session.flush()
        
        print(f"创建了测试任务: ID={test_task.id}, 模式={test_task.processing_mode.value}")
        print(f"使用LLM: {default_llm.name} (ID={default_llm.id})")
        print(f"使用Prompt ID: {prompt_id}")


if __name__ == "__main__":
    main()