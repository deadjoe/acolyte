# Acolyte 测试指南

## 运行测试

```bash
uv run pytest                # 全部测试 (424 passed)
uv run pytest tests/unit/core/llm/   # 特定模块
uv run pytest -k "test_send_request"  # 按名称筛选
uv run pytest --cov=acolyte --cov-report=html  # 覆盖率
```

## 测试结构

```
tests/
├── conftest.py                 # 全局 fixtures
├── unit/                       # 单元测试
│   ├── api/                    # API 层
│   ├── cli/                    # CLI 层
│   ├── core/                   # 核心模块
│   │   ├── db/                 # 数据库
│   │   ├── llm/                # LLM 客户端
│   │   ├── services/           # 服务层
│   │   ├── task/               # 任务处理
│   │   └── utils/              # 工具函数
│   └── utils/                  # 通用工具
└── texts/                      # 测试用文本
```

## 编写测试

- 每个测试只验证一个行为
- 使用 `pytest fixtures` 共享 setup
- 异步测试添加 `@pytest.mark.asyncio`
- 文件名匹配 `test_*.py`，函数匹配 `test_*`
