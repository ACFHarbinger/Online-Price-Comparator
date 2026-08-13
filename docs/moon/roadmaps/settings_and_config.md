# Settings & Persistent Config Roadmap

**Status:** 📋 Planned (v1.7, v2.1, v2.2) · **Source:** codex research, grounded in `src/config/settings.py`

## Two-layer config split

- **Runtime settings** (`src/config/settings.py`, `pydantic-settings`, `.env`):
  paths, secrets, networking/reliability tuning, feature defaults. Stateless,
  read once at startup.
- **SQLite-persisted user/domain config** (new tables): tracked products,
  identity-matching profiles, alert state, per-site overrides. This data has a
  lifecycle (created, updated, referenced by history) and doesn't belong in an
  environment variable — a tracked-product list needs IDs, target prices,
  per-product exclusions, and alert delivery history, none of which fit a CSV
  env var.

## Runtime `Settings` — planned additions (v1.7)

Current fields (`database_path`, `enabled_scrapers`, `serpapi_key`,
`google_cse_api_key`, `google_cse_cx`, `app_env`, `log_level`) stay as-is.
Planned additions:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `display_currency` | `str` | `"EUR"` | Display-only; matching/storage stays EUR-native per [scope boundaries](../ROADMAP.md#scope-boundaries). |
| `default_results_per_source` | `int` | `10` | CLI/dashboard default, distinct from the hard cap. |
| `max_results_per_source` | `int` | `20` | Upper bound regardless of caller-requested limit. |
| `monitoring_enabled` | `bool` | `false` | Master switch for scheduled/passive refresh (v2.2). |
| `refresh_interval_hours` | `int` | `12` | How often a tracked product is re-checked. |
| `request_timeout_seconds` / `connect_timeout_seconds` | `float` | `15.0` / `5.0` | Slightly more generous than the current hardcoded `httpx.Timeout(10.0, connect=5.0)`. |
| `response_cache_ttl_seconds` | `int` | `600` | Short-lived cache for successful scraper responses (see [scrapers_and_retailers.md](scrapers_and_retailers.md)). |
| `robots_cache_ttl_hours` | `int` | `24` | |
| `default_min_request_interval_seconds` | `float` | `5.0` | Replaces the current global `1.5s` default in `HostRateLimiter` — per-site overrides go in `site_settings` (below). |
| `request_jitter_fraction` | `float` | `0.20` | |
| `retry_max_attempts` | `int` | `2` | |
| `retry_initial_backoff_seconds` / `retry_max_backoff_seconds` | `float` | `2.0` / `30.0` | |
| `block_circuit_breaker_failures` | `int` | `2` | Failures before a site is paused. |
| `block_circuit_breaker_cooldown_hours` | `int` | `24` | |
| `browser_fallback_enabled` | `bool` | `false` | Master switch for the Playwright fallback path. |
| `browser_fallback_sites` | `str` (CSV) | `""` | Explicit allowlist — never on by default per-site. |
| `alerts_enabled` | `bool` | `true` | |
| `alert_drop_percent` | `float` | `10.0` | |
| `alert_drop_min_amount` | `Decimal` | `10.00` | |
| `alert_rolling_window_days` | `int` | `7` | |
| `alert_all_time_low_percent` | `float` | `2.0` | |
| `alert_all_time_low_min_amount` | `Decimal` | `5.00` | |
| `alert_cooldown_hours` | `int` | `72` | |
| `alert_channel` | enum | `"none"` | `"telegram"` / `"discord"` / both once [alerting.md](alerting.md) lands. |
| `telegram_bot_token`, `telegram_chat_id` | optional secret `str` | `None` | |
| `discord_webhook_url` | optional secret `str` | `None` | |

## Persisted tables (v2.1)

New tables alongside the existing `products` / `listings` / `price_history`
(`src/storage/schema.py`):

- **`tracked_products`** — query text, canonical name, enabled flag,
  per-product refresh-interval override, target price + currency, created/
  last-checked timestamps. This is what turns an ad-hoc `search` into a
  persistent watchlist entry.
- **`product_identity_rules`** — required model tokens, brand tokens, excluded/
  allowed terms, `match_mode`, user-approved aliases (feeds
  [product_matching.md](product_matching.md)).
- **`candidate_listings`** — `review`/`rejected` match outcomes, kept for
  debugging/manual review, never auto-promoted to `price_history`.
- **`site_settings`** — site key, enabled flag, result limit, min request
  interval, cache TTL, browser-rendering-allowed flag. Overrides the runtime
  defaults above per-site (e.g. Amazon at 8s, PcComponentes at 15s, per
  [scrapers_and_retailers.md](scrapers_and_retailers.md)).
- **`alert_deliveries`** — product, alert type, triggering listing/observation,
  payload fingerprint, delivered timestamp/status. Backs the alert cooldown
  logic in [alerting.md](alerting.md).
- **`price_analysis`** — observation/listing reference plus match and anomaly
  outcome + reasons (feeds both matching and anomaly detection).

## Sequencing

v1.7 ships the runtime `Settings` additions only (no behavior depends on them
yet beyond documenting intent). v2.1 adds `tracked_products` and turns
`cli search` into two modes: an ad-hoc one-off (today's behavior, unchanged)
and a `cli track <keywords>` that persists a watchlist entry. v2.2 adds the
actual scheduled-refresh runner (a simple loop/cron entry point, not a new
service — this is a personal tool, not infrastructure).
