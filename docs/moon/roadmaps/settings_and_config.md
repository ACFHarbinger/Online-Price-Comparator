# Settings & Persistent Config Roadmap

**Status:** ✅ Done (v1.7 runtime Settings; v2.1 watchlist + global/per-product site enable/disable; v2.2 scheduled/passive refresh; v2.10 native + EUR-equivalent persistence — 2026-08-21) · 📋 Planned (v2.14) · **Source:** codex research, grounded in `src/config/settings.py`; v2.10/v2.14 from the 2026-08-15 global-scope brainstorm

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
- **Anomaly detection, v2.14 alerts, and historical-low badges** run on the
  observation's persisted **item sticker**: native amount plus the
  `price_eur_equivalent` / `fx_rate_used` / `fx_rate_date` stored with that
  row. They never run on landed-cost. A shipping-table or VAT-rule edit
  must not fire an ATL or rewrite percentile history.
- Persist `condition` on each `price_history` row (observation-time
  snapshot). Listing `condition` is current belief only.
- **"Best price" ranking runs on a credible EUR landed-cost estimate**, not
  price alone: `price_eur_equivalent + shipping + estimated customs/VAT` with
  a persisted basis and confidence. Store the component estimates and
  `landed_cost_eur_estimate` alongside the FX fields. Eligibility depends
  on **`import_regime`** (`eu_domestic` / `uk_import` / `row`), which is
  distinct from `search_scope_tier` (where we *look*). A UK or row listing
  without a credible shipping/customs estimate stays visible in the
  dashboard's highlighted uncertain-cost group, but receives no definitive
  rank and cannot displace a credible landed-cost winner.
- **Dashboard shows both**: native price (what you'd actually be charged at
  that retailer) as primary, EUR-equivalent as the comparison basis — never
  only the converted number, since the native price is what matters at
  actual checkout (and FX-converted "savings" that evaporate at your card's
  real conversion rate would be exactly the kind of dishonest number this
  tool exists to avoid).
- `display_currency` (existing field, still useful) controls which currency
  headline numbers render in; the *stored* data is always both, regardless
  of display preference.

**Shipped 2026-08-21 (persistence slice):** ECB `eurofxref-daily.xml` via
`src/fx/`, scrape-time conversion in `persist_snapshot`, additive
`price_history` columns. `fx_rate_used` is ECB units of native currency per
1 EUR. Fetch/parse failure stores native only (NULL EUR equivalent). IQR
anomaly detection, dashboard ranking, and forecasting are **not** switched
onto `price_eur_equivalent` yet. Landed-cost / `import_regime` columns and
dual native+EUR dashboard display remain later v2.10 follow-ups.

## `search_scope_tier` — per-tracked-product geography (v2.1, extended)

Extends the existing `tracked_products` design (below) with one more field:
`search_scope_tier` enum — `local` (Portugal + Spain, original scope) /
`eu_wide` (search geography: EU hardware markets + UK as a *search* target,
secondhand-inclusive — high-cost hardware) / `global` (worldwide — small,
low-customs-friction categories like RAM). Default `local`, set explicitly
per tracked product; a category default (e.g. RAM → `global`) is a UX
convenience at creation time, not a hardcoded rule — the field itself is
always per-product and overridable, since scope is genuinely a judgment
call per item (see [ROADMAP.md](../ROADMAP.md)'s tier table for the
reasoning), not something the tool should decide unilaterally.

**`import_regime` is a separate listing-level field**, not a synonym of
the search tier: `eu_domestic` (no customs) / `uk_import` / `row`. Derived
from seller destination (and overridable). A `.co.uk` hit found while the
product is `eu_wide` is still `uk_import` for landed-cost and ranking.

## Persisted tables (v2.1)

New tables alongside the existing `products` / `listings` / `price_history`
(`src/storage/schema.py`):

