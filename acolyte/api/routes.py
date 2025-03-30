"""
API路由定义
"""
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, root_validator
from sqlalchemy.orm import Session

from acolyte.core.db.database import db
from acolyte.core.db.models import (
    LlmConfig, LlmRole, ProcessingMode, Prompt, Task, TaskResult
)
from acolyte.core.llm.manager import LlmManager
from acolyte.core.prompt.manager import PromptManager
from acolyte.core.task.processor import TaskProcessor


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
    
    # 使用to_dict方法
    return new_llm.to_dict()


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
    llm_manager = LlmManager()
    update_data = llm_config.dict(exclude_unset=True)
    updated_llm = llm_manager.update_llm(llm_id, **update_data)
    if not updated_llm:
        raise HTTPException(status_code=404, detail="LLM配置不存在")
    
    # 使用to_dict方法
    return updated_llm.to_dict()


@router.delete("/llms/{llm_id}")
def delete_llm(llm_id: int, session: Session = Depends(get_db)):
    """删除LLM配置"""
    llm_manager = LlmManager()
    success = llm_manager.delete_llm(llm_id)
    if not success:
        raise HTTPException(status_code=404, detail="LLM配置不存在")
    return {"status": "success", "message": "LLM配置已删除"}


@router.post("/llms/{llm_id}/test")
def test_llm_connection(llm_id: int, session: Session = Depends(get_db)):
    """测试LLM连接"""
    llm_manager = LlmManager()
    result = llm_manager.test_connection(llm_id=llm_id)
    return result


# 任务路由
@router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate, session: Session = Depends(get_db)):
    """创建新任务"""
    # 创建任务
    new_task = Task(
        content=task_data.content,
        processing_mode=task_data.processing_mode,
        prompt_id=task_data.prompt_id
    )
    session.add(new_task)
    session.flush()

    # 如果指定了LLM，关联任务与LLM
    if task_data.llm_ids:
        llms = session.query(LlmConfig).filter(LlmConfig.id.in_(task_data.llm_ids)).all()
        new_task.llm_configs.extend(llms)

    session.commit()

    # 异步处理任务
    task_processor = TaskProcessor()
    # 这里使用创建的任务ID启动异步处理，不等待结果
    import asyncio
    asyncio.create_task(task_processor.process_task(new_task.id))

    return new_task


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
        query = query.filter(Task.status == status)
    
    # 获取查询结果
    results = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    
    # 使用to_dict转换
    return [task.to_dict() for task in results]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, session: Session = Depends(get_db)):
    """获取特定任务"""
    task = session.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.to_dict()


@router.get("/tasks/{task_id}/results", response_model=List[TaskResultResponse])
def get_task_results(
    task_id: int,
    include_raw_response: bool = False,
    session: Session = Depends(get_db)
):
    """获取任务结果"""
    task = session.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    results = session.query(TaskResult).filter(TaskResult.task_id == task_id).all()
    
    # 使用to_dict方法转换，并控制是否包含原始响应
    return [r.to_dict(include_raw_response=include_raw_response) for r in results]


@router.get("/tasks/{task_id}/final-result", response_model=TaskResultResponse)
def get_task_final_result(
    task_id: int,
    include_raw_response: bool = True,
    session: Session = Depends(get_db)
):
    """获取任务最终结果"""
    task = session.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.final_result_id:
        final_result = session.query(TaskResult).filter(TaskResult.id == task.final_result_id).first()
        return final_result.to_dict(include_raw_response=include_raw_response)
    
    # 如果没有最终结果但任务已完成，查找是否有评议结果
    if task.status == "completed":
        review_result = session.query(TaskResult).filter(
            TaskResult.task_id == task_id,
            TaskResult.is_review_result == True
        ).first()
        
        if review_result:
            return review_result.to_dict(include_raw_response=include_raw_response)
    
    raise HTTPException(status_code=404, detail="任务最终结果不存在")


# 配置路由
@router.post("/config/export")
def export_config():
    """导出LLM配置到配置文件"""
    from acolyte.core.llm.config import export_llm_config_to_file
    success = export_llm_config_to_file()
    if success:
        return {"status": "success", "message": "配置已成功导出到文件"}
    else:
        raise HTTPException(status_code=500, detail="导出配置文件失败")


@router.post("/config/import")
def import_config(name: Optional[str] = None):
    """从配置文件导入LLM配置"""
    from acolyte.core.llm.config import import_llm_config_from_file
    try:
        imported_llms = import_llm_config_from_file(name, verbose=False)
        if imported_llms:
            return {
                "status": "success", 
                "message": f"已导入 {len(imported_llms)} 个LLM配置",
                "llms": imported_llms
            }
        else:
            return {"status": "warning", "message": "未导入任何LLM配置"}
    except Exception as e:
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
    prompt_manager = PromptManager()
    prompt_manager.sync_prompt_files_to_db()
    return {"status": "success", "message": "Prompt同步完成"}