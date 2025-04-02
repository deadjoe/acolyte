"""
API路由定义
"""
import asyncio
import os
import traceback
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, root_validator
from sqlalchemy.orm import Session

from acolyte.core.db.database import db
from acolyte.core.db.models import (
    LlmConfig, LlmRole, ProcessingMode, Prompt, Task, TaskResult, TaskStatus
)
from acolyte.core.llm.manager import LlmManager
from acolyte.core.prompt.manager import PromptManager
from acolyte.core.task.processor import TaskProcessor
from acolyte.utils.logging import get_logger

# 获取路由模块日志记录器
logger = get_logger("acolyte.api.routes")


# 创建路由器
router = APIRouter()

# 获取数据库会话依赖
def get_db():
    with db.session_scope() as session:
        yield session


# 模型定义
class LlmConfigCreate(BaseModel):
    name: str
    api_key: str
    base_url: str
    model_name: str
    description: Optional[str] = None
    role: LlmRole = LlmRole.NORMAL
    is_default: bool = False


class LlmConfigUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[LlmRole] = None
    is_default: Optional[bool] = None


class LlmConfigResponse(BaseModel):
    id: int
    name: str
    base_url: str
    model_name: str
    description: Optional[str] = None
    role: str  # 使用字符串而不是枚举
    is_default: bool
    
    class Config:
        orm_mode = True


class TaskCreate(BaseModel):
    content: str
    processing_mode: ProcessingMode
    prompt_id: Optional[int] = None
    llm_ids: Optional[List[int]] = None


class TaskResponse(BaseModel):
    id: int
    content: str
    processing_mode: str  # 使用字符串而不是枚举
    status: str
    prompt_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        orm_mode = True


class TaskResultResponse(BaseModel):
    id: int
    task_id: int
    llm_id: int
    bias_index: Optional[float] = None
    misleading_index: Optional[float] = None
    hidden_intent_index: Optional[float] = None
    credibility_score: Optional[float] = None
    is_review_result: bool
    raw_response: Optional[str] = None

    class Config:
        orm_mode = True


class PromptResponse(BaseModel):
    id: int
    version: str
    model_target: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    content: Optional[str] = None

    class Config:
        orm_mode = True


# LLM配置路由
@router.post("/llms", response_model=LlmConfigResponse)
def create_llm(llm_config: LlmConfigCreate, session: Session = Depends(get_db)):
    """创建新的LLM配置"""
    logger.info(f"正在创建新的LLM配置: {llm_config.name}")
    try:
        llm_manager = LlmManager()
        new_llm = llm_manager.add_llm(
            name=llm_config.name,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            model_name=llm_config.model_name,
            description=llm_config.description,
            role=llm_config.role,
            is_default=llm_config.is_default
        )
        
        logger.info(f"LLM配置创建成功: ID={new_llm.id}, Name={new_llm.name}")
        # 使用to_dict方法
        return new_llm.to_dict()
    except Exception as e:
        logger.error(f"创建LLM配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建LLM配置失败: {str(e)}")


@router.get("/llms", response_model=List[LlmConfigResponse])
def get_llms(
    role: Optional[LlmRole] = None,
    is_default: Optional[bool] = None,
    session: Session = Depends(get_db)
):
    """获取LLM配置列表"""
    query = session.query(LlmConfig)
    if role is not None:
        query = query.filter(LlmConfig.role == role)
    if is_default is not None:
        query = query.filter(LlmConfig.is_default == is_default)
    
    # 获取查询结果并使用to_dict转换
    results = query.all()
    return [item.to_dict() for item in results]


@router.get("/llms/{llm_id}", response_model=LlmConfigResponse)
def get_llm(llm_id: int, session: Session = Depends(get_db)):
    """获取特定LLM配置"""
    llm = session.query(LlmConfig).filter(LlmConfig.id == llm_id).first()
    if not llm:
        raise HTTPException(status_code=404, detail="LLM配置不存在")
    
    # 使用to_dict方法
    return llm.to_dict()