- **`tracked_products`** — query text, canonical name, enabled flag,
  per-product refresh-interval override, target price + currency,
  `search_scope_tier` (`local`/`eu_wide`/`global`, see above; not
  import law — see `import_regime` on listings),
  `historical_low_alert_mode` (`tiered`/`percentile`/`both`) plus
  `rarity_percentile`/`rarity_window_days`/`rarity_min_observations` for the
  percentile mode (see
  [alerting.md](alerting.md#two-configurable-historical-low-modes-v214)),
  created/last-checked timestamps. This is what turns an ad-hoc `search`
  into a persistent watchlist entry.
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

## Per-comparison site management (2026-08-21, priority 2 of 5)

**Why:** direct user request, 2026-08-21 — "customize the app, including
adding other websites to the comparator and allowing him to enable/disable
websites for certain comparisons." Two distinct capabilities, both building
on tables already speced above rather than replacing them:

1. **Global site enable/disable** — already covered by `site_settings.enabled`
   (above). No new design needed; this is the existing per-site toggle
   applied app-wide (e.g. "stop querying PCDIGA everywhere").
2. **Per-tracked-product site inclusion** (new) — a tracked product needs to
   opt a site *out* of its own comparisons without disabling that site
   globally (e.g. "don't check Amazon.es for this one item because its
   listing there is a mismatched bundle," while Amazon.es stays enabled for
   every other tracked product). New join table **`tracked_product_site_overrides`**:
   `tracked_product_id`, `site_key`, `included` (bool), `reason` (free text,
   optional — "site sells a bundle-only SKU here," "confirmed wrong variant
   listed," etc.). Absence of a row for a `(product, site)` pair means
   "follow the global `site_settings.enabled` default" — this table only
   stores *exceptions*, not a full per-product/per-site matrix, so adding a
   new site never requires touching every existing tracked product's rows.
   **Shipped 2026-08-21** via `cli sites exclude|include|clear-override` and
   `cli sites enable|disable`; the dashboard has no settings pane yet but its
   search box already respects these flags.
3. **"Adding other websites to the comparator"** — this is `scrapers/`'s
   existing extension pattern (`AGENTS.md` §5 "Add a new scraper") plus
   v2.15's custom-site tracking, not a new mechanism. What's new here is
   making that discoverable/manageable *from settings* rather than only
   via a code change: v2.15 Tier A (track a specific listing URL) is
   already a user-facing, no-code action once implemented — this note just
   confirms it's the intended vehicle for "add other websites," so v2.15's
   priority should track this request rather than being treated as a
   separate, lower-priority idea. A registered site's own scraper code
   (Tier B, "custom searchable site") still requires implementing the
   `ScraperAdapter` Protocol — that's a code change by design (arbitrary
   site scraping can't be safely no-code without the fail-closed/rate-limit/
   robots.txt contract every scraper must follow), not a gap to close here.

## Sequencing

v1.7 ships the runtime `Settings` additions only (no behavior depends on them
yet beyond documenting intent). v2.1 adds `tracked_products` and turns
`cli search` into two modes: an ad-hoc one-off (today's behavior, unchanged)
and a `cli track <keywords>` that persists a watchlist entry. **Shipped
2026-08-21:** those two modes, plus `site_settings` / `tracked_product_site_overrides`
and `cli sites` for global and per-product enable/disable. Discovery (`cli
search`/`track` and the dashboard search box) honors the flags. The other
tables originally listed under v2.1 (`product_identity_rules`,
`candidate_listings`, `alert_deliveries`, `price_analysis`) are not created
yet — they wait for matching-evidence persistence and v2.3 alerting.
v2.2 adds the actual scheduled-refresh runner (a simple loop/cron entry
point, not a new service — this is a personal tool, not infrastructure).

**v2.10 (native + FX + landed-cost + `import_regime`) lands before
v2.11–v2.16 and before the PC configurator.** Condition buckets, site
scorecards, and BOM totals are meaningless on mixed native currencies or
sticker-as-landed. v2.17a (one real `SearchProvider`) is a prerequisite of
v2.17b (discover-and-approve UX), not part of it.
