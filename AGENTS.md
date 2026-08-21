# AGENTS.md - Instructions for Coding Assistant LLMs

> **Version**: 2.0
> **Last Updated**: 2026-08-14
> **Purpose**: Authoritative reference for AI assistants (Claude, Grok, Codex, Gemini, etc.) working in this repository.

This file previously described a C++/CMake/GoogleTest template — that was a
copy-paste leftover from a sibling variant of the scaffolding this repo was
generated from and never matched anything actually in this repo. Everything
below reflects the real, current stack.

## Table of Contents

1. [Project Overview & Mission](#1-project-overview--mission)
2. [Technical Stack & Governance](#2-technical-stack--governance)
3. [Module Boundaries](#3-module-boundaries)
4. [Key CLI Entry Points](#4-key-cli-entry-points)
5. [Extending the System](#5-extending-the-system)
6. [Coding Standards](#6-coding-standards)
7. [Known Constraints](#7-known-constraints)
8. [Data, Privacy & Scraping Ethics](#8-data-privacy--scraping-ethics)
9. [Roadmap & Further Reading](#9-roadmap--further-reading)

## 1. Project Overview & Mission

Online Price Comparator is a personal, solo-run watchlist tool: given a
product's keywords, it discovers listings across a mix of search-API
providers and site-specific scrapers (currently Amazon.es and PcComponentes,
more Iberian retailers planned), builds real price history in SQLite over
repeated runs, and presents a Plotly Dash dashboard showing per-site links, a
product image, a cross-site snapshot price comparison, and each site's
historical price trend. It deliberately does **not** try to be a broad
shopping index (that's Idealo/KuantoKusta's job) — see
[docs/moon/ROADMAP.md](../docs/moon/ROADMAP.md) for the full product
direction and explicit scope boundaries.

## 2. Technical Stack & Governance

| Component | Specification | Notes |
| --- | --- | --- |
| Language | Python 3.11+ | `from __future__ import annotations` in every file |
| Package manager | [`uv`](https://github.com/astral-sh/uv) | `uv sync`, `uv run ...` |
| Task runner | [`just`](https://github.com/casey/just) | `just --list` for available recipes |
| HTTP client | `httpx` | `src/fetch/http_client.py` — shared client factory + retry helper |
| HTML parsing | `beautifulsoup4` + `lxml` | Used by `src/scrapers/` |
| Persistence | SQLite via `sqlalchemy` (Core, **no ORM**) | `src/storage/` |
| Matching | `rapidfuzz` | `src/matching/` — product identity + price anomaly detection |
| Config | `pydantic-settings` | `src/config/settings.py`, loads `.env` |
| Dashboard | `dash` + `plotly` | `src/dashboard/` |
| Lint/format | `ruff` (line-length 88, `select = ["E","F","I","B","UP","SIM","RUF"]`) | `just lint` / `just format` |
| Type checking | `mypy --strict` | `just typecheck` — every function needs full type annotations |
| Tests | `pytest` (`test/`, mirrors `src/` layout) | See [Known Constraints](#7-known-constraints) before running |

## 3. Module Boundaries

Each `src/<package>/` has its own `__init__.py` + `py.typed` marker. One-line
responsibility per package:

| Package | Responsibility |
| --- | --- |
| `models/` | Shared data contracts (`RawListing`, `Product`) — no I/O |
| `config/` | `Settings` (pydantic-settings), loaded from env/`.env` |
| `search/` | `SearchProvider` Protocol + registry + concrete API providers (SerpAPI/Google CSE — not yet wired up; `NullProvider` is the safe default) |
| `scrapers/` | `ScraperAdapter` Protocol + registry + concrete site scrapers (`amazon.py`, `pccomponentes.py`) |
| `fetch/` | Shared HTTP client, retry-with-backoff, process-wide rate limiter, circuit breaker, robots.txt check, short-lived response cache |
| `normalize/` | Locale-aware price string → `(amount, currency)` parsing; title display-normalization + dedupe keys |
| `matching/` | Product identity matching (`ProductIdentityProfile`, `match_listing`) and cross-retailer price anomaly detection (`detect_anomalies`) |
| `storage/` | SQLite schema (SQLAlchemy Core) + repository layer — the only code that touches the DB directly |
| `pipeline/` | Orchestration: `discover` (fan out to search/scrapers) → `snapshot` (match → anomaly-check → persist) |
| `dashboard/` | Dash app: `theme.py` (palette/typography), `charts.py`, `layout.py`, `callbacks.py`, `app.py` (factory) |
| `cli/` | `argparse` entry point tying pipeline/storage/dashboard together |
| `utils/` | Generic helpers with no other home (currently just `calculate_digest`) |

**Composition flow**: `cli.py` → `pipeline.discover.run_discovery` (fans out to
every enabled `search`/`scrapers` source concurrently-ish, each fails
independently) → `pipeline.snapshot.persist_snapshot` (matches each raw
listing against a `matching.ProductIdentityProfile`, runs
`matching.detect_anomalies` over the confirmed batch, writes to `storage`) →
`dashboard`/`cli` read back through `storage.repository`, which filters to
`confirmed`/`likely` match status and `is_anomalous=False` by default. The
dashboard never touches `scrapers`/`search` directly — it only reads from
`storage`.

## 4. Key CLI Entry Points

### `just` recipes (dev workflow)

| Command | Purpose |
| --- | --- |
| `just --list` | List all available recipes |
| `just setup` | Create venv, sync deps, install pre-commit hooks |
| `just lint` / `just format` | Ruff check / format |
| `just typecheck` | `mypy --strict` |
| `just check` | lint + typecheck + test (see constraint below before running the `test` part) |
| `just test` | Full pytest suite — **see [Known Constraints](#7-known-constraints) first** |
| `just docs` | Serve the mkdocs documentation portal locally |
| `just build` | Build distribution packages |

### `online-price-comparator` (the actual product CLI)

| Command | Purpose |
| --- | --- |
| `online-price-comparator search "<keywords>" [--limit N]` | Discover, persist, and print a confirmed price snapshot |
| `online-price-comparator dashboard [--host] [--port] [--debug]` | Launch the Dash dashboard's dev server |
| `online-price-comparator --version` | Print version |

## 5. Extending the System

### Add a new scraper

1. Implement the `ScraperAdapter` Protocol (`src/scrapers/base.py`) in a new
   `src/scrapers/<site>.py` — needs a `site_key: str` attribute and
   `search(query, *, limit) -> list[RawListing]`. Must fail closed (log +
   return `[]`), never raise.
2. Use `fetch.http_client.build_http_client()` / `get_with_retry()`, a
   per-site `fetch.rate_limit.HostRateLimiter(min_interval_seconds)` (pick a
   conservative interval — 8-15s is the current norm, faster only if the
   site's actual `robots.txt`/observed behavior supports it), and check
   `fetch.circuit_breaker.CircuitBreaker().is_open(site_key)` /
   `fetch.robots.is_allowed(...)` before fetching. See `scrapers/amazon.py`
   or `scrapers/pccomponentes.py` for the full pattern.
3. Register it in `scrapers/registry.py`'s `_build_all_scrapers()`.
4. Prefer structured data (`application/ld+json`) over CSS selectors when a
   site provides it — more robust to layout changes.

### Add a new search-API provider

1. Implement the `SearchProvider` Protocol (`src/search/base.py`) in a new
   `src/search/providers/<name>.py` — needs `name: str`,
   `is_configured() -> bool` (checks its own required settings), and
   `search(query, *, limit) -> list[RawListing]`.
2. Add any required settings (API keys, etc.) to `config/settings.py` and
   document them in `.env.example`.
3. Register it in `search/registry.py`'s `_build_all_providers()`.
4. Never raise from an unconfigured provider — `enabled_providers()` should
   just skip it (logged), so the tool keeps working with zero API keys.

## 6. Coding Standards

- Prefer small, reviewable diffs. Do not reformat files unrelated to the change.
- Full type annotations everywhere — `mypy --strict` is enforced.
- Fail closed, log, and return an empty result rather than raising, for
  anything touching the network (scrapers, search providers) — one broken
  source must never take down discovery for the others.
- Flag, never silently delete, data of dubious quality (mismatched listings,
  anomalous prices) — see `src/matching/`. Read-side filtering happens in
  `storage/repository.py`, not by deleting rows.

## 7. Known Constraints

None currently open. (The CPU cooling issue that previously blocked
`pytest`/`just test`/`just bench` runs was resolved — confirmed by the user
2026-08-21, replacement cooler installed and working; also no longer
applicable to this environment's dev machine regardless. Full test suite
runs are fine.)

## 8. Data, Privacy & Scraping Ethics

- Respect `robots.txt` (`fetch/robots.py`, fail-open only on a genuine
  fetch/parse failure, not as a way to ignore a real disallow).
- Rate-limit every host (`fetch/rate_limit.py`) and back off on repeated
  failures (`fetch/circuit_breaker.py`) rather than retrying aggressively.
- Do not add CAPTCHA-solving, proxy rotation/IP-reputation evasion, or any
  other anti-bot circumvention — explicitly out of scope, see
  [docs/moon/roadmaps/scrapers_and_retailers.md](../docs/moon/roadmaps/scrapers_and_retailers.md).
- No credentials, PII, or payment data are ever stored — the SQLite DB holds
  only product queries, listing URLs/prices, and match/anomaly metadata.

## 9. Roadmap & Further Reading

- [docs/moon/ROADMAP.md](../docs/moon/ROADMAP.md) — milestones, scope
  boundaries, "won't do" list.
- [docs/moon/roadmaps/](../docs/moon/roadmaps/) — per-feature design docs
  (product matching, scraper reliability, dashboard UX, alerting, settings).
- GitHub Project board tracks individual roadmap items as issues.
