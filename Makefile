.PHONY: setup dev format lint test run clean

setup:
	uv venv
	uv pip install -e .

dev:
	uv pip install -e ".[dev]"

format:
	uv run -m black .
	uv run -m isort .

lint:
	uv run -m ruff check .
	uv run -m mypy .

test:
	uv run -m pytest

run:
	uv run -m acolyte.main

clean:
	rm -rf .venv
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete