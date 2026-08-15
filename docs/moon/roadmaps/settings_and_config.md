# Settings & Persistent Config Roadmap

**Status:** 📋 Planned (v1.7, v2.1, v2.2, v2.10, v2.14) · **Source:** codex research, grounded in `src/config/settings.py`; v2.10/v2.14 from the 2026-08-15 global-scope brainstorm

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
| `display_currency` | `str` | `"EUR"` | Default display currency. Storage is now native-currency-preserving, not EUR-only — see [Currency and FX normalization](#currency-and-fx-normalization) below (revises the original EUR-native boundary). |
| `fx_rate_provider` | `str` | TBD (e.g. ECB reference rates) | Source for daily FX rates. ECB's daily reference rate API is free, EU-official, and sufficient for a personal tool's daily-refresh cadence — no real-time FX needed. |
| `fx_rate_cache_ttl_hours` | `int` | `24` | Rates refresh once/day; matches the existing `refresh_interval_hours` cadence, not per-request. |
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

## Currency and FX normalization (v2.10)

**Why this revises the original "EUR-native" boundary:** that boundary was
correct for a Portugal/Spain-only scope, where every real listing was already
EUR. The global/EU-wide tiers make non-EUR listings a real, common case (USD
for global RAM sources, GBP for UK, etc.) — exactly the condition the
original boundary named as its own trigger for revisiting.

**Design principle: store what was observed, never silently overwrite it.**

- Every listing/observation persists its **native currency and native price**
  as scraped — this is the source of truth, never discarded.
- A **normalized EUR-equivalent** is computed at scrape time using that day's
  FX rate and stored *alongside* the native value, not instead of it:
  `price_native`, `currency_native`, `price_eur_equivalent`, `fx_rate_used`,
  `fx_rate_date`. This makes every cross-currency comparison auditable —
  "why does this look cheap" is always answerable from stored data, not a
  live recalculation that could silently drift if rates are refreshed later.
- **Anomaly detection and "best price" ranking run on
  `price_eur_equivalent`**, never on mixed native currencies directly — this
  is what makes the [condition-bucketed anomaly design](product_matching.md#condition-as-a-first-class-field-v211)
  actually work correctly across markets.
- **Dashboard shows both**: native price (what you'd actually be charged at
  that retailer) as primary, EUR-equivalent as the comparison basis — never
  only the converted number, since the native price is what matters at
  actual checkout (and FX-converted "savings" that evaporate at your card's
  real conversion rate would be exactly the kind of dishonest number this
  tool exists to avoid).
- `display_currency` (existing field, still useful) controls which currency
  headline numbers render in; the *stored* data is always both, regardless
  of display preference.

## `search_scope_tier` — per-tracked-product geography (v2.1, extended)

Extends the existing `tracked_products` design (below) with one more field:
`search_scope_tier` enum — `local` (Portugal + Spain, original scope) /
`eu_wide` (EU + trade-deal countries, secondhand-inclusive — high-cost
hardware) / `global` (worldwide — small, low-customs-friction categories like
RAM). Default `local`, set explicitly per tracked product; a category default
(e.g. RAM → `global`) is a UX convenience at creation time, not a hardcoded
rule — the field itself is always per-product and overridable, since scope
is genuinely a judgment call per item (see [ROADMAP.md](../ROADMAP.md)'s
tier table for the reasoning), not something the tool should decide
unilaterally.

## Persisted tables (v2.1)

New tables alongside the existing `products` / `listings` / `price_history`
(`src/storage/schema.py`):

- **`tracked_products`** — query text, canonical name, enabled flag,
  per-product refresh-interval override, target price + currency,
  `search_scope_tier` (`local`/`eu_wide`/`global`, see above), created/
  last-checked timestamps. This is what turns an ad-hoc `search` into a
  persistent watchlist entry.
- **`product_identity_rules`** — required model tokens, brand tokens, excluded/
  allowed terms, `match_mode`, user-approved aliases (feeds
  [product_matching.md](product_matching.md)).
- **`candidate_listings`** — `review`/`rejected` match outcomes, kept for
  debugging/manual review, never auto-promoted to `price_history`.
- **`site_settings`** — site key, enabled flag, result limit, min request
  interval, cache TTL, browser-rendering-allowed flag,
  `min_refresh_interval_hours` (site-level refresh-cadence floor, see
  [alerting.md](alerting.md#refresh-scheduling-per-site-cadence-via-a-tick-script-not-a-daemon-v214)).
  Overrides the runtime defaults above per-site (e.g. Amazon at 8s,
  PcComponentes at 15s, per [scrapers_and_retailers.md](scrapers_and_retailers.md)).
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
