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

*[English](README.md) | [中文](README_zh.md)*

Acolyte is a content analysis and evaluation system focused on detecting bias, misleading content, and hidden intent in text. The system supports content submission through Web interface, CLI, and API, which is then analyzed by single or multiple LLMs.

## Key Features

- **Multiple Access Methods**: Web interface, CLI, and API
- **Flexible LLM Integration**: Support for multiple LLM providers (Anthropic Claude, OpenAI, Google Gemini)
- **Advanced Analysis Workflows**:
  - Single LLM processing
  - Multiple LLM parallel processing
  - Multi-LLM review aggregation with voting mechanism
- **Comprehensive Content Analysis**:
  - Bias detection
  - Misleading content detection
  - Hidden intent detection
  - Quantitative scoring system with multiple indices
- **Unified Logging System**:
  - Configurable log levels
  - Multiple output destinations (console, file)
  - Detailed diagnostic information
- **History and Record Management**:
  - Task record storage and retrieval
  - Result visualization

## Installation

Create a virtual environment and install dependencies using [uv](https://github.com/astral-sh/uv) (recommended package manager):

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
```

### Configuration Management

```bash
# Add LLM configuration
uv run -m acolyte.cli.main config add-llm -n "Claude-3" -k "your-api-key" -u "https://api.anthropic.com/v1" -m "claude-3-opus-20240229"

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

## Configuration

The configuration file is located by default at `~/.config/acolyte/config.json`, and you can specify another location through the environment variable `ACOLYTE_CONFIG_PATH`.

### Configuration File Example

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

## Development Notes

### Configuration File Format
The configuration file must use the following format:
```json
{
  "database_url": "sqlite:///acolyte.db",
  "default_prompt_version": "",
  "llm_configs": [...]
}
```

Do not use the legacy nested format `{"llms": {...}}`, which will cause the configuration to fail to load correctly. If you encounter this issue, you can use the `tools/convert_config.py` script to convert the format.

### Database Session Management
When using SQLAlchemy, ensure you don't use database objects outside of a session, especially in asynchronous operations. Always acquire and operate on database objects within a session context.

### LLM API URL Format
Different LLM providers have different URL format requirements:
- Anthropic Claude: `https://api.anthropic.com/v1`
- OpenAI: `https://api.openai.com/v1`
- Google Gemini: `https://generativelanguage.googleapis.com/v1beta`

### Prompt Templates
The bias detection prompts used by the system are located in the `prompt/` directory and support model-specific versions. After adding new prompts, you need to run the `config sync-prompts` command to synchronize them to the database. The naming format is `bias-detection-prompt_vX.Y.md` or `bias-detection-prompt_vX.Y_modelname.md`.

### Utility Scripts
The project includes several useful utility scripts in the `tools/` directory:
- `convert_config.py`: Convert configuration file format
- `check_prompts.py`: Check prompt records in the database
- `direct_task_process.py`: Process tasks directly, bypassing the API
- `show_result.py`: Display task result content

### Startup Sequence
1. Start the API server: `uv run -m acolyte.main`
2. Import LLM configurations: `uv run -m acolyte.cli.main config import-config`
3. Synchronize prompts: `uv run -m acolyte.cli.main config sync-prompts`
4. Start analyzing content with the system

## Testing

Acolyte includes a comprehensive test suite to ensure code quality and functionality:

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
./run_tests.sh

# Run specific test modules
python -m pytest tests/unit/core/llm/test_response_parser.py
python -m pytest tests/unit/core/db/test_models.py
python -m pytest tests/unit/core/task/test_base_processor.py

# Generate coverage report
python -m pytest tests/ --cov=acolyte --cov-report=term --cov-report=html
```

See [tests/README.md](tests/README.md) for more details on the testing framework and best practices.