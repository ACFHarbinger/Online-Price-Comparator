# Development Guide

## Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv)
- [`just`](https://github.com/casey/just)

## Local Setup

```bash
git clone https://github.com/ACFHarbinger/Python-Module-Template.git
cd Python-Module-Template
cp .env.example .env
just setup
```

## Running Tasks

```bash
just test       # Run pytest suite
just lint       # Run ruff linter
just format     # Run ruff formatter
just typecheck  # Run mypy strict type checker
just check      # Run all quality checks
just docs       # Serve live documentation
```

## Optional infrastructure (`infra/`)

This module template ships a standard infra layout for when you add deploy tooling:

| Path | Purpose |
| --- | --- |
| `infra/global/` | External deploy/host tools (docker, k8s, helm, terraform, ansible) |
| `infra/cloud/` | Managed cloud host configs (AWS, Azure, Firebase, Serverless) |
| `infra/private/` | Developer-only tooling |
| `infra/server/nginx/` | Standalone nginx configs |
| `infra/server/proxy/` | Envoy reverse-proxy configs |

See [`infra/README.md`](../infra/README.md).
