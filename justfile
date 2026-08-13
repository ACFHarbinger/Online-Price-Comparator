# Justfile for Python-Module-Template

set shell := ["bash", "-c"]

# Default task: list all commands
default:
    @just --list

# Set up local virtual environment and install dependencies
setup:
    uv venv .venv
    uv sync --extra dev --extra docs
    uv run pre-commit install

# Run full test suite with coverage
test:
    uv run pytest

# Run performance benchmarks
bench:
    uv run pytest test/test_benchmark.py --benchmark-only 2>/dev/null || uv run python benchmark/bench_core.py

# Lint codebase with ruff
lint:
    uv run ruff check .

# Format codebase with ruff
format:
    uv run ruff format .

# Type check codebase with mypy
typecheck:
    uv run mypy src test

# Run all quality checks (lint, typecheck, test)
check: lint typecheck test

# Build documentation portal locally
docs:
    uv run mkdocs serve

# Build production distribution packages
build:
    uv build

# Clean temporary build and cache files
clean:
    rm -rf .venv .uv build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov site
