"""
Acolyte应用启动入口
"""
import uvicorn

from acolyte.api.app import app as api_app


def main():
    """启动API服务"""
    uvicorn.run(
        "acolyte.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()