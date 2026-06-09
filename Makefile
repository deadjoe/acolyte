.PHONY: setup dev format lint test run clean web-setup web-dev web-test

# === Backend (uv) ===

setup:
	uv sync

dev:
	uv sync --extra dev

format:
	uv run black .
	uv run isort .

lint:
	uv run ruff check .
	uv run mypy .

test:
	uv run pytest

run:
	uv run acolyte

# === Frontend (bun) ===

web-setup:
	cd acolyte/web && bun install

web-dev:
	cd acolyte/web && bun run dev

web-test:
	cd acolyte/web && bun run test

# === Cleanup ===

clean:
	rm -rf .venv
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf coverage_html_report
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
