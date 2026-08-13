# Contributing to Python-Module-Template

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org/)
[![uv](https://img.shields.io/badge/uv-Package_Manager-DE5FE9)](https://github.com/astral-sh/uv)

Thank you for contributing! Please follow these guidelines to submit high-quality changes.

## Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv)
- [`just`](https://github.com/casey/just)

## Development Workflow

```bash
just setup    # Create venv and install dependencies
just lint     # Run ruff check
just typecheck# Run mypy strict type checker
just test     # Run pytest test suite
just build    # Build distribution packages
```
