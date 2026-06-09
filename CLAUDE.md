# CLAUDE.md

## Commands

```bash
# Backend (uv)
uv sync --extra dev     # install all deps
uv run pytest           # run tests (424 passed)
uv run ruff check .     # lint
uv run black .          # format
uv run acolyte          # start API server

# Frontend (bun) — run from acolyte/web/
cd acolyte/web
bun install             # install deps
bun run dev             # dev server (localhost:5173)
bun run build           # production build
bun run test            # run tests (26 passed)
bun run lint            # ESLint
```

## Architecture

```
acolyte/                    # backend Python package
├── api/                    # FastAPI routes → thin, delegates to services
├── cli/                    # Click CLI → entry point: acolyte.cli.main:cli
├── core/
│   ├── db/models.py        # SQLAlchemy models (LlmConfig, Task, TaskResult, Prompt)
│   ├── db/session.py       # run_in_session, session_scope
│   ├── llm/base.py         # LlmClient abstract base → all providers extend this
│   ├── llm/client.py       # get_client_for_llm() factory
│   ├── llm/providers/      # anthropic, openai, gemini, deepseek, ollama
│   ├── task/               # processors: SingleLlm, MultipleLlm, Review
│   └── services/           # LlmService, TaskService, PromptService
├── web/                    # React + Vite frontend (bun)
└── utils/logging.py        # get_logger("module_name")

tests/                      # pytest at repo root (424 tests)
prompt/                     # bias-detection-prompt_vX.Y[_model].md
tools/                      # convert_config, sync_prompts, etc.
```

## Key Patterns

- **Service layer**: API routes are thin; business logic lives in `core/services/`
- **Async everywhere**: FastAPI + httpx + asyncio. Use `@pytest.mark.asyncio` for async tests
- **DB sessions**: Use `run_in_session()` helper, never hold objects outside sessions
- **LLM clients**: Factory pattern via `get_client_for_llm(config)`; all extend `LlmClient`
- **Config**: JSON at `~/.config/acolyte/config.json`, overridable via `ACOLYTE_CONFIG_PATH`
- **Logging**: `from acolyte.utils.logging import get_logger`; env vars control level/format

## Conventions

- Python: PEP 8, snake_case, PascalCase classes, UPPER_SNAKE constants
- Frontend: TypeScript strict mode, path alias `@/` → `src/`
- CSS: Tailwind v4 with `@tailwindcss/vite` plugin (no tailwind.config.js needed)
- Dependencies: `>=` constraints in pyproject.toml; exact pins in uv.lock (committed)
- Python ≥ 3.10 required (3.9 is EOL, no longer supported)

## Environment Variables

| Variable | Purpose |
|---|---|
| `ACOLYTE_LOG_LEVEL` | debug/info/warning/error/critical |
| `ACOLYTE_LOG_TO_FILE` | 1 to enable file logging |
| `ACOLYTE_LOG_DIR` | log directory path |
| `ACOLYTE_PORT` | API server port |
| `ACOLYTE_CONFIG_PATH` | config file path override |
| `ACOLYTE_DATABASE_URL` | DB connection string |
| `VITE_API_URL` | Frontend API base URL |
