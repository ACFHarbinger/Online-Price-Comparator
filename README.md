# Python-Module-Template

<a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-AGPL_v3-blue.svg"></a>
<a href="https://github.com/ACFHarbinger/Python-Module-Template/actions"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/ACFHarbinger/Python-Module-Template/ci.yml?branch=main&label=CI"></a>
<a href="https://codecov.io/gh/ACFHarbinger/Python-Module-Template"><img alt="Coverage" src="https://img.shields.io/codecov/c/github/ACFHarbinger/Python-Module-Template"></a>

A production-ready, standardized single-module Python repository template powered by [`uv`](https://github.com/astral-sh/uv), [`pytest`](https://docs.pytest.org/), [`ruff`](https://github.com/astral-sh/ruff), [`mypy`](https://mypy-lang.org/), and [`mkdocs`](https://www.mkdocs.org/).

---

## Key Features

- **Modern Packaging**: Pure `pyproject.toml` workspace managed via fast `uv` package resolver.
- **Code Quality**: Pre-configured `ruff` linter/formatter and strict `mypy` type checking.
- **Testing & Benchmarks**: Robust test suite with `pytest`, `pytest-cov`, and performance benchmarks.
- **Documentation Portal**: Multi-page documentation portal using `mkdocs-material` and `mkdocstrings`.
- **CI/CD Infrastructure**: GitHub Actions, GitLab CI, and Forgejo/Gitea pipeline definitions.
- **Agentic Backlog Automation**: Autonomous project sync with GitHub Projects (V2).

---

## Quick Start

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) package manager
- [`just`](https://github.com/casey/just) task runner

### Local Development Setup

```bash
git clone https://github.com/ACFHarbinger/Python-Module-Template.git
cd Python-Module-Template
cp .env.example .env
just setup
```

### Common Commands

```bash
just test      # Run pytest suite with coverage
just lint      # Run ruff check and formatting checks
just typecheck # Run mypy strict type checking
just bench     # Run benchmark suite
just docs      # Serve live local documentation portal
```

---

## Licensing

- **Open Source (Free)**: GNU AGPL-3.0. See [LICENSE](LICENSE) (Section A).
- **Commercial (Paid)**: Enterprise licensing options available. See [LICENSE](LICENSE) (Section B).

## Infrastructure layout

Optional deploy and edge configs live under [`infra/`](infra/README.md):

- `infra/global/` — external deploy/host tooling
- `infra/cloud/` — managed cloud host configs
- `infra/private/` — developer-only tooling
- `infra/server/` — nginx and Envoy reverse-proxy configs