@router.put("/llms/{llm_id}", response_model=LlmConfigResponse)
def update_llm(llm_id: int, llm_config: LlmConfigUpdate, session: Session = Depends(get_db)):
    """更新LLM配置"""
    logger.info(f"正在更新LLM配置: ID={llm_id}")
    try:
        llm_manager = LlmManager()
        update_data = llm_config.dict(exclude_unset=True)
        logger.debug(f"更新数据: {update_data}")
        
        updated_llm = llm_manager.update_llm(llm_id, **update_data)
        if not updated_llm:
            logger.warning(f"LLM配置不存在: ID={llm_id}")
            raise HTTPException(status_code=404, detail="LLM配置不存在")
        
        logger.info(f"LLM配置更新成功: ID={updated_llm.id}, Name={updated_llm.name}")
        # 使用to_dict方法
        return updated_llm.to_dict()
    except Exception as e:
        logger.error(f"更新LLM配置失败: ID={llm_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新LLM配置失败: {str(e)}")


@router.delete("/llms/{llm_id}")
def delete_llm(llm_id: int, session: Session = Depends(get_db)):
    """删除LLM配置"""
    logger.info(f"正在删除LLM配置: ID={llm_id}")
    try:
        llm_manager = LlmManager()
        success = llm_manager.delete_llm(llm_id)
        if not success:
            logger.warning(f"LLM配置不存在: ID={llm_id}")
            raise HTTPException(status_code=404, detail="LLM配置不存在")
        
        logger.info(f"LLM配置删除成功: ID={llm_id}")
        return {"status": "success", "message": "LLM配置已删除"}
    except Exception as e:
        logger.error(f"删除LLM配置失败: ID={llm_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除LLM配置失败: {str(e)}")


