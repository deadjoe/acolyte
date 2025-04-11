"""
Acolyte安装配置
"""

import re

from setuptools import find_packages, setup

# 从__init__.py文件中提取版本号
with open("acolyte/__init__.py", "r", encoding="utf-8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
    name="acolyte",
    version=version,
    description="内容分析评估系统",
    author="Acolyte Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn>=0.21.0",
        "sqlalchemy>=2.0.0",
        "httpx>=0.24.0",
        "click>=8.1.3",
        "rich>=13.3.4",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "ruff>=0.0.260",
        ],
    },
    entry_points={
        "console_scripts": [
            "acolyte=acolyte.cli.main:cli",
        ],
    },
)
