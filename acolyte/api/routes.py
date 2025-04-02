"""
API路由定义

使用FastAPI定义API端点，处理请求和响应，但将业务逻辑委托给服务层。
"""
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, root_validator
from sqlalchemy.orm import Session

from acolyte.core.db.database import db
from acolyte.core.db.models import (
    LlmRole, ProcessingMode, TaskStatus
)
from acolyte.core.services.llm_service import LlmService
from acolyte.core.services.task_service import TaskService
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
async def create_llm(llm_config: LlmConfigCreate):
    """创建新的LLM配置"""
    llm_service = LlmService()
    result = await llm_service.add_llm(llm_config.dict())
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "创建LLM配置失败"))
    
    return result


@router.get("/llms", response_model=List[LlmConfigResponse])
async def get_llms(
    role: Optional[LlmRole] = None,
    is_default: Optional[bool] = None
):
    """获取LLM配置列表"""
    llm_service = LlmService()
    result = await llm_service.get_llms(
        role=role.value if role else None,
        is_default=is_default
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "获取LLM配置列表失败"))
    
    return result.get("llms", [])


@router.get("/llms/{llm_id}", response_model=LlmConfigResponse)
async def get_llm(llm_id: int):
    """获取特定LLM配置"""
    llm_service = LlmService()
    result = await llm_service.get_llm(llm_id)
    
    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "获取LLM配置失败"))
    
    return result


@router.put("/llms/{llm_id}", response_model=LlmConfigResponse)
async def update_llm(llm_id: int, llm_config: LlmConfigUpdate):
    """更新LLM配置"""
    llm_service = LlmService()
    result = await llm_service.update_llm(llm_id, llm_config.dict(exclude_unset=True))
    
    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "更新LLM配置失败"))
    
    return result


@router.delete("/llms/{llm_id}")
async def delete_llm(llm_id: int):
    """删除LLM配置"""
    llm_service = LlmService()
    result = await llm_service.delete_llm(llm_id)
    
    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "删除LLM配置失败"))
    
    return {"status": "success", "message": "LLM配置已删除"}


@router.post("/llms/{llm_id}/test")
async def test_llm_connection(llm_id: int):
    """测试LLM连接"""
    llm_service = LlmService()
    result = await llm_service.test_connection(llm_id)
    return result


# 任务路由
@router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate):
    """创建新任务"""
    task_service = TaskService()
    result = await task_service.create_task(task_data.dict())
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "创建任务失败"))
    
    return result


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """获取任务列表"""
    task_service = TaskService()
    result = await task_service.get_tasks(status=status, skip=skip, limit=limit)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "获取任务列表失败"))
    
    return result.get("tasks", [])


@router.delete("/tasks")
async def clear_tasks(
    confirm: bool = False,
    status: Optional[str] = None
):
    """清空所有任务及其关联结果
    
    Args:
        confirm: 必须为True才能执行删除操作
        status: 可选，只删除特定状态的任务
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="必须设置confirm=true参数以确认操作")
    
    task_service = TaskService()
    result = await task_service.clear_tasks(status=status)
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "清空任务失败"))
    
    return {
        "status": "success", 
        "message": result.get("message", "已清空任务"),
        "count": result.get("count", 0)
    }


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    """获取特定任务"""
    task_service = TaskService()
    result = await task_service.get_task(task_id)
    
    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "获取任务失败"))
    
    return result


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """删除特定任务及其关联结果"""
    task_service = TaskService()
    result = await task_service.delete_task(task_id)
    
    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "删除任务失败"))
    
    return {"status": "success", "message": f"任务 {task_id} 已删除"}


@router.get("/tasks/{task_id}/results", response_model=List[TaskResultResponse])
async def get_task_results(
    task_id: int,
    include_raw_response: bool = False
):
    """获取任务结果"""
    task_service = TaskService()
    result = await task_service.get_task_results(task_id, include_raw_response)
    
    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "获取任务结果失败"))
    
    return result.get("results", [])