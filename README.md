<p align="center">
  <img src="logo.png" alt="Acolyte Logo" width="200"/>
</p>

# Acolyte

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-orange.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![LLM: Claude](https://img.shields.io/badge/LLM-Claude-blueviolet)](https://www.anthropic.com/)
[![LLM: OpenAI](https://img.shields.io/badge/LLM-OpenAI-lightgrey)](https://openai.com/)
[![LLM: Gemini](https://img.shields.io/badge/LLM-Gemini-blue)](https://ai.google.dev/)
[![Package Manager: uv](https://img.shields.io/badge/Package%20Manager-uv-purple)](https://github.com/astral-sh/uv)
[![Status: Alpha](https://img.shields.io/badge/Status-Alpha-red)]()

Acolyte是一个内容分析评估系统，支持通过Web界面、CLI和API三种方式提交内容，由单个或多个LLM进行分析评估，特别关注内容的偏见、误导性和隐藏意图等方面。

## 功能特点

- 支持Web、CLI和API三种使用方式
- 支持单个或多个LLM同时评估内容
- 提供多LLM评议汇总功能
- 保存历史任务记录
- 支持多种LLM供应商（Anthropic Claude、OpenAI、Google Gemini）
- 支持LLM配置管理
- 基于评估框架的内容分析
- 内容分析包括偏见检测、误导性内容检测和隐藏意图检测
- 提供量化评分系统，包括偏见指数、误导性指数、隐藏意图指数和综合可信度分数

## 安装

使用uv创建虚拟环境并安装依赖：

```bash
# 创建虚拟环境
uv venv

# 安装依赖
uv pip install -r requirements.txt

# 开发模式安装
uv pip install -e .
```

## 使用方法

### 启动API服务

```bash
uv run -m acolyte.main
```

### 使用CLI工具

```bash
# 分析内容
uv run -m acolyte.cli.main analyze content.txt --mode=single

# 使用配置文件中指定的LLM
uv run -m acolyte.cli.main analyze content.txt --llm-config "Claude-3"

# 查看历史记录
uv run -m acolyte.cli.main history --limit=5

# 显示特定任务结果
uv run -m acolyte.cli.main show 123 --raw

# 添加LLM配置
uv run -m acolyte.cli.main config add-llm -n "Claude-3" -k "your-api-key" -u "https://api.anthropic.com" -m "claude-3-opus-20240229"

# 导出LLM配置到文件
uv run -m acolyte.cli.main config export-config

# 从配置文件导入LLM配置
uv run -m acolyte.cli.main config import-config --name "Claude-3"

# 列出LLM配置
uv run -m acolyte.cli.main config list-llms

# 列出Prompt配置
uv run -m acolyte.cli.main config list-prompts

# 显示特定Prompt内容
uv run -m acolyte.cli.main config show-prompt 1

# 同步Prompt文件
uv run -m acolyte.cli.main config sync-prompts

# 删除LLM配置
uv run -m acolyte.cli.main config delete-llm 1
```

### 配置文件

配置文件默认位于 `~/.config/acolyte/config.json`，可以通过环境变量 `ACOLYTE_CONFIG_PATH` 指定其他位置。配置文件示例：

```json
{
  "database_url": "sqlite:///acolyte.db",
  "default_prompt_version": "",
  "llm_configs": [
    {
      "name": "Claude-Sonnet",
      "api_key": "your-anthropic-api-key",
      "base_url": "https://api.anthropic.com/v1",
      "model_name": "claude-3-7-sonnet-latest",
      "description": "Anthropic Claude 3.7 Sonnet",
      "role": "normal",
      "is_default": true
    },
    {
      "name": "GPT-4o",
      "api_key": "your-openai-api-key",
      "base_url": "https://api.openai.com/v1",
      "model_name": "gpt-4o",
      "description": "OpenAI GPT-4o",
      "role": "normal",
      "is_default": false
    },
    {
      "name": "Gemini-Pro",
      "api_key": "your-google-api-key",
      "base_url": "https://generativelanguage.googleapis.com/v1beta",
      "model_name": "gemini-2.5-pro",
      "description": "Google Gemini 2.5 Pro",
      "role": "normal",
      "is_default": false
    },
    {
      "name": "Claude-Reviewer",
      "api_key": "your-anthropic-api-key",
      "base_url": "https://api.anthropic.com/v1",
      "model_name": "claude-3-7-sonnet-latest",
      "description": "Claude 3.7 Sonnet as reviewer",
      "role": "reviewer",
      "is_default": false
    }
  ]
}
```

## 开发注意事项

### 配置文件格式
配置文件必须使用以下格式：
```json
{
  "database_url": "sqlite:///acolyte.db",
  "default_prompt_version": "",
  "llm_configs": [...]
}
```

不要使用旧的嵌套格式 `{"llms": {...}}`，这将导致配置无法正确加载。如果遇到此问题，可以使用 `tools/convert_config.py` 脚本转换格式。

### 数据库会话管理
使用SQLAlchemy时，确保不在会话外使用数据库对象，特别是在异步操作中。始终在会话上下文中获取和操作数据库对象。

### LLM API URL格式
不同的LLM供应商有不同的URL格式要求：
- Anthropic Claude: `https://api.anthropic.com/v1`
- OpenAI: `https://api.openai.com/v1`
- Google Gemini: `https://generativelanguage.googleapis.com/v1beta`

### 检测模板提示词
系统使用的偏见检测提示词位于 `prompt/` 目录，支持模型特定版本。添加新提示词后，需要运行 `config sync-prompts` 命令同步到数据库。命名格式为 `bias-detection-prompt_vX.Y.md` 或 `bias-detection-prompt_vX.Y_modelname.md`。

### 工具脚本
项目在 `tools/` 目录下包含一些有用的工具脚本：
- `convert_config.py`: 转换配置文件格式
- `check_prompts.py`: 检查数据库中的prompt记录
- `direct_task_process.py`: 直接处理任务，绕过API
- `show_result.py`: 显示任务结果内容

### 启动顺序
1. 启动API服务器：`uv run -m acolyte.main`
2. 导入LLM配置：`uv run -m acolyte.cli.main config import-config`
3. 同步提示词：`uv run -m acolyte.cli.main config sync-prompts`
4. 开始使用系统分析内容