"""
API服务主应用
"""
import json
from datetime import date, datetime
from enum import Enum

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder

from acolyte.api.routes import router
from acolyte.core.db.database import db
from acolyte.core.prompt.manager import PromptManager


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
        # 处理请求
        response = await call_next(request)
        
        # 覆盖响应的default方法，用于处理json序列化
        # 这很可能没有效果，因为FastAPI的响应已经被序列化了
        # 但我们可以尝试一下
        return response

app.add_middleware(DatetimeHandlerMiddleware)

# 包含路由
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行的操作"""
    # 创建数据库表
    db.create_tables()
    
    # 同步Prompt文件到数据库
    prompt_manager = PromptManager()
    prompt_manager.sync_prompt_files_to_db()


@app.get("/")
async def root():
    """API根路径响应"""
    return {
        "message": "Acolyte内容分析评估系统API",
        "version": "0.1.0",
        "docs_url": "/docs"
    }