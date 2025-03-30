#!/usr/bin/env python
"""
创建测试任务的工具
"""
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import Task, ProcessingMode, LlmConfig


def main():
    """主函数"""
    # 读取测试文本
    test_file = project_root / "tests" / "texts" / "test_1.txt"
    print(f"读取测试文件: {test_file}")
    
    try:
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"内容长度: {len(content)} 字符")
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 获取默认LLM
    with db.session_scope() as session:
        llm = session.query(LlmConfig).filter_by(is_default=True).first()
        if not llm:
            print("错误: 未找到默认LLM配置")
            return
        
        print(f"使用默认LLM: {llm.name} (ID={llm.id})")
        
        # 创建任务
        task = Task(
            content=content,
            processing_mode=ProcessingMode.SINGLE
        )
        session.add(task)
        session.flush()
        
        # 关联LLM
        task.llm_configs.append(llm)
        
        # 提交
        session.commit()
        
        print(f"成功创建任务，ID={task.id}")
        
        
if __name__ == "__main__":
    main()