@router.post("/llms/{llm_id}/test")
def test_llm_connection(llm_id: int, session: Session = Depends(get_db)):
    """测试LLM连接"""
    logger.info(f"测试LLM连接: ID={llm_id}")
    try:
        llm_manager = LlmManager()
        result = llm_manager.test_connection(llm_id=llm_id)
        logger.info(f"LLM连接测试结果: ID={llm_id}, 状态={result.get('status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"LLM连接测试失败: ID={llm_id}, 错误: {str(e)}", exc_info=True)
        return {"status": "error", "message": f"连接测试失败: {str(e)}"}


# 任务路由
@router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, session: Session = Depends(get_db)):
    """创建新任务"""
    logger.info(f"正在创建新的内容分析任务，处理模式: {task_data.processing_mode}")
    logger.debug(f"内容长度: {len(task_data.content)} 字符")
    
    try:
        # 创建任务
        new_task = Task(
            content=task_data.content,
            processing_mode=task_data.processing_mode,
            prompt_id=task_data.prompt_id
        )
        session.add(new_task)
        session.flush()
        
        logger.info(f"任务已创建: ID={new_task.id}")

        # 如果指定了LLM，关联任务与LLM
        if task_data.llm_ids:
            logger.debug(f"关联LLM: {task_data.llm_ids}")
            llms = session.query(LlmConfig).filter(LlmConfig.id.in_(task_data.llm_ids)).all()
            if len(llms) != len(task_data.llm_ids):
                logger.warning(f"请求的LLM数量 ({len(task_data.llm_ids)}) 与找到的LLM数量 ({len(llms)}) 不匹配")
            new_task.llm_configs.extend(llms)
            logger.debug(f"成功关联 {len(llms)} 个LLM")

        session.commit()
        logger.info(f"任务创建完成并已保存到数据库: ID={new_task.id}")

        # 异步处理任务 - 使用内联实现，不依赖TaskProcessor
        logger.info(f"启动异步任务处理: ID={new_task.id}")
        task_id = new_task.id
        
        # 创建一个异步函数来处理任务
        async def process_task_async(task_id):
            logger.info(f"开始异步处理任务 {task_id}")
            try:
                # 首先更新任务状态为处理中
                with db.session_scope() as session:
                    task = session.query(Task).filter_by(id=task_id).first()
                    if not task:
                        logger.error(f"任务不存在: ID={task_id}")
                        return
                    
                    # 更新任务状态为处理中
                    task.status = TaskStatus.PROCESSING
                    session.commit()
                    logger.info(f"已更新任务状态为处理中: ID={task_id}")
                
                # 使用外部变量存储会话外需要的数据
                task_content = None
                task_id_value = task_id  # 我们已经有了task_id
                llm_data = None
                prompt_content = None
                prompt_id_value = None
                
                # 使用单独的会话获取任务信息
                with db.session_scope() as session:
                    # 获取任务和相关信息
                    task = session.query(Task).filter_by(id=task_id).first()
                    if not task:
                        logger.error(f"任务不存在: ID={task_id}")
                        return
                    
                    # 在会话内显式获取内容和ID
                    task_content = task.content
                    logger.debug(f"成功获取任务内容: 长度={len(task_content)}字符")
                    
                    # 获取默认LLM
                    llm = session.query(LlmConfig).filter_by(is_default=True).first()
                    if not llm:
                        logger.error(f"未找到默认LLM配置")
                        task.status = TaskStatus.FAILED
                        session.commit()
                        return
                    
                    # 在会话内复制LLM数据到字典
                    # 确定提供商类型，基于base_url或模型名称
                    provider = None
                    if "anthropic" in llm.base_url.lower():
                        provider = "anthropic"
                    elif "openai" in llm.base_url.lower() or "azure" in llm.base_url.lower():
                        provider = "openai"
                    elif "googleapis" in llm.base_url.lower() or "google" in llm.base_url.lower():
                        provider = "gemini"
                    else:
                        # 尝试从模型名称推断
                        model_name = llm.model_name.lower()
                        if any(name in model_name for name in ["claude", "anthropic"]):
                            provider = "anthropic"
                        elif any(name in model_name for name in ["gpt", "davinci", "openai"]):
                            provider = "openai"
                        elif any(name in model_name for name in ["gemini", "google"]):
                            provider = "gemini"
                        else:
                            # 默认使用OpenAI
                            provider = "openai"
                    
                    llm_data = {
                        "id": llm.id,
                        "name": llm.name,
                        "api_key": llm.api_key,
                        "base_url": llm.base_url,
                        "model_name": llm.model_name,
                        "provider": provider,
                        "role": llm.role.value if hasattr(llm.role, 'value') else llm.role
                    }
                    logger.debug(f"成功获取LLM配置: {llm_data['name']}, 推断提供商: {provider}")
                    
                    # 获取Prompt
                    prompt = None
                    if task.prompt_id:
                        prompt = session.query(Prompt).filter_by(id=task.prompt_id).first()
                        if prompt:
                            # 在会话内获取内容
                            prompt_content = prompt.content
                            prompt_id_value = prompt.id
                            logger.debug(f"成功获取指定Prompt内容: ID={prompt.id}, 长度={len(prompt_content)}字符")
                
                # 如果在主会话中没找到prompt，使用另一个单独的会话尝试获取
                if not prompt:
                    logger.info("在主会话中未找到prompt，尝试使用单独会话获取")
                    # 使用PromptManager获取最新的Prompt
                    prompt_manager = PromptManager()
                    logger.info("获取最新活跃的prompt")
                    
                    # 直接获取最新的活跃prompt，不关联任何特定模型
                    with db.session_scope() as prompt_session:
                        prompt = prompt_session.query(Prompt).filter(
                            Prompt.is_active == True
                        ).order_by(Prompt.id.asc()).first()
                        
                        if prompt:
                            logger.info(f"找到活跃的prompt: ID={prompt.id}, 版本={prompt.version}")
                            # 在会话内获取内容
                            prompt_content = prompt.content
                            prompt_id_value = prompt.id
                            logger.debug(f"成功获取Prompt内容: 长度={len(prompt_content)}字符")
                        else:
                            logger.warning("数据库中没有活跃的prompt")
                            
                            # 尝试获取任何prompt
                            all_prompts = prompt_session.query(Prompt).all()
                            logger.info(f"数据库中找到 {len(all_prompts)} 个prompt记录")
                            
                            if all_prompts:
                                # 使用第一个prompt
                                prompt = all_prompts[0]
                                prompt_content = prompt.content
                                prompt_id_value = prompt.id
                                logger.info(f"使用第一个可用的prompt: ID={prompt_id_value}")
                                logger.debug(f"成功获取Prompt内容: 长度={len(prompt_content)}字符")
                
                # 检查是否有必要数据
                if not prompt_content:
                    logger.error("无法获取有效的Prompt内容")
                    # 使用新会话更新任务状态
                    with db.session_scope() as fail_session:
                        task = fail_session.query(Task).filter_by(id=task_id).first()
                        if task:
                            task.status = TaskStatus.FAILED
                            fail_session.commit()
                            logger.info(f"已更新任务状态为失败: ID={task_id}")
                    return
                
                logger.info(f"准备阶段完成: 已获取任务、LLM和Prompt数据")
                # 创建LLM客户端并处理内容
                try:
                    # 重建LLM配置对象，确保包含所有必要属性
                    # 注意：不向LlmConfig传递provider属性，因为该类没有这个属性
                    llm_config = LlmConfig(
                        id=llm_data["id"],
                        name=llm_data["name"],
                        api_key=llm_data["api_key"],
                        base_url=llm_data["base_url"],
                        model_name=llm_data["model_name"],
                        role=llm_data["role"]  # 添加角色属性，确保完整
                    )
                    # 动态添加provider属性供client使用
                    setattr(llm_config, 'provider', llm_data["provider"])
                    
                    # 获取对应的LLM客户端
                    from acolyte.core.llm.client import get_client_for_llm
                    client = get_client_for_llm(llm_config)
                    
                    # 处理内容
                    logger.info(f"开始调用LLM API处理内容: 任务ID={task_id}")
                    
                        # 添加额外的验证
                    if not task_content or not llm_data or not prompt_content:
                        error_msg = "缺少必要数据无法处理任务"
                        missing_data = []
                        if not task_content:
                            missing_data.append("任务内容")
                        if not llm_data:
                            missing_data.append("LLM配置")
                        if not prompt_content:
                            missing_data.append("Prompt内容")
                        logger.error(f"{error_msg}: 缺少 {', '.join(missing_data)}")
                        raise ValueError(f"{error_msg}: {', '.join(missing_data)}")
                    
                    # 添加调试日志
                    logger.info(f"调用LLM API: {llm_data['name']} ({llm_data['model_name']})")
                    logger.info(f"使用的任务ID: {task_id_value}")
                    logger.info(f"Prompt内容长度: {len(prompt_content)} 字符")
                    logger.info(f"任务内容长度: {len(task_content)} 字符")
                    
                    # 调用LLM API处理内容
                    
                    # 调用真实LLM API (通过异步运行同步方法)
                    # 使用run_in_executor将同步的process_content方法在线程池中运行，避免阻塞事件循环
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: client.process_content(content=task_content, prompt=prompt_content)
                    )
                    logger.info(f"LLM API调用已完成: 任务ID={task_id}, 成功={response.get('success', False)}")
                    
                    # 解析响应数据
                    result = {
                        "success": response.get("success", False),
                        "raw_response": response.get("raw_response", ""),
                        "processed_result": response.get("processed_result", ""),
                        "result": response.get("result", {})
                    }
                    
                    # 保存处理结果
                    if result["success"]:
                        logger.info(f"API调用成功，保存结果: 任务ID={task_id}")
                        
                        # 提取分析结果
                        bias_index = result["result"].get("bias_index")
                        misleading_index = result["result"].get("misleading_index")
                        hidden_intent_index = result["result"].get("hidden_intent_index")
                        credibility_score = result["result"].get("credibility_score")
                        
                        logger.info(f"评分结果: BI={bias_index}, MI={misleading_index}, "
                                  f"HI={hidden_intent_index}, CS={credibility_score}")
                        
                        # 保存结果到数据库
                        with db.session_scope() as session:
                            # 创建任务结果
                            task_result = TaskResult(
                                task_id=task_id,
                                llm_id=llm_data["id"],
                                raw_response=result["raw_response"],
                                processed_result=result.get("processed_result"),
                                bias_index=bias_index,
                                misleading_index=misleading_index,
                                hidden_intent_index=hidden_intent_index,
                                credibility_score=credibility_score,
                                is_review_result=False
                            )
                            session.add(task_result)
                            session.flush()
                            result_id = task_result.id
                            logger.info(f"已创建任务结果记录: ID={result_id}")
                            
                            # 更新任务状态为已完成
                            task = session.query(Task).filter_by(id=task_id).first()
                            if task:
                                task.status = TaskStatus.COMPLETED
                                task.final_result_id = result_id
                                logger.info(f"已更新任务状态为已完成并设置最终结果: ID={task_id}, 结果ID={result_id}")
                                session.commit()
                                logger.info(f"任务处理成功，已更新状态为已完成: ID={task_id}")
                            else:
                                logger.error(f"无法找到任务进行最终状态更新: ID={task_id}")
                    else:
                        logger.error(f"API调用失败: {result.get('error', '未知错误')}")
                        with db.session_scope() as session:
                            task = session.query(Task).filter_by(id=task_id).first()
                            if task:
                                task.status = TaskStatus.FAILED
                                session.commit()
                                logger.info(f"任务处理失败，已更新状态: ID={task_id}")
                except Exception as e:
                    logger.error(f"处理任务内容时出错: {str(e)}")
                    logger.error(f"错误详情: {traceback.format_exc()}")
                    with db.session_scope() as session:
                        task = session.query(Task).filter_by(id=task_id).first()
                        if task:
                            task.status = TaskStatus.FAILED
                            session.commit()
                            logger.info(f"由于处理异常，已更新任务状态为失败: ID={task_id}")
            except Exception as e:
                logger.error(f"任务处理发生异常: {str(e)}")
                logger.error(f"异常详情: {traceback.format_exc()}")
                try:
                    with db.session_scope() as session:
                        task = session.query(Task).filter_by(id=task_id).first()
                        if task:
                            task.status = TaskStatus.FAILED
                            session.commit()
                            logger.info(f"由于顶层异常，已更新任务状态为失败: ID={task_id}")
                except Exception as inner_e:
                    logger.error(f"无法更新任务状态: {str(inner_e)}")
            
            logger.info(f"异步任务处理完成: ID={task_id}")
            return {"success": True, "task_id": task_id}
        
        # 启动异步任务处理
        background_task = asyncio.create_task(process_task_async(task_id))
        
        # 注册完成回调，确保任务异常被正确处理
        def on_task_done(task):
            try:
                task_result = task.result()  # 如果有未捕获的异常，这里会引发它
                logger.info(f"后台任务完成: ID={task_id}, 成功={task_result.get('success', False) if task_result else False}")
                
                # 检查一下任务状态
                with db.session_scope() as session:
                    db_task = session.query(Task).filter_by(id=task_id).first()
                    if db_task and db_task.status == TaskStatus.PROCESSING:
                        # 异步任务完成了，但数据库中的任务状态没有更新
                        logger.warning(f"任务异步处理已完成但状态未更新，检查结果记录: ID={task_id}")
                        task_result = session.query(TaskResult).filter_by(task_id=task_id).first()
                        if task_result:
                            # 有结果记录，更新任务状态为已完成
                            db_task.status = TaskStatus.COMPLETED
                            db_task.final_result_id = task_result.id
                            session.commit()
                            logger.info(f"任务状态已更新为已完成: ID={task_id}")
                        else:
                            # 无结果记录，可能出现了错误
                            db_task.status = TaskStatus.FAILED
                            session.commit()
                            logger.warning(f"任务处理完成但无结果记录，已更新为失败: ID={task_id}")
            except Exception as e:
                logger.error(f"后台任务执行失败: ID={task_id}, 错误={str(e)}")
                # 确保任务状态更新为失败
                try:
                    with db.session_scope() as session:
                        db_task = session.query(Task).filter_by(id=task_id).first()
                        if db_task and db_task.status != TaskStatus.COMPLETED:
                            db_task.status = TaskStatus.FAILED
                            session.commit()
                            logger.info(f"在回调中将失败任务状态更新为失败: ID={task_id}")
                except Exception as inner_e:
                    logger.error(f"在回调中更新任务状态失败: {str(inner_e)}")
        
        background_task.add_done_callback(on_task_done)

        # 使用to_dict方法确保正确序列化datetime字段
        return new_task.to_dict()
    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/tasks", response_model=List[TaskResponse])
