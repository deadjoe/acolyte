#!/bin/bash
# 运行单元测试脚本

# 设置环境变量
export PYTHONPATH=.

# 运行所有测试
echo "运行所有单元测试..."
uv run -m pytest tests/unit -v

# 运行API相关测试
echo "运行API测试..."
uv run -m pytest tests/unit/api/ -v

# 运行CLI相关测试
echo "运行CLI测试..."
uv run -m pytest tests/unit/cli/ -v

# 运行核心模块测试
echo "运行数据库模型测试..."
uv run -m pytest tests/unit/core/db/test_models.py -v

echo "运行LLM相关测试..."
uv run -m pytest tests/unit/core/llm/ -v

echo "运行服务层测试..."
uv run -m pytest tests/unit/core/services/ -v

echo "运行任务处理器测试..."
uv run -m pytest tests/unit/core/task/ -v

echo "运行HTTP工具测试..."
uv run -m pytest tests/unit/core/utils/test_http.py -v
uv run -m pytest tests/unit/utils/test_http_utils.py -v

# 运行主模块测试
echo "运行主模块测试..."
uv run -m pytest tests/unit/test_main.py -v

# 生成覆盖率报告
echo "生成测试覆盖率报告..."
uv run -m pytest tests/unit --cov=acolyte --cov-report=term --cov-report=html

echo "测试完成！"
