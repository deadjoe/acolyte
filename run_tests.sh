#!/bin/bash
# 运行单元测试脚本

# 设置环境变量
export PYTHONPATH=.

# 运行所有测试
echo "运行所有单元测试..."
uv run -m pytest tests/unit -v

# 运行特定模块测试
echo "运行ResponseParser测试..."
uv run -m pytest tests/unit/core/llm/test_response_parser.py -v

echo "运行数据库模型测试..."
uv run -m pytest tests/unit/core/db/test_models.py -v

echo "运行任务处理器测试..."
uv run -m pytest tests/unit/core/task/test_base_processor.py -v

# 生成覆盖率报告
echo "生成测试覆盖率报告..."
uv run -m pytest tests/unit --cov=acolyte --cov-report=term --cov-report=html

echo "测试完成！"