def get_tasks(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db)
):
    """获取任务列表"""
    logger.info(f"获取任务列表: 状态筛选={status}, 跳过={skip}, 限制={limit}")
    try:
        query = session.query(Task)
        if status:
            # 将字符串状态转换为枚举值
            from acolyte.core.db.models import TaskStatus
            try:
                status_enum = TaskStatus(status)
                logger.debug(f"应用状态筛选: {status}")
                query = query.filter(Task.status == status_enum)
            except ValueError:
                logger.warning(f"无效的任务状态值: {status}")
                # 如果无效的状态值，返回空列表
                return []
        
        # 获取查询结果
        results = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
        logger.debug(f"找到 {len(results)} 个任务")
        
        # 使用to_dict转换
        return [task.to_dict() for task in results]
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.delete("/tasks")
def clear_tasks(
    confirm: bool = False,
    status: Optional[str] = None,
    session: Session = Depends(get_db)
):
    """清空所有任务及其关联结果
    
    Args:
        confirm: 必须为True才能执行删除操作
        status: 可选，只删除特定状态的任务
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="必须设置confirm=true参数以确认操作")
    
    # 创建Task查询
    task_query = session.query(Task)
    
    # 如果指定了状态，先筛选
    if status:
        from acolyte.core.db.models import TaskStatus
        try:
            status_enum = TaskStatus(status)
            task_query = task_query.filter(Task.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的任务状态: {status}")
    
    # 获取要删除的任务ID列表
    task_ids = [task.id for task in task_query.all()]
    
    # 如果没有任务，直接返回
    if not task_ids:
        return {"status": "success", "message": "没有找到需要删除的任务", "count": 0}
    
    # 先删除关联的任务结果
    result_count = session.query(TaskResult).filter(TaskResult.task_id.in_(task_ids)).delete()
    
    # 然后删除任务
    task_count = task_query.delete()
    
    # 提交事务
    session.commit()
    
    return {
        "status": "success", 
        "message": f"已清空{task_count}个任务和{result_count}个任务结果",
        "count": task_count
    }


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, session: Session = Depends(get_db)):
    """获取特定任务"""
    logger.info(f"获取特定任务: ID={task_id}")
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"任务不存在: ID={task_id}")
            raise HTTPException(status_code=404, detail="任务不存在")
        logger.debug(f"成功获取任务: ID={task_id}, 状态={task.status.value}")
        return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_db)):
    """删除特定任务及其关联结果"""
    logger.info(f"删除特定任务: ID={task_id}")
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"任务不存在: ID={task_id}")
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 先删除关联的任务结果
        result_count = session.query(TaskResult).filter(TaskResult.task_id == task_id).delete()
        logger.debug(f"已删除 {result_count} 个关联结果")
        
        # 再删除任务本身
        session.delete(task)
        session.commit()
        logger.info(f"成功删除任务: ID={task_id}")
        
        return {"status": "success", "message": f"任务 {task_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
        # 回滚事务
        session.rollback()
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.get("/tasks/{task_id}/results", response_model=List[TaskResultResponse])
def get_task_results(
    task_id: int,
    include_raw_response: bool = False,
    session: Session = Depends(get_db)
):
    """获取任务结果"""
    logger.info(f"获取任务结果: ID={task_id}, 包含原始响应={include_raw_response}")
    
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"任务不存在: ID={task_id}")
            raise HTTPException(status_code=404, detail="任务不存在")

        logger.debug(f"任务状态: {task.status}")
        results = session.query(TaskResult).filter(TaskResult.task_id == task_id).all()
        logger.info(f"找到 {len(results)} 个任务结果")
        
        # 检查结果中是否有缺失指标
        for idx, result in enumerate(results):
            missing_metrics = []
            if result.bias_index is None:
                missing_metrics.append("bias_index")
            if result.misleading_index is None:
                missing_metrics.append("misleading_index")
            if result.hidden_intent_index is None:
                missing_metrics.append("hidden_intent_index")
            if result.credibility_score is None:
                missing_metrics.append("credibility_score")
                
            if missing_metrics:
                logger.warning(f"任务结果 #{idx+1} (ID={result.id}) 缺少以下指标: {', '.join(missing_metrics)}")
        
        # 使用to_dict方法转换，并控制是否包含原始响应
        return [r.to_dict(include_raw_response=include_raw_response) for r in results]
    except Exception as e:
        logger.error(f"获取任务结果失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@router.get("/tasks/{task_id}/final-result", response_model=TaskResultResponse)
def get_task_final_result(
    task_id: int,
    include_raw_response: bool = True,
    session: Session = Depends(get_db)
):
    """获取任务最终结果"""
    logger.info(f"获取任务最终结果: ID={task_id}")
    
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.warning(f"任务不存在: ID={task_id}")
            raise HTTPException(status_code=404, detail="任务不存在")
        
        logger.debug(f"任务状态: {task.status}, 最终结果ID: {task.final_result_id}")
        
        if task.final_result_id:
            logger.info(f"已找到最终结果: ID={task.final_result_id}")
            final_result = session.query(TaskResult).filter(TaskResult.id == task.final_result_id).first()
            return final_result.to_dict(include_raw_response=include_raw_response)
        
        # 如果没有最终结果但任务已完成，查找是否有评议结果
        if task.status == "completed":
            logger.debug("任务已完成但无最终结果，尝试查找评议结果")
            review_result = session.query(TaskResult).filter(
                TaskResult.task_id == task_id,
                TaskResult.is_review_result == True
            ).first()
            
            if review_result:
                logger.info(f"已找到评议结果: ID={review_result.id}")
                return review_result.to_dict(include_raw_response=include_raw_response)
            else:
                logger.warning(f"未找到评议结果")
        
        logger.error(f"任务最终结果不存在: ID={task_id}")
        raise HTTPException(status_code=404, detail="任务最终结果不存在")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"获取任务最终结果失败: ID={task_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务最终结果失败: {str(e)}")


# 配置路由
@router.post("/config/export")
def export_config():
    """导出LLM配置到配置文件"""
    logger.info("开始导出LLM配置到配置文件")
    try:
        from acolyte.core.llm.config import export_llm_config_to_file
        success = export_llm_config_to_file()
        if success:
            logger.info("配置导出成功")
            return {"status": "success", "message": "配置已成功导出到文件"}
        else:
            logger.error("导出配置文件失败")
            raise HTTPException(status_code=500, detail="导出配置文件失败")
    except Exception as e:
        logger.error(f"导出配置文件时发生异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出配置文件失败: {str(e)}")


@router.post("/config/import")
def import_config(name: Optional[str] = None):
    """从配置文件导入LLM配置"""
    logger.info(f"开始从配置文件导入LLM配置{' (' + name + ')' if name else ''}")
    try:
        from acolyte.core.llm.config import import_llm_config_from_file
        imported_llms = import_llm_config_from_file(name, verbose=False)
        
        if imported_llms:
            logger.info(f"成功导入 {len(imported_llms)} 个LLM配置")
            for llm in imported_llms:
                logger.debug(f"导入的LLM: {llm.get('name')}, 模型: {llm.get('model_name')}")
            return {
                "status": "success", 
                "message": f"已导入 {len(imported_llms)} 个LLM配置",
                "llms": imported_llms
            }
        else:
            logger.warning("未导入任何LLM配置")
            return {"status": "warning", "message": "未导入任何LLM配置"}
    except Exception as e:
        logger.error(f"导入配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入配置失败: {str(e)}")


# Prompt路由
@router.get("/prompts", response_model=List[PromptResponse])
def get_prompts(
    model_target: Optional[str] = None,
    active_only: bool = True,
    session: Session = Depends(get_db)
):
    """获取Prompt列表"""
    query = session.query(Prompt)
    if model_target:
        query = query.filter(Prompt.model_target == model_target)
    if active_only:
        query = query.filter(Prompt.is_active == True)
    
    # 获取查询结果并使用to_dict转换
    results = query.order_by(Prompt.version.desc()).all()
    return [item.to_dict(include_content=False) for item in results]


@router.get("/prompts/{prompt_id}", response_model=PromptResponse)
def get_prompt(prompt_id: int, include_content: bool = True, session: Session = Depends(get_db)):
    """获取特定Prompt
    
    Args:
        prompt_id: Prompt ID
        include_content: 是否包含Prompt内容
        session: 数据库会话
    
    Returns:
        Prompt对象
    """
    prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt不存在")
    
    # 使用to_dict方法，指定是否包含内容
    return prompt.to_dict(include_content=include_content)


@router.get("/prompts/{prompt_id}/content")
def get_prompt_content(prompt_id: int, session: Session = Depends(get_db)):
    """获取Prompt内容"""
    prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt不存在")
    return {"content": prompt.content}


class SyncPromptRequest(BaseModel):
    prompt_dir: Optional[str] = None
    
@router.post("/prompts/sync")
def sync_prompts(request: SyncPromptRequest, req: Request):
    """同步Prompt文件到数据库
    
    Args:
        request: 请求数据，可以包含prompt_dir参数
        req: FastAPI原始请求对象
    """
    # 记录完整请求信息（确保在日志中可见）
    request_info = {
        "body": request.model_dump(),
        "query_params": dict(req.query_params),
        "headers": dict(req.headers)
    }
    logger.info(f"收到同步请求，完整信息: {request_info}")
    
    # 获取请求体 - 直接从请求对象读取
    prompt_dir = request.prompt_dir
    logger.info(f"开始同步Prompt文件到数据库，提供的prompt_dir: {prompt_dir}")
    
    # 将prompt_dir转换为绝对路径
    if prompt_dir:
        logger.info(f"收到的prompt_dir非空: {prompt_dir}")
        from pathlib import Path
        prompt_dir_path = Path(prompt_dir).resolve()
        logger.info(f"绝对路径: {prompt_dir_path}")
        # 验证路径是否存在
        if prompt_dir_path.exists() and prompt_dir_path.is_dir():
            logger.info(f"路径验证: {prompt_dir_path} 存在且是目录")
            # 检查目录中是否有.md文件
            md_files = list(prompt_dir_path.glob("*.md"))
            logger.info(f"目录中包含 {len(md_files)} 个.md文件: {[f.name for f in md_files]}")
            
            try:
                # 直接使用相对路径同步prompts
                from acolyte.core.db.database import db
                from acolyte.core.db.models import Prompt
                import re
                
                logger.info(f"直接同步 {len(md_files)} 个文件到数据库")
                
                # 正则表达式匹配文件名
                prompt_pattern = re.compile(
                    r"bias-detection-prompt_v(\d+(?:\.\d+)*)(?:_([a-zA-Z0-9]+))?\.md"
                )
                
                # 处理每个文件
                with db.session_scope() as session:
                    for md_file in md_files:
                        logger.info(f"处理文件: {md_file.name}")
                        # 判断是否符合格式
                        match = prompt_pattern.match(md_file.name)
                        version = None
                        model_target = None
                        
                        if match:
                            version = match.group(1)
                            model_target = match.group(2) or "general"
                            logger.info(f"解析prompt: 版本={version}, 目标={model_target}")
                        elif md_file.name == "bias-detection-prompt_v3.md":
                            version = "3.0"
                            model_target = "claude"
                            logger.info(f"解析特殊prompt: 版本={version}, 目标={model_target}")
                        
                        if version and model_target:
                            # 读取文件内容
                            with open(md_file, "r", encoding="utf-8") as f:
                                content = f.read()
                                logger.info(f"读取文件内容: {len(content)} 字符")
                            
                            # 检查是否存在同版本同目标的prompt
                            existing = session.query(Prompt).filter_by(
                                version=version,
                                model_target=model_target
                            ).first()
                            
                            if existing:
                                logger.info(f"更新现有prompt记录: ID={existing.id}")
                                existing.content = content
                                existing.file_path = str(md_file)
                            else:
                                logger.info(f"创建新prompt记录: 版本={version}, 目标={model_target}")
                                new_prompt = Prompt(
                                    version=version,
                                    model_target=model_target,
                                    content=content,
                                    file_path=str(md_file),
                                    description=f"Bias detection prompt v{version} for {model_target}"
                                )
                                session.add(new_prompt)
                    
                    # 提交事务
                    session.commit()
                    logger.info("所有prompt文件同步完成")
                
                logger.info("同步Prompt文件完成")
                return {"status": "success", "message": "Prompt同步完成"}
            except Exception as e:
                logger.error(f"直接同步prompt文件失败: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"同步Prompt文件失败: {str(e)}")
        else:
            logger.warning(f"路径验证: {prompt_dir_path} 不存在或不是目录")
    else:
        logger.warning("没有提供prompt_dir参数或参数为空")
    
    try:
        # 创建PromptManager之前记录更多信息
        # 使用顶部已导入的os模块 (不要重复导入)
        env_prompt_dir = os.environ.get("ACOLYTE_PROMPT_DIR")
        logger.info(f"环境变量ACOLYTE_PROMPT_DIR: {env_prompt_dir}")
        logger.info(f"最终传递给PromptManager的prompt_dir: {prompt_dir}")
        
        # 创建prompt管理器并强制传入路径
        prompt_manager = PromptManager(prompt_dir=prompt_dir)
        # 添加手动验证
        logger.info(f"PromptManager实例创建后的prompt_dir: {prompt_manager.prompt_dir}")
        
        # 扫描prompt目录查看是否有文件
        # 使用顶部已导入的os模块
        if os.path.exists(prompt_manager.prompt_dir):
            files = os.listdir(prompt_manager.prompt_dir)
            logger.info(f"PromptManager.prompt_dir中的文件: {files}")
        else:
            logger.warning(f"PromptManager.prompt_dir不存在: {prompt_manager.prompt_dir}")
            
        result = prompt_manager.sync_prompt_files_to_db()
        logger.info("同步Prompt文件完成")
        return {"status": "success", "message": "Prompt同步完成"}
    except Exception as e:
        logger.error(f"同步Prompt文件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"同步Prompt文件失败: {str(e)}")