# Acolyte 测试指南

本目录包含 Acolyte 项目的测试代码。

## 测试结构

测试代码按照以下结构组织：

```
tests/
├── unit/                  # 单元测试
│   ├── core/              # 核心模块测试
│   │   ├── db/            # 数据库模块测试
│   │   ├── llm/           # LLM模块测试
│   │   └── task/          # 任务处理模块测试
│   └── ...
├── integration/           # 集成测试（未来添加）
└── e2e/                   # 端到端测试（未来添加）
```

## 运行测试

### 安装测试依赖

```bash
pip install pytest pytest-asyncio pytest-cov
```

### 运行所有测试

```bash
./run_tests.sh
```

或者使用 pytest 直接运行：

```bash
python -m pytest tests/
```

### 运行特定测试

```bash
# 运行特定测试文件
python -m pytest tests/unit/core/llm/test_response_parser.py

# 运行特定测试类
python -m pytest tests/unit/core/llm/test_response_parser.py::TestResponseParser

# 运行特定测试方法
python -m pytest tests/unit/core/llm/test_response_parser.py::TestResponseParser::test_extract_scores_standard_format
```

### 生成覆盖率报告

```bash
python -m pytest tests/ --cov=acolyte --cov-report=term --cov-report=html
```

覆盖率报告将生成在 `coverage_html_report` 目录中。

## 测试原则

1. **单元测试**：测试单个组件的功能，使用模拟（mock）隔离依赖
2. **集成测试**：测试多个组件的交互
3. **端到端测试**：测试整个系统的功能

## 编写测试的最佳实践

1. 每个测试方法只测试一个功能点
2. 使用有意义的测试方法名称，描述被测试的行为
3. 遵循 AAA 模式：Arrange（准备）、Act（执行）、Assert（断言）
4. 使用 pytest fixtures 共享测试设置
5. 为边缘情况和错误情况编写测试
6. 保持测试独立，不依赖于其他测试的执行顺序
