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

Acolyte is a content analysis and evaluation system that supports content submission through Web interface, CLI, and API. The system analyzes content using single or multiple LLMs, with a special focus on detecting bias, misleading content, and hidden intent in text.

## Key Features

- Three access methods: Web interface, CLI, and API
- Support for evaluation using single or multiple LLMs simultaneously
- Multi-LLM review aggregation functionality
- Historical task record storage and retrieval
- Support for multiple LLM providers (Anthropic Claude, OpenAI, Google Gemini)
- LLM configuration management
- Framework-based content analysis
- Content analysis including bias detection, misleading content detection, and hidden intent detection
- Quantitative scoring system with bias index, misleading index, hidden intent index, and overall credibility score
- Comprehensive logging system with configurable levels and output destinations

## Installation

Create a virtual environment and install dependencies using uv:

```bash
# Create virtual environment
uv venv

# Install dependencies
uv pip install -r requirements.txt

# Install in development mode
uv pip install -e .
```

## Usage

### Starting the API Service

```bash
# Basic start
uv run -m acolyte.main

# Start with custom log level
ACOLYTE_LOG_LEVEL=debug uv run -m acolyte.main

# Enable file logging
ACOLYTE_LOG_TO_FILE=1 uv run -m acolyte.main

# Specify log directory
ACOLYTE_LOG_DIR=/path/to/logs ACOLYTE_LOG_TO_FILE=1 uv run -m acolyte.main

# Specify custom port
ACOLYTE_PORT=8080 uv run -m acolyte.main
```

### Using the CLI Tool

```bash
# Analyze content
uv run -m acolyte.cli.main analyze content.txt --mode=single

# Use a specific LLM from the configuration file
uv run -m acolyte.cli.main analyze content.txt --llm-config "Claude-3"

# Use multiple LLMs with review
uv run -m acolyte.cli.main analyze content.txt --mode=multiple_with_review --llm 1 --llm 2

# View history
uv run -m acolyte.cli.main history list --limit=5

# Show specific task results
uv run -m acolyte.cli.main show 123 --raw

# Add LLM configuration
uv run -m acolyte.cli.main config add-llm -n "Claude-3" -k "your-api-key" -u "https://api.anthropic.com" -m "claude-3-opus-20240229"

# Export LLM configuration to file
uv run -m acolyte.cli.main config export-config

# Import LLM configuration from file
uv run -m acolyte.cli.main config import-config --name "Claude-3"

# List LLM configurations
uv run -m acolyte.cli.main config list-llms

# List Prompt configurations
uv run -m acolyte.cli.main config list-prompts

# Show specific Prompt content
uv run -m acolyte.cli.main config show-prompt 1

# Synchronize Prompt files
uv run -m acolyte.cli.main config sync-prompts

# Delete LLM configuration
uv run -m acolyte.cli.main config delete-llm 1

# Set log level for CLI operations
ACOLYTE_LOG_LEVEL=debug uv run -m acolyte.cli.main analyze content.txt
```

### Configuration File

The configuration file is located by default at `~/.config/acolyte/config.json`, and you can specify another location through the environment variable `ACOLYTE_CONFIG_PATH`. Configuration file example:

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