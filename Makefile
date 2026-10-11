.PHONY: help db-up db-down test lint typecheck check format

help:
	@echo "Available commands:"
	@echo "  make db-up      Start PostgreSQL container"
	@echo "  make db-down    Stop PostgreSQL container"
	@echo "  make test       Run test suite via pytest"
	@echo "  make lint       Run ruff linter"
	@echo "  make typecheck  Run mypy type checker"
	@echo "  make check      Run lint, typecheck, and test"
	@echo "  make format     Format code with ruff"

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

test:
	uv run --directory backend --group dev pytest

lint:
	uv run --directory backend --group dev ruff check src tests

typecheck:
	uv run --directory backend --group dev mypy src tests

format:
	uv run --directory backend --group dev ruff format src tests

check: lint typecheck test
