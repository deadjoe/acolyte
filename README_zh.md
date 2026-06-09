<p align="center">
  <img src="logo.png" alt="Acolyte Logo" width="200"/>
</p>

# Acolyte

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Backend: uv](https://img.shields.io/badge/Backend-uv-purple)](https://github.com/astral-sh/uv)
[![Frontend: bun](https://img.shields.io/badge/Frontend-bun-orange)](https://bun.sh)

*[English](README.md) | [中文](README_zh.md)*

Acolyte 是一个内容分析评估系统，用于检测文本中的偏见、误导性内容和隐藏意图。支持 Web 界面、CLI 和 API 三种方式提交内容，由单个或多个 LLM 进行分析。

## 功能特性

- **Web 界面、CLI、API** 三种访问方式
- **多 LLM 支持**：Anthropic Claude、OpenAI、Google Gemini
- **分析模式**：单 LLM、多 LLM 并行、多 LLM 评议投票
- **量化评分**：偏见指数、误导性指数、隐藏意图指数、可信度分数
- **历史记录**：任务存储与结果可视化
- **技术栈**：React + TypeScript + Tailwind CSS v4 + shadcn UI

## 快速开始

### 环境要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- [bun](https://bun.sh)

### 后端

```bash
uv sync --extra dev   # 安装全部依赖
uv run acolyte        # 启动 API 服务 (http://localhost:8000)
```

### 前端

```bash
cd acolyte/web
bun install           # 安装依赖
bun run dev           # 启动开发服务器 (http://localhost:5173)
```

### CLI

```bash
uv run acolyte analyze content.txt --mode=single
uv run acolyte history list --limit=5
uv run acolyte config add-llm -n "My LLM" -k "sk-..." -u "https://api.openai.com/v1" -m "gpt-4o"
```

## 项目结构

```
acolyte/
├── acolyte/              # 后端 Python 包
│   ├── core/             # LLM、数据库、任务处理
│   ├── api/              # FastAPI 路由
│   ├── cli/              # CLI 命令行工具
│   └── web/              # React + Vite 前端
├── tests/                # Python 测试 (424 passed)
├── prompt/               # 偏见检测提示词模板
├── tools/                # 工具脚本
├── pyproject.toml        # 项目配置 + 依赖声明
├── uv.lock               # 锁定依赖版本
└── Makefile              # 快捷命令
```

## 配置

配置文件默认位置 `~/.config/acolyte/config.json`（可通过 `ACOLYTE_CONFIG_PATH` 环境变量覆盖）：

```json
{
  "database_url": "sqlite:///acolyte.db",
  "default_prompt_version": "",
  "llm_configs": [
    {
      "name": "Claude-Sonnet",
      "api_key": "your-api-key",
      "base_url": "https://api.anthropic.com/v1",
      "model_name": "claude-sonnet-4-20250514",
      "role": "normal",
      "is_default": true
    }
  ]
}
```

## 开发

```bash
# 后端
uv sync --extra dev     # 安装开发依赖
uv run pytest           # 运行测试 (424 passed)
uv run ruff check .     # 代码检查
uv run black .          # 代码格式化

# 前端
cd acolyte/web
bun run dev             # 开发服务器
bun run build           # 生产构建
bun run test            # 运行测试 (26 passed)
bun run lint            # ESLint

# 快捷命令（项目根目录）
make test               # 后端测试
make web-test           # 前端测试
make lint               # 后端代码检查
make clean              # 清理构建产物
```

## 提示词模板

偏见检测提示词位于 `prompt/` 目录，命名格式为 `bias-detection-prompt_vX.Y[_modelname].md`。添加新提示词后运行：

```bash
uv run acolyte config sync-prompts
```

## License

MIT
