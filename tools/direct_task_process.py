#!/usr/bin/env python
"""
直接处理单个LLM任务，绕过TaskProcessor
"""
import os
import sys
import json
import traceback
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# 设置环境变量以启用调试日志
os.environ["ACOLYTE_LOG_LEVEL"] = os.environ.get("ACOLYTE_LOG_LEVEL", "debug")
os.environ["ACOLYTE_LOG_TO_FILE"] = os.environ.get("ACOLYTE_LOG_TO_FILE", "1")

from acolyte.core.db.database import db
from acolyte.core.db.models import Task, TaskResult, LlmConfig, TaskStatus, Prompt
from acolyte.core.llm.client import get_client_for_llm
from acolyte.core.prompt.manager import PromptManager
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger("direct_task_process")


async def main():
    """主函数"""
    logger.info("启动直接任务处理工具")

    if len(sys.argv) != 2:
        logger.error("参数错误: 未提供任务ID")
        print("用法: python direct_task_process.py <任务ID>")
        return

    try:
        task_id = int(sys.argv[1])
        logger.info(f"处理任务: ID={task_id}")
    except ValueError:
        logger.error("参数错误: 任务ID必须是整数")
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
                logger.error(f"任务不存在: ID={task_id}")
                print(f"错误: 未找到ID为{task_id}的任务")
                return

            logger.info(f"找到任务: ID={task.id}, 状态={task.status.value}, 模式={task.processing_mode.value}")
            print(f"找到任务: ID={task.id}, 状态={task.status.value}")

            # 获取内容
            task_content = task.content
            logger.debug(f"任务内容长度: {len(task_content)} 字符")
            print(f"内容长度: {len(task_content)} 字符")

            # 获取LLM
            if task.llm_configs:
                db_llm = task.llm_configs[0]  # 只使用第一个LLM
                logger.info(f"任务关联LLM: {db_llm.name} (ID={db_llm.id})")

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
                logger.info(f"使用LLM: {llm_config.name} (ID={llm_config.id}, 模型={llm_config.model_name})")
                print(f"使用LLM: {llm_config.name} (ID={llm_config.id})")
            else:
                # 获取默认LLM
                logger.info("任务无关联LLM，尝试使用默认LLM")
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
                    logger.info(f"使用默认LLM: {llm_config.name} (ID={llm_config.id}, 模型={llm_config.model_name})")
                    print(f"使用默认LLM: {llm_config.name} (ID={llm_config.id})")
                else:
                    logger.error("未找到可用的LLM配置")
                    print("错误: 未找到可用的LLM")
                    return

            # 获取prompt
            prompt_manager = PromptManager(prompt_dir=str(project_root / "prompt"))
            if task.prompt_id:
                logger.info(f"尝试获取指定的Prompt: ID={task.prompt_id}")
                db_prompt = session.query(Prompt).filter(Prompt.id == task.prompt_id).first()
                if db_prompt:
                    prompt_content = db_prompt.content
                    logger.info(f"使用指定的Prompt: ID={task.prompt_id}, 版本={db_prompt.version}")
                    logger.debug(f"Prompt内容长度: {len(prompt_content)} 字符")
                    print(f"使用Prompt ID: {task.prompt_id}, 长度: {len(prompt_content)} 字符")
                else:
                    logger.error(f"未找到指定的Prompt: ID={task.prompt_id}")
                    print(f"未找到ID为{task.prompt_id}的Prompt")
                    return
            else:
                # 获取最新的Prompt
                logger.info("任务无关联Prompt，尝试使用最新Prompt")
                with db.session_scope() as prompt_session:
                    latest_prompt = prompt_session.query(Prompt).order_by(Prompt.id.desc()).first()
                    if latest_prompt:
                        prompt_content = latest_prompt.content
                        logger.info(f"使用最新Prompt: ID={latest_prompt.id}, 版本={latest_prompt.version}")
                        logger.debug(f"Prompt内容长度: {len(prompt_content)} 字符")
                        print(f"使用最新Prompt, 长度: {len(prompt_content)} 字符")
                    else:
                        logger.error("未找到可用的Prompt")
                        print("错误: 未找到可用的Prompt")
                        return

            # 更新任务状态
            task.status = TaskStatus.PROCESSING
            session.commit()
            logger.debug(f"已更新任务状态为处理中: ID={task_id}")

        # 处理任务
        logger.info(f"开始处理任务: ID={task_id}")
        print(f"开始处理任务...")

        # 创建LLM客户端
        logger.debug(f"创建LLM客户端: {llm_config.name}, 模型={llm_config.model_name}")
        client = get_client_for_llm(llm_config)

        # 调用API
        logger.info("发送API请求...")
        result = await client.process_content(task_content, prompt_content)

        if result["success"]:
            logger.info("API调用成功!")
            processing_time = result.get('result', {}).get('processing_time', 'N/A')
            logger.info(f"处理时间: {processing_time}秒")
            logger.debug(f"原始响应长度: {len(result['raw_response'])} 字符")

            print("API调用成功!")
            print(f"处理时间: {processing_time}秒")
            print(f"结果内容长度: {len(result['raw_response'])} 字符")

            # 获取评分结果
            bias_index = result["result"].get("bias_index")
            misleading_index = result["result"].get("misleading_index")
            hidden_intent_index = result["result"].get("hidden_intent_index")
            credibility_score = result["result"].get("credibility_score")

            logger.info(f"评分结果: BI={bias_index}, MI={misleading_index}, "
                       f"HI={hidden_intent_index}, CS={credibility_score}")

            # 保存结果
            logger.info("保存结果到数据库...")
            with db.session_scope() as session:
                task_result = TaskResult(
                    task_id=task_id,
                    llm_id=llm_config.id,
                    raw_response=result["raw_response"],
                    processed_result=json.dumps(result.get("result", {})),
                    bias_index=bias_index,
                    misleading_index=misleading_index,
                    hidden_intent_index=hidden_intent_index,
                    credibility_score=credibility_score,
                    is_review_result=False
                )
                session.add(task_result)
                session.flush()

                # 更新任务状态
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.COMPLETED
                    task.final_result_id = task_result.id
                    logger.debug(f"已更新任务状态为已完成: ID={task_id}")
                    logger.debug(f"已设置最终结果ID: {task_result.id}")

                logger.info(f"结果已保存: ID={task_result.id}")
                print(f"保存了结果: ID={task_result.id}")
                print(f"偏见指数: {task_result.bias_index}")
                print(f"误导性指数: {task_result.misleading_index}")
                print(f"隐藏意图指数: {task_result.hidden_intent_index}")
                print(f"可信度分数: {task_result.credibility_score}")

        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"API调用失败: {error}")
            print(f"API调用失败: {error}")

            # 更新任务状态为失败
            logger.info("更新任务状态为失败")
            with db.session_scope() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = TaskStatus.FAILED
                    logger.debug(f"已更新任务状态为失败: ID={task_id}")
    except Exception as e:
        logger.error(f"处理过程异常: {str(e)}")
        logger.debug(f"异常详情: {traceback.format_exc()}")
        print(f"处理失败: {e}")

        # 更新任务状态为失败
        logger.info("更新任务状态为失败")
        with db.session_scope() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = TaskStatus.FAILED
                logger.debug(f"已更新任务状态为失败: ID={task_id}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())