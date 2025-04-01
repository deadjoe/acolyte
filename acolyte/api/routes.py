"""
API路由定义
"""
import asyncio
import traceback
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, root_validator
from sqlalchemy.orm import Session

from acolyte.core.db.database import db
from acolyte.core.db.models import (
    LlmConfig, LlmRole, ProcessingMode, Prompt, Task, TaskResult
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

        # 异步处理任务
        logger.info(f"启动异步任务处理: ID={new_task.id}")
        task_processor = TaskProcessor()
        # 这里使用创建的任务ID启动异步处理，不等待结果
        asyncio.create_task(task_processor.process_task(new_task.id))

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
    query = session.query(Task)
    if status:
        # 将字符串状态转换为枚举值
        from acolyte.core.db.models import TaskStatus
        try:
            status_enum = TaskStatus(status)
            query = query.filter(Task.status == status_enum)
        except ValueError:
            # 如果无效的状态值，返回空列表
            return []
    
    # 获取查询结果
    results = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    
    # 使用to_dict转换
    return [task.to_dict() for task in results]


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
    task = session.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.to_dict()


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_db)):
    """删除特定任务及其关联结果"""
    task = session.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 先删除关联的任务结果
    session.query(TaskResult).filter(TaskResult.task_id == task_id).delete()
    
    # 再删除任务本身
    session.delete(task)
    session.commit()
    
    return {"status": "success", "message": f"任务 {task_id} 已删除"}


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


@router.post("/prompts/sync")
def sync_prompts():
    """同步Prompt文件到数据库"""
    logger.info("开始同步Prompt文件到数据库")
    try:
        prompt_manager = PromptManager()
        result = prompt_manager.sync_prompt_files_to_db()
        logger.info("同步Prompt文件完成")
        return {"status": "success", "message": "Prompt同步完成"}
    except Exception as e:
        logger.error(f"同步Prompt文件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"同步Prompt文件失败: {str(e)}")