"""
API路由定义

使用FastAPI定义API端点，处理请求和响应，但将业务逻辑委托给服务层。
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from acolyte.core.db.database import db
from acolyte.core.db.models import LlmRole, ProcessingMode, Task, TaskResult
from acolyte.core.services import LlmService, PromptService, TaskService
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
        from_attributes = True


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
        from_attributes = True


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
        from_attributes = True


class PromptCreate(BaseModel):
    version: str
    model_target: str = "general"
    content: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    is_active: bool = True


class PromptUpdate(BaseModel):
    version: Optional[str] = None
    model_target: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    file_path: Optional[str] = None
    is_active: Optional[bool] = None


class PromptResponse(BaseModel):
    id: int
    version: str
    model_target: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    content: Optional[str] = None
    file_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# LLM配置路由
@router.post("/llms", response_model=LlmConfigResponse)
async def create_llm(llm_config: LlmConfigCreate):
    """创建新的LLM配置"""
    logger.info(f"API请求: 创建LLM配置, 名称={llm_config.name}, 模型={llm_config.model_name}")

    llm_service = LlmService()
    result = await llm_service.add_llm(llm_config.dict())

    if not result.get("success", False):
        error_message = result.get("error", "创建LLM配置失败")
        logger.error(f"API错误: 创建LLM配置失败, {error_message}")
        raise HTTPException(status_code=500, detail=error_message)

    logger.info(f"API响应: LLM配置创建成功, ID={result.get('id')}, 名称={result.get('name')}")
    return result


@router.get("/llms", response_model=List[LlmConfigResponse])
async def get_llms(role: Optional[LlmRole] = None, is_default: Optional[bool] = None):
    """获取LLM配置列表"""
    logger.info(f"API请求: 获取LLM配置列表, 角色={role}, 是否默认={is_default}")

    llm_service = LlmService()
    result = await llm_service.get_llms(role=role.value if role else None, is_default=is_default)

    if not result.get("success", False):
        error_message = result.get("error", "获取LLM配置列表失败")
        logger.error(f"API错误: 获取LLM配置列表失败, {error_message}")
        raise HTTPException(status_code=500, detail=error_message)

    llms = result.get("llms", [])
    logger.info(f"API响应: 成功获取LLM配置列表, 数量={len(llms)}")
    return llms


@router.get("/llms/{llm_id}", response_model=LlmConfigResponse)
async def get_llm(llm_id: int):
    """获取特定LLM配置"""
    logger.info(f"API请求: 获取LLM配置, ID={llm_id}")

    llm_service = LlmService()
    result = await llm_service.get_llm(llm_id)

    if not result.get("success", False):
        error_message = result.get("error", "获取LLM配置失败")
        status_code = 404 if "不存在" in error_message else 500
        logger.error(
            f"API错误: 获取LLM配置失败, ID={llm_id}, 错误={error_message}, 状态码={status_code}"
        )
        raise HTTPException(status_code=status_code, detail=error_message)

    logger.info(f"API响应: 成功获取LLM配置, ID={result.get('id')}, 名称={result.get('name')}")
    return result


@router.put("/llms/{llm_id}", response_model=LlmConfigResponse)
async def update_llm(llm_id: int, llm_config: LlmConfigUpdate):
    """更新LLM配置"""
    logger.info(
        f"API请求: 更新LLM配置, ID={llm_id}, "
        f"更新字段={list(llm_config.dict(exclude_unset=True).keys())}"
    )

    llm_service = LlmService()
    result = await llm_service.update_llm(llm_id, llm_config.dict(exclude_unset=True))

    if not result.get("success", False):
        error_message = result.get("error", "更新LLM配置失败")
        status_code = 404 if "不存在" in error_message else 500
        logger.error(
            f"API错误: 更新LLM配置失败, ID={llm_id}, 错误={error_message}, 状态码={status_code}"
        )
        raise HTTPException(status_code=status_code, detail=error_message)

    logger.info(f"API响应: LLM配置更新成功, ID={result.get('id')}, 名称={result.get('name')}")
    return result


@router.delete("/llms/{llm_id}")
async def delete_llm(llm_id: int):
    """删除LLM配置"""
    logger.info(f"API请求: 删除LLM配置, ID={llm_id}")

    llm_service = LlmService()
    result = await llm_service.delete_llm(llm_id)

    if not result.get("success", False):
        error_message = result.get("error", "删除LLM配置失败")
        status_code = 404 if "不存在" in error_message else 500
        logger.error(
            f"API错误: 删除LLM配置失败, ID={llm_id}, 错误={error_message}, 状态码={status_code}"
        )
        raise HTTPException(status_code=status_code, detail=error_message)

    logger.info(f"API响应: LLM配置删除成功, ID={llm_id}")
    return {"status": "success", "message": "LLM配置已删除"}


@router.post("/llms/{llm_id}/test")
async def test_llm_connection(llm_id: int):
    """测试LLM连接"""
    logger.info(f"API请求: 测试LLM连接, ID={llm_id}")

    llm_service = LlmService()
    result = await llm_service.test_connection(llm_id)

    success = result.get("success", False)
    if success:
        logger.info(f"API响应: LLM连接测试成功, ID={llm_id}, 状态={result.get('status')}")
    else:
        logger.error(f"API错误: LLM连接测试失败, ID={llm_id}, 消息={result.get('message')}")

    return result


@router.post("/llms/{llm_id}/set-default")
async def set_default_llm(llm_id: int):
    """设置指定LLM为默认"""
    logger.info(f"API请求: 设置LLM为默认, ID={llm_id}")

    llm_service = LlmService()
    result = await llm_service.set_default_llm(llm_id)

    if not result.get("success", False):
        error_message = result.get("error", "设置默认LLM失败")
        status_code = 404 if "不存在" in error_message else 500
        logger.error(
            f"API错误: 设置默认LLM失败, ID={llm_id}, 错误={error_message}, 状态码={status_code}"
        )
        raise HTTPException(status_code=status_code, detail=error_message)

    logger.info(f"API响应: 成功设置默认LLM, ID={llm_id}, 名称={result.get('name')}")
    return result


# 任务路由
@router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskCreate):
    """创建新任务"""
    logger.info(
        f"API请求: 创建任务, 处理模式={task_data.processing_mode}, "
        f"内容长度={len(task_data.content)}字符"
    )

    task_service = TaskService()
    result = await task_service.create_task(task_data.dict())

    if not result.get("success", False):
        error_message = result.get("error", "创建任务失败")
        logger.error(f"API错误: 创建任务失败, 错误={error_message}")
        raise HTTPException(status_code=500, detail=error_message)

    logger.info(f"API响应: 任务创建成功, ID={result.get('id')}, 状态={result.get('status')}")
    return result


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(status: Optional[str] = None, skip: int = 0, limit: int = 100):
    """获取任务列表"""
    task_service = TaskService()
    result = await task_service.get_tasks(status=status, skip=skip, limit=limit)

    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "获取任务列表失败"))

    return result.get("tasks", [])


@router.delete("/tasks")
async def clear_tasks(confirm: bool = False, status: Optional[str] = None):
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
        "count": result.get("count", 0),
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
async def get_task_results(task_id: int, include_raw_response: bool = False):
    """获取任务结果"""
    task_service = TaskService()
    result = await task_service.get_task_results(task_id, include_raw_response)

    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "获取任务结果失败"))

    return result.get("results", [])


@router.get("/tasks/{task_id}/final-result", response_model=TaskResultResponse)
async def get_task_final_result(task_id: int, include_raw_response: bool = False):
    """获取任务最终结果"""
    logger.info(f"API请求: 获取任务最终结果, ID={task_id}, 包含原始响应={include_raw_response}")

    async def _get_final_result(session: Session):
        task = session.query(Task).filter_by(id=task_id).first()
        if not task:
            logger.warning(f"任务不存在: ID={task_id}")
            return None

        if not task.final_result_id:
            logger.warning(f"任务无最终结果: ID={task_id}")
            return None

        final_result = session.query(TaskResult).filter_by(id=task.final_result_id).first()
        if not final_result:
            logger.warning(f"最终结果不存在: ID={task.final_result_id}")
            return None

        return final_result.to_dict(include_raw_response=include_raw_response)

    try:
        from acolyte.core.db.session import run_in_session

        final_result = await run_in_session(_get_final_result)

        if not final_result:
            logger.warning(f"API响应: 任务无最终结果, ID={task_id}")
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 无最终结果")

        logger.info(f"API响应: 成功获取任务最终结果, ID={task_id}, 结果ID={final_result['id']}")
        return final_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API错误: 获取任务最终结果失败, ID={task_id}, 错误={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务最终结果失败: {str(e)}") from e


# 配置路由
@router.post("/config/import")
async def import_config(name: Optional[str] = None):
    """从配置文件导入LLM配置到数据库

    Args:
        name: 可选，指定要导入的LLM名称
    """
    logger.info(f"API请求: 从配置文件导入LLM配置{' (' + name + ')' if name else ''}")

    try:
        from acolyte.core.llm.config import import_llm_config_from_file

        imported_llms = import_llm_config_from_file(llm_name=name)

        if not imported_llms:
            logger.warning(f"未找到可导入的LLM配置{' (' + name + ')' if name else ''}")
            return {
                "status": "success",
                "message": f"未找到可导入的LLM配置{' (' + name + ')' if name else ''}",
                "llms": [],
            }

        logger.info(f"成功导入 {len(imported_llms)} 个LLM配置")
        return {
            "status": "success",
            "message": f"成功导入 {len(imported_llms)} 个LLM配置",
            "llms": imported_llms,
        }
    except Exception as e:
        logger.error(f"导入LLM配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入LLM配置失败: {str(e)}") from e


@router.post("/config/export")
async def export_config():
    """将数据库中的LLM配置导出到配置文件"""
    logger.info("API请求: 导出LLM配置到配置文件")

    try:
        from acolyte.core.llm.config import export_llm_config_to_file

        success = export_llm_config_to_file()

        if success:
            logger.info("LLM配置导出成功")
            return {"status": "success", "message": "LLM配置已成功导出到配置文件"}
        else:
            logger.error("LLM配置导出失败")
            raise HTTPException(status_code=500, detail="LLM配置导出失败")
    except Exception as e:
        logger.error(f"导出LLM配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出LLM配置失败: {str(e)}") from e


# 提示词路由
@router.get("/prompts", response_model=List[PromptResponse])
async def get_prompts(model_target: Optional[str] = None, version: Optional[str] = None):
    """获取提示词列表"""
    prompt_service = PromptService()
    result = await prompt_service.get_prompts(model_target=model_target, version=version)

    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "获取提示词列表失败"))

    return result.get("prompts", [])


@router.get("/prompts/latest", response_model=PromptResponse)
async def get_latest_prompt(model_target: Optional[str] = None):
    """获取最新版本的提示词"""
    prompt_service = PromptService()
    result = await prompt_service.get_latest_prompt(model_target=model_target)

    if not result.get("success", False):
        status_code = 404 if "未找到" in result.get("error", "") else 500
        raise HTTPException(
            status_code=status_code, detail=result.get("error", "获取最新提示词失败")
        )

    return result


@router.get("/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: int):
    """获取特定提示词"""
    prompt_service = PromptService()
    result = await prompt_service.get_prompt(prompt_id)

    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "获取提示词失败"))

    return result


@router.post("/prompts", response_model=PromptResponse)
async def create_prompt(prompt_data: PromptCreate):
    """创建新提示词"""
    prompt_service = PromptService()
    result = await prompt_service.create_prompt(prompt_data.dict())

    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "创建提示词失败"))

    return result


@router.put("/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(prompt_id: int, prompt_data: PromptUpdate):
    """更新提示词"""
    prompt_service = PromptService()
    result = await prompt_service.update_prompt(prompt_id, prompt_data.dict(exclude_unset=True))

    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "更新提示词失败"))

    return result


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: int, delete_file: bool = False):
    """删除提示词"""
    prompt_service = PromptService()
    result = await prompt_service.delete_prompt(prompt_id, delete_file=delete_file)

    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(status_code=status_code, detail=result.get("error", "删除提示词失败"))

    return {
        "status": "success",
        "message": f"提示词 {prompt_id} 已删除",
        "file_deleted": result.get("file_deleted", False),
    }


class PromptSyncRequest(BaseModel):
    prompt_dir: Optional[str] = None


@router.post("/prompts/sync")
async def sync_prompts(request_data: Optional[PromptSyncRequest] = None):
    """同步提示词文件到数据库

    Args:
        request_data: 可选的请求数据，可包含prompt_dir参数
    """
    logger.info("API请求: 同步提示词文件到数据库")

    # 提取prompt_dir参数（如果存在）
    prompt_dir = None
    if request_data:
        prompt_dir = request_data.prompt_dir
        if prompt_dir:
            logger.info(f"使用指定的prompt_dir: {prompt_dir}")

    prompt_service = PromptService()
    result = await prompt_service.sync_prompts(prompt_dir=prompt_dir)

    if not result.get("success", False):
        logger.error(f"同步提示词失败: {result.get('error', '未知错误')}")
        raise HTTPException(status_code=500, detail=result.get("error", "同步提示词失败"))

    logger.info(f"提示词同步成功: {result.get('count', 0)} 个提示词")
    return {
        "status": "success",
        "message": result.get("message", "提示词同步成功"),
        "count": result.get("count", 0),
    }


@router.patch("/prompts/{prompt_id}/status")
async def set_prompt_status(prompt_id: int, is_active: bool):
    """设置提示词活跃状态"""
    prompt_service = PromptService()
    result = await prompt_service.set_active_status(prompt_id, is_active)

    if not result.get("success", False):
        status_code = 404 if "不存在" in result.get("error", "") else 500
        raise HTTPException(
            status_code=status_code, detail=result.get("error", "设置提示词状态失败")
        )

    return {
        "status": "success",
        "message": result.get("message", f"提示词状态已设置为 {'活跃' if is_active else '非活跃'}"),
        "is_active": is_active,
    }
