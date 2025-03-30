"""
API服务主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from acolyte.api.routes import router
from acolyte.core.db.database import db
from acolyte.core.prompt.manager import PromptManager

# 创建FastAPI应用
app = FastAPI(
    title="Acolyte API",
    description="内容分析评估系统API",
    version="0.1.0",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有头部
)

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