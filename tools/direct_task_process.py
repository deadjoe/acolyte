#!/usr/bin/env python
"""
直接处理单个LLM任务，绕过TaskProcessor
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from acolyte.core.db.database import db
from acolyte.core.db.models import Task, TaskResult, LlmConfig, TaskStatus, Prompt
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.prompt.manager import PromptManager


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python direct_task_process.py <任务ID>")
        return
        
    try:
        task_id = int(sys.argv[1])
    except ValueError:
        print("错误: 任务ID必须是整数")
        return
        
    # 处理任务
    try:
        # 获取任务信息和LLM信息
        task_content = None
        llm_config = None
        prompt_content = None
        
        with db.session_scope() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                print(f"错误: 未找到ID为{task_id}的任务")
                return
                
            print(f"找到任务: ID={task.id}, 状态={task.status.value}")
            
            # 获取内容
            task_content = task.content
            print(f"内容长度: {len(task_content)} 字符")
            
            # 获取LLM
            if task.llm_configs:
                db_llm = task.llm_configs[0]  # 只使用第一个LLM
                
                # 创建新的LLM配置对象以便在会话外使用
                llm_config = LlmConfig(
                    id=db_llm.id,
                    name=db_llm.name,
                    api_key=db_llm.api_key,
                    base_url=db_llm.base_url,
                    model_name=db_llm.model_name,
                    role=db_llm.role,
                    is_default=db_llm.is_default
                )
                print(f"使用LLM: {llm_config.name} (ID={llm_config.id})")
            else:
                # 获取默认LLM
                db_llm = session.query(LlmConfig).filter(LlmConfig.is_default == True).first()
                if db_llm:
                    # 创建新的LLM配置对象以便在会话外使用
                    llm_config = LlmConfig(
                        id=db_llm.id,
                        name=db_llm.name,
                        api_key=db_llm.api_key,
                        base_url=db_llm.base_url,
                        model_name=db_llm.model_name,
                        role=db_llm.role,
                        is_default=db_llm.is_default
                    )
                    print(f"使用默认LLM: {llm_config.name} (ID={llm_config.id})")
                else:
                    print("错误: 未找到可用的LLM")
                    return
                    
            # 获取prompt
            prompt_manager = PromptManager(prompt_dir=str(project_root / "prompt"))
            if task.prompt_id:
                db_prompt = session.query(Prompt).filter(Prompt.id == task.prompt_id).first()
                if db_prompt:
                    prompt_content = db_prompt.content
                    print(f"使用Prompt ID: {task.prompt_id}, 长度: {len(prompt_content)} 字符")
                else:
                    print(f"未找到ID为{task.prompt_id}的Prompt")
                    return
            else:
                # 获取最新的Prompt
                with db.session_scope() as prompt_session:
                    latest_prompt = prompt_session.query(Prompt).order_by(Prompt.id.desc()).first()
                    if latest_prompt:
                        prompt_content = latest_prompt.content
                        print(f"使用最新Prompt, 长度: {len(prompt_content)} 字符")
                    else:
                        print("错误: 未找到可用的Prompt")
                        return
                    
            # 更新任务状态
            task.status = TaskStatus.PROCESSING
            session.commit()
        
        # 处理任务
        print(f"开始处理任务...")
        
        # 创建LLM客户端
        client = get_client_for_llm(llm_config)
        
        # 调用API
        result = client.process_content(task_content, prompt_content)
        
        if result["success"]:
            print("API调用成功!")
            print(f"处理时间: {result.get('result', {}).get('processing_time', 'N/A')}秒")
            print(f"结果内容长度: {len(result['raw_response'])} 字符")
            
            # 保存结果
            with db.session_scope() as session:
                task_result = TaskResult(
                    task_id=task_id,
                    llm_id=llm_config.id,
                    raw_response=result["raw_response"],
                    processed_result=json.dumps(result.get("result", {})),
                    bias_index=result["result"].get("bias_index"),
                    misleading_index=result["result"].get("misleading_index"),
                    hidden_intent_index=result["result"].get("hidden_intent_index"),
                    credibility_score=result["result"].get("credibility_score"),
                    is_review_result=False
                )
                session.add(task_result)
                session.flush()
                
                # 更新任务状态
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.COMPLETED
                    task.final_result_id = task_result.id
                
                print(f"保存了结果: ID={task_result.id}")
                print(f"偏见指数: {task_result.bias_index}")
                print(f"误导性指数: {task_result.misleading_index}")
                print(f"隐藏意图指数: {task_result.hidden_intent_index}")
                print(f"可信度分数: {task_result.credibility_score}")
                
        else:
            print(f"API调用失败: {result.get('error', 'Unknown error')}")
            # 更新任务状态为失败
            with db.session_scope() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED
    except Exception as e:
        print(f"处理失败: {e}")
        # 更新任务状态为失败
        with db.session_scope() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED


if __name__ == "__main__":
    main()