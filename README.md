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

Acolyte is a content analysis and evaluation system that detects bias, misleading content, and hidden intent in text. Submit content via Web UI, CLI, or API — analyzed by single or multiple LLMs.

## Features

- **Web UI, CLI, and API** access
- **Multi-LLM support**: Anthropic Claude, OpenAI, Google Gemini
- **Analysis modes**: single LLM, multi-LLM parallel, multi-LLM with review/voting
- **Scoring**: bias index, misleading index, hidden intent index, credibility score
- **History**: task records, result visualization
- **Modern web stack**: React + TypeScript + Tailwind CSS v4 + shadcn UI

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- [bun](https://bun.sh)

### Backend

```bash
uv sync --extra dev   # install all dependencies
uv run acolyte        # start API server (http://localhost:8000)
```

### Frontend

```bash
cd acolyte/web
bun install           # install dependencies
bun run dev           # start dev server (http://localhost:5173)
```

### CLI

```bash
uv run acolyte analyze content.txt --mode=single
uv run acolyte history list --limit=5
uv run acolyte config add-llm -n "My LLM" -k "sk-..." -u "https://api.openai.com/v1" -m "gpt-4o"
```

## Project Structure

```
acolyte/
├── acolyte/              # backend Python package
│   ├── core/             # LLM, DB, task processing
│   ├── api/              # FastAPI routes
│   ├── cli/              # CLI (Click)
│   └── web/              # React + Vite frontend
├── tests/                # Python tests (424 passed)
├── prompt/               # bias detection prompt templates
├── tools/                # utility scripts
├── pyproject.toml        # project config + dependencies
├── uv.lock               # pinned dependency versions
└── Makefile              # convenience commands
```

## Configuration

Config file at `~/.config/acolyte/config.json` (override with `ACOLYTE_CONFIG_PATH`):

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

## Development

```bash
# Backend
uv sync --extra dev     # install with dev deps
uv run pytest           # run tests (424 passed)
uv run ruff check .     # lint
uv run black .          # format

# Frontend
cd acolyte/web
bun run dev             # dev server
bun run build           # production build
bun run test            # run tests (26 passed)
bun run lint            # ESLint

# Convenience (from repo root)
make test               # backend tests
make web-test           # frontend tests
make lint               # backend lint
make clean              # remove build artifacts
```

## Prompt Templates

Bias detection prompts in `prompt/` follow the naming convention `bias-detection-prompt_vX.Y[_modelname].md`. After adding prompts, sync to database:

```bash
uv run acolyte config sync-prompts
```

## License

MIT
