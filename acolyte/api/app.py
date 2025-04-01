"""
API服务主应用
"""
import json
import os
from datetime import date, datetime
from enum import Enum

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder

from acolyte.api.routes import router
from acolyte.core.db.database import db
from acolyte.core.prompt.manager import PromptManager
from acolyte.utils.logging import get_logger

# 获取API模块日志记录器
logger = get_logger("acolyte.api")


# 自定义JSON编码器，处理datetime, date等类型
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

# 重写默认的JSON响应类
from fastapi.responses import JSONResponse
class FastAPICustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        # 使用自定义编码器编码响应内容
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

# 创建FastAPI应用
app = FastAPI(
    title="Acolyte API",
    description="内容分析评估系统API",
    version="0.1.0",
    default_response_class=FastAPICustomJSONResponse
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有头部
)

# 添加自定义中间件处理响应
from starlette.middleware.base import BaseHTTPMiddleware
class DatetimeHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 记录请求信息
        logger.debug(f"收到请求: {request.method} {request.url.path}")
        
        try:
            # 处理请求
            response = await call_next(request)
            # 记录响应状态
            logger.debug(f"请求处理完成: {request.method} {request.url.path} - 状态码: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"请求处理异常: {request.method} {request.url.path} - {str(e)}", exc_info=True)
            raise

app.add_middleware(DatetimeHandlerMiddleware)

# 包含路由
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行的操作"""
    logger.info("API服务正在启动...")
    
    try:
        # 创建数据库表
        logger.info("正在初始化数据库表...")
        db.create_tables()
        logger.info("数据库表初始化完成")
        
        # 同步Prompt文件到数据库
        logger.info("正在同步Prompt文件到数据库...")
        prompt_manager = PromptManager()
        prompt_manager.sync_prompt_files_to_db()
        logger.info("Prompt文件同步完成")
        
        # 记录PID文件用于服务管理
        pid = os.getpid()
        with open("acolyte_api.pid", "w") as f:
            f.write(str(pid))
        logger.info(f"API服务启动完成，PID: {pid}")
    except Exception as e:
        logger.critical(f"API服务启动失败: {str(e)}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的操作"""
    logger.info("API服务正在关闭...")
    try:
        # 删除PID文件
        if os.path.exists("acolyte_api.pid"):
            os.remove("acolyte_api.pid")
            logger.info("PID文件已删除")
        logger.info("API服务已安全关闭")
    except Exception as e:
        logger.error(f"API服务关闭过程中发生错误: {str(e)}", exc_info=True)


@app.get("/")
async def root():
    """API根路径响应"""
    logger.debug("访问API根路径")
    return {
        "message": "Acolyte内容分析评估系统API",
        "version": "0.1.0",
        "docs_url": "/docs"
    }