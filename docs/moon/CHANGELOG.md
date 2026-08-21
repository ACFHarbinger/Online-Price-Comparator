# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **v2.3 close-out: all-time-low + meaningful-drop alerts, refresh wiring
  (2026-08-21):** `src/alerting/rules.py` gains `should_fire_all_time_low`
  and `should_fire_meaningful_drop`, both operating on
  `price_eur_equivalent` per `alerting.md`'s exact thresholds (ATL: the
  *larger* of 2% or EUR 5 below the prior sticker ATL; meaningful-drop:
  *both* 10% and EUR 10 below the 7-day rolling median, gated on >=3
  observations in that window). New `src/alerting/{messages,observations}.py`
  support the richer message content and the EUR-equivalent history lookup
  the two rules need. `AlertingService` is now invoked from
  `pipeline.refresh.refresh_tracked_product` after each snapshot persists,
  wrapped so an alerting failure logs and never breaks the refresh. Not yet
  done: condition-bucketing (all conditions pooled into one comparison,
  same known gap `anomaly.py` still has).

### Changed (2026-08-21 priority list)

- **2026-08-21 priority list from Harbinger, documented before implementation:**
  five priorities, in order — (1) price-data visualization including
  statistical attributes (variance, trend/gradient), (2) persistent
  settings/config with per-comparison site enable/disable, (3) source
  discovery search, (4) visual aesthetics + other roadmap items, (5) price
  forecasting. Added `ROADMAP.md`'s new "Current priorities (2026-08-21)"
  section mapping each to roadmap IDs; added new spec content for the two
  priorities that needed it (statistics view in `dashboard_ux.md`,
  per-product site override in `settings_and_config.md`) plus a new
  `price_forecasting.md` un-parking the previously-twice-rejected
  forecasting idea under an explicit separate-surface/confidence-band
  design (new milestone v2.18). Priorities 3 and 4 map to existing v2.17a/b
  and v1.4/dashboard_ux.md work — no new spec, just re-sequencing.
  Fixed `v1.7`'s `ROADMAP.md` status line (was still marked incomplete
  after `792b90c` landed the runtime `Settings` fields) and
  `product_matching.md`'s status header (was still "Planned" after Grok's
  v1.5/v1.6 close-out landed).

### Added

- **v2.8 KuantoKusta verification consumer (2026-08-21):** manual
  `verify_kuantokusta_hints_for_product` consumes typed external retailer URL
  hints, performs a polite robots-checked, rate-limited fetch of each real
  retailer page, requires complete Product/Offer JSON-LD and an identity
  match, then creates a time-limited **pending** candidate through the shared
  `CandidateListingRepository`. It never parses or stores the aggregator's
  displayed price, and it rejects unmatched pages and duplicate URLs. User
  approval remains required before a candidate is promoted.

- **v2.11 condition-bucketed IQR (2026-08-21):** `detect_anomalies` now fences
  each exact condition on scrape-time `price_eur_equivalent` (never mixed
  native currencies, never landed-cost). `unknown` and missing EUR values
  are excluded from every sample. Sparse buckets (n<4 in that condition,
  including sparse `new`) never auto-hide. `persist_snapshot` converts to
  EUR before the fence. Dashboard condition badges/filters remain later.

- **v2.11 listing condition field (2026-08-21):** additive `condition` /
  `condition_source` / `condition_confidence` on `listings` (current belief)
  and `price_history` (observation-time snapshot). `extract_condition` reads
  structured-data `itemCondition`, then title keywords (ES/PT/EN/DE used /
  refurb / surplus / explicit new), then `unknown` — never a silent `new`.
  Known new-stock retailers may apply recorded `source_policy`. IQR anomaly
  detection is **not** bucketed by condition this slice. Historic rows stay
  NULL (no backfill).

- **v2.17b manual per-product source discovery UX (2026-08-21):** implemented
  manual, user-triggered source discovery for watchlist items. Created
  additive `candidate_listings` table, daily credit budget limiter (50
  credits/day) and per-run limits (10 items), discovery runner in
  `src/pipeline/source_discovery.py`, and `CandidateListingRepository` in
  `src/storage/candidates.py`. Discovered sources pass through identity
  matching and are presented as time-limited (7-day) pending candidates in a
  dashboard review panel. Explicit user approval promotes candidate to persistent
  `listings`, creates initial `price_history`, and ensures `tracked_product_site_overrides`
  enablement; rejection/expiry drops candidates cleanly. Full test coverage in
  `test/storage/test_candidates.py`, `test/pipeline/test_source_discovery.py`,
  and `test/dashboard/test_candidates_view.py`.

- **v2.7 retailer coverage complete / v2.8 groundwork (2026-08-21):** added
  the CHIP7 adapter, completing the planned Portugal retailer set. Like the
  other retailer adapters it uses robots checks, rate limiting, cache/retry and
  circuit-breaker safeguards, and prefers complete Product/Offer JSON-LD over
  its CSS fallback. Added the separate `KuantoKustaHintSource`, which yields
  typed external retailer URL hints only — it is deliberately not a
  `ScraperAdapter`, has no price field, and is excluded from `run_discovery`,
  making it impossible to persist KuantoKusta's displayed comparison price.
  A later hint consumer must fetch and match the real retailer URL before any
  observation can enter price history.

- **v2.10 currency/FX normalization (2026-08-21):** `price_history` now stores
  the native sticker (`price_native`/`currency_native`) alongside a scrape-time
  EUR equivalent (`price_eur_equivalent`, `fx_rate_used`, `fx_rate_date`).
  New `src/fx/` fetches ECB eurofxref-daily.xml (quoted as units of foreign
  currency per 1 EUR), caches it for `fx_rate_cache_ttl_hours`, and fail-closes
  to a NULL EUR equivalent when the rate is missing. EUR identity conversion
  needs no network. `persist_snapshot` writes the pair; `matching/anomaly.py`
  still runs on native amounts this slice. Landed-cost / ranking / dashboard
  dual-price display and wiring anomaly/forecasting onto EUR-equivalent are
  follow-ups.

- **v2.6 stock & stale-data honesty banners (2026-08-21):** enhanced dashboard
  with honest circuit-breaker and stale-data visibility. Surfaced open circuit
  breakers via `CircuitBreaker.open_sites()` as top warning banners and retailer
  table `[PAUSED]` badges with `.row-blocked` styling. Rendered out-of-stock
  listings honestly with `.price-strikethrough`, `.stock-out` indicators, and
  `.row-out-of-stock` styling. Added stale observations handling (>24h) with
  `STALE (Xd ago)` badges and `.stock-stale` indicators. Full test coverage in
  `test/fetch/test_circuit_breaker.py` and `test/dashboard/test_charts_and_views.py`.

- **v2.3/v2.4 alerting, target-price slice (2026-08-21, scoped down):** new
  `src/alerting/` package plus an additive `alert_deliveries` table. Only the
  **target-price crossing** rule ships (`current_price <= user_target_price`,
  notify once on a fresh crossing below - never on re-refresh while below -
  honoring `alert_cooldown_hours`). One internal `AlertDispatcher` protocol
  with a raw Telegram `sendMessage` and a plain Discord webhook `POST`,
  selected via `alert_channel`; both fail-closed (log + `False`, never raise)
  and record a delivery only on success so failures retry. `alert_deliveries`
  drives the per-(product, alert-type) cooldown and audit. **Out of scope this
  pass:** all-time-low, meaningful-drop, and the v2.14 tiered/percentile rules -
  all three key on `price_eur_equivalent`, which lands with v2.10 in the same
  round. Target-price does not depend on it, hence it is the one rule shipped.
  Coverage in `test/alerting/`.

- **v2.7 Portugal retailer coverage (2026-08-21, in progress):** added
  PCDIGA, Worten, and Fnac.pt scraper adapters and registered them alongside
  Amazon.es and PcComponentes. Each checks robots.txt, shares a 12-second
  per-host rate limit, uses the existing retry/cache/circuit-breaker safeguards,
  fails closed on fetch or block-page failures, and prefers complete schema.org
  Product/Offer JSON-LD before a retailer-specific CSS fallback. Sanitized
  fixture tests cover JSON-LD precedence and CSS fallback for all three sites.
  Chip7 remains the final planned v2.7 retailer.

- **v2.2 scheduled and passive refresh (2026-08-21):** added `src/pipeline/refresh.py`
  orchestrating watchlist re-checks (`is_due_for_refresh`, `refresh_tracked_product`,
  `refresh_watchlist`, `run_monitoring_loop`). Checks whether enabled watchlist items
  are due based on per-product `refresh_interval_hours` overrides or the global
  `Settings.refresh_interval_hours` (default: 12h), discovers listings honoring site
  settings and overrides, persists snapshots, and touches `last_checked_at`. Added
  CLI command `online-price-comparator refresh [--force] [--limit N] [--watch] [--interval-seconds S]`
  for manual, cron, or continuous passive background monitoring. Full test coverage
  in `test/pipeline/test_refresh.py` and `test/test_cli.py`.

- **v2.18 forecasting first slice (2026-08-21, in progress):** added the
  dependency-free Holt linear-trend model in `forecasting.holt`. It aggregates
  daily same-currency medians, refuses histories with fewer than eight
  observations or 21 days of span, and produces a widening 80% confidence band
  for a 14-day horizon. The dashboard renders that band only in a separate
  **Projected — not a guarantee** panel with its history gate and training-data
  timestamp; forecasts remain isolated from observed charts, price ranking,
  historical-low badges, and anomaly detection. Persisted refresh-cadence
  retraining awaits v2.2.

- **v2.17a SerpAPI SearchProvider (2026-08-21):** `SerpApiProvider` implements
  the existing `SearchProvider` Protocol against Google Shopping
  (`engine=google_shopping`, `gl=es`) behind `SERPAPI_KEY`. Unconfigured or
  failed requests log and return `[]` (never raise). Registered in
  `search.registry`; Google CSE stays unwired. Mocked HTTP coverage in
  `test/search/` (configured results, zero results, API error, HTTP/transport
  failure, unset key). v2.17b approve-before-persist is not this slice.

- **v2.1 watchlist + per-comparison site enable/disable (2026-08-21):** new
  SQLite tables `tracked_products`, `site_settings`, and
  `tracked_product_site_overrides` (schema + `src/storage/watchlist.py`, not
  the price-history repository). `cli track` / `watchlist` / `untrack` persist
  a watchlist without changing ad-hoc `search`. `cli sites` lists, globally
  enables/disables retailers, and sets per-product include/exclude exceptions
  (absence of a row still means "follow the global default"). Discovery honors
  those flags when given a DB engine (CLI search/track and dashboard search).
  Remaining originally-listed v2.1 tables (`product_identity_rules`,
  `candidate_listings`, `alert_deliveries`, `price_analysis`) wait for the
  features that write them.

- **Matching excluded-term negation (2026-08-21):** `find_excluded_term` now
  ignores a prohibited accessory/category phrase when it is preceded by a
  negation particle (`sin` / `sem` / `without` / `no`, plus an intervening
  article). Amazon.es "Sin Ventilador" / "without a cooler" CPU titles
  confirm instead of false-rejecting on `ventilador`/`cooler`; positive
  mentions (`Cooler para Ryzen…`, `con ventilador`) still reject. Shared
  by the matcher and the sparse anomaly path.

- **v2.19 statistical price attributes (2026-08-21):** the single-product
  hero reports price volatility (coefficient of variation / IQR percent of
  median) in plain percentage terms and a descriptive linear-regression
  observed trend rate per week (with directional arrows and weekly percentage
  rates). Implemented as a **single** stats module, `src/dashboard/stats.py`,
  with standalone statistical descriptors (`coefficient_of_variation`,
  `iqr_percent_of_median`, `linear_regression_slope`, `compute_price_stats`)
  used directly by the dashboard over history returned from the repository.
  Reconciliation: the storage layer stays a thin query layer — the redundant
  repository-side statistic models (`PriceVolatilityStats`, `PriceTrendStats`,
  `compute_price_volatility`, `compute_price_trend`, `PriceSeriesStatistics`,
  `product_price_series_statistics`) and the dead `volatility_90d`/`trend_30d`
  branch in `_build_hero_metrics` were consolidated away. Calculations use only
  confirmed, non-anomalous observations by default, recompute when the
  anomalous-listings reveal toggle changes, enforce an observation-count sparse
  guard, and select one compatible native currency rather than mixing
  currencies before v2.10 FX normalization. Coverage in
  `test/dashboard/test_stats.py` and `test/dashboard/test_charts_and_views.py`.

- **Test/verification scaffolding (2026-08-21, opencode):** added a reusable
  `in_memory_engine` pytest fixture in `test/conftest.py` (shared in-memory
  SQLite engine via `StaticPool`, schema bootstrapped with
  `metadata.create_all`) so storage/repository tests can reuse one helper
  instead of recreating temp-DB logic per package; created
  `test/{matching,dashboard,scrapers}/` as empty packages and a `test/__init__.py`
  so pytest's `prepend` import mode inserts the repo root (not `test/`) on
  `sys.path`, preventing `test/scrapers` etc. from shadowing the same-named
  `src/` packages.

### Changed

- **v1.5/v1.6 matching close-out (2026-08-21):** `match_listing` now
  enforces query-token coverage >= 0.80 on meaningful non-stopword tokens,
  `ProductIdentityProfile` carries `match_mode` (`exact_model` /
  `strict_title` / `manual_review`) and `build_profile_from_query` picks
  `exact_model` when a SKU-like token is present else `strict_title`, and
  Amazon-ASIN-shaped tokens are excluded from model-token extraction so an
  ASIN cannot become a cross-retailer identity key. Confirmed matches still
  follow the spec's "hard model match, no conflict" path — `token_sort_ratio
  >= 88` is applied on the no-model-token (`strict_title` / `likely`) path
  only, because verbose retail titles of the exact SKU routinely score
  ~40-65. `anomaly.py`'s IQR / sparse algorithm is unchanged. New suite
  `test/matching/` covers the Ryzen 9950X3D vs-variant example, bundle/kit
  exclusion, the coverage gate, match_mode, ASIN non-identity, and the n>=4
  IQR plus n=2/3 excluded-term sparse fallback.

- **v1.4 dashboard remainder close-out (2026-08-21):** extended the single-product
  Dash dashboard with an All-Time-Low (ATL) badge and 30-day delta vs. average pill
  in the hero header, historical trend chart range selectors (1W, 1M, 3M, 1Y, ALL)
  with a dashed ATL reference line, expanded retailer table columns (stock status
  dot indicator, shipping estimate placeholder, delta vs. average), and an
  anomalous-listings reveal toggle backed by read-side repository filtering. Added
  `ProductPriceStats` and `product_price_stats` query to `PriceHistoryRepository`.
  Added tests under `test/dashboard/`.

- **v1.8 scraper reliability close-out (2026-08-21):** Amazon.es and
  PcComponentes now parse complete schema.org `Product`/`Offer` JSON-LD before
  trying their existing CSS selectors. Malformed or incomplete structured data
  is ignored safely and falls through to CSS parsing. Added fixture-backed
  coverage for JSON-LD precedence and CSS fallback on both retailers.

- **Roadmap status reconciliation + multi-agent BUS kickoff (2026-08-21):**
  verified `docs/moon/ROADMAP.md`'s status column against real code instead
  of trusting the table: v1.9 (`AGENTS.md` rewrite) was already done
  (`c6e615b`) but marked Planned; v1.5/v1.6 (`src/matching/`) and v1.8
  (`src/fetch/` hardening) had real, substantial implementations already
  landed but marked Planned; v1.7 (persistent settings schema) is confirmed
  genuinely not started. Updated `ROADMAP.md` and the `product_matching.md`/
  `scrapers_and_retailers.md` status headers accordingly. Resolved the
  CPU-cooler test-execution caution in `AGENTS.md` §7 (confirmed by the user)
  and removed the two now-stale `.agent/cache/HANDOFF_*` files whose content
  (cooler crisis, 2026-08-15 roadmap review) is either resolved or already
  folded into the roadmap docs themselves. Started `.agent/bus/` (see
  `.agent/bus/AGENT_BUS.md`) as the coordination log for delegating
  remaining v1.4/v1.5/v1.6/v1.7/v1.8 work across opencode/grok/codex/agy,
  mirroring the Image-Toolkit repo's bus convention.

- **Grok roadmap review (2026-08-15):** after the global-scope expansion
  and the Gemini/Chat passes, locked: alerts/ATL/percentile on persisted
  item sticker (not landed-cost); `import_regime` (`eu_domestic` /
  `uk_import` / `row`) distinct from `search_scope_tier`; `condition`
  snapshotted on every `price_history` row; sparse-bucket review anchor
  as a per-category editable fraction (GPU surplus 0.40, RAM used 0.50
  starting values); v2.16 is a four-cell scorecard not a composite
  score, price dimensions same-condition only; v2.17 split into 2.17a
  real `SearchProvider` then 2.17b discover-and-approve; Kleinanzeigen
  is a separate source from eBay.de; PC-configurator v0 totals labeled
  as independent-component sums and blocked on v2.10.

### Added

- **Global/EU-wide scope expansion roadmap (2026-08-15):** added v2.10-v2.14
  across `ROADMAP.md`, `product_matching.md`, `scrapers_and_retailers.md`,
  `settings_and_config.md`, and `dashboard_ux.md` — reverses the original
  EUR-only/Iberia-only scope boundaries into a per-tracked-product geographic
  tier model (local / EU-wide-secondhand-inclusive / global), motivated by
  the 2026 DRAM shortage and a real German enterprise-surplus GPU purchase.
  Key additions: `condition` as a first-class field so used/refurb listings
  get their own anomaly-detection statistical bucket instead of being
  auto-hidden against new-retail medians; native-currency-preserving storage
  with an EUR-equivalent computed alongside (never replacing) the observed
  price; multilingual matching via per-market alias lists with machine
  translation as a fallback; landed-cost/delivery-time estimates for
  cross-border listings; per-site refresh cadence via a tick script (not a
  new daemon process); a statistical-rarity alert and matching percentile-
  rank dashboard badge, both descriptive/retrospective only, no forecasting.
  **Revised same day**: the rarity alert/badge became a tiered historical-low
  ladder (30d/90d/180d/365d/all-time, fires at the strongest tier reached)
  rather than a raw percentile score — generalizes and supersedes v2.5's
  original two-tier 30-day/ATL badge design instead of sitting alongside it.
  Price forecasting (ARIMA or similar) noted as a genuinely separate future
  research track in the Parked table, explicitly not blended into the
  descriptive tiered-low feature.
  **Revised again same day**: percentile rarity restored as a second,
  independent configurable mode alongside the tiered ladder (not replaced by
  it) — `historical_low_alert_mode` (`tiered`/`percentile`/`both`) lets the
  tier ladder and the percentile rule fire independently, since they answer
  different questions (interpretable window-based vs. continuously tunable
  rarity) and which one you want depends on urgency, not correctness.

- **Custom sites, site scoring, source discovery, and PC configurator
  (2026-08-15):** added v2.15 (custom user-added sites — track a specific
  listing URL now, a custom searchable site later), v2.16 (site
  value-proposition scoring: extreme-value + consistency/volatility pair +
  inferred proximity + reliability, sample-size-gated), and v2.17 (per-product
  source discovery, scoped to avoid the existing full-catalog-indexing
  boundary; found and flagged that v1.1's search-API abstraction has no real
  provider implementation yet, only `null_provider.py`, despite being marked
  Done). Added `pc_configurator.md`, a new, explicitly experimental and
  un-sequenced side-tool roadmap (hand-specified build cost/value comparison
  at v0, compatibility-aware automatic enumeration as a later explicit
  escalation, not assumed) — supersedes and replaces the original "dumb
  basket" v3+ item.

- **Interactive Analytics, Landed-Cost Breakdown & 3D Configurator UI (2026-08-15):**
  added UI/UX specifications across `dashboard_ux.md` and `pc_configurator.md`
  incorporating brushing and linking across historical trend lines, snapshot
  bars, and retailer tables; condition filter chips with dynamic IQR recalculation;
  landed-cost breakdown waterfall popovers with delivery SLA tiers; statistical
  anomaly inspection cards and scraper circuit-breaker status drawers; and
  experimental `@react-three/fiber` 3D exploded-view schematic rigs, multi-build
  value radar charts, and historical build-cost timeline scrubbers for the PC
  configurator tool.


- Created templates and placeholder documents for research and reports directories under `docs/research/` and `docs/reports/`.
- Created a beautiful, interactive Vue documentation portal in `docs/website/` that parses and displays all repository documentation files dynamically with search, dark mode, alert styling, and navigation.
- Created `website/javascript/` workspace similar to the typescript/ directory but for JavaScript, and added it to root workspace settings and `justfile` tasks.
- Populated `langs/sql`, `langs/graphql`, `langs/mjml`, `r/`, and `ruby/` directories with comprehensive multi-language code snippets.
- Populated `website/html/` (with a premium dark-themed landing page), `website/php/`, and `website/css/` (with a modular CSS framework architecture).
- Populated all `libraries/` subdirectories (including Prisma ORM, Fastlane, Rails, LESS, SASS, SCSS, Stylus, Delta Lake, PHPMailer, Expo, Firebase, TensorFlow for `flow`, PyTorch for `torch`, and Jinja templates).
- Populated package manager configuration examples in the `env/` directory and its subdirectories (including Bower, Conda, C++ CMakeLists.txt/Qt GUI `.pro` files, Gopm, Gradle, Maven, NPM, Pixi, and UV configurations).
- Populated Jupyter notebook examples in `notebooks/` utilizing `notebook_setup.py` utility.
- Added editor settings templates for IntelliJ IDEA, Obsidian, and Sublime Text under the `settings/` directory.
- Initial template scaffolding: root files (`LICENSE`, `README.md`, `.env.example`, `.pre-commit-config.yaml`, `.gitignore`/`.gitattributes`), `.git/` CI/CD, `git/` (`CONTRIBUTING.md`, `codecov.yaml`), `docs/` documentation portal (MkDocs + Sphinx + Structurizr + ADRs), `moon/` roadmap and changelog.
- `.agent/` LLM coding-agent scaffolding: `AGENTS.md` plus generic rules, workflows, prompts, and skills covering all six supported languages.
- Six language module skeletons (`python/`, `typescript/`, `kotlin/`, `rust/`, `go/`, `cpp/`), root workspace orchestrator files, and merged `python/validation/` dev-tooling.
- `java/` Maven module (7th language), wired into CI/pre-commit/justfile/docs alongside the existing six.
- Root Gradle wrapper and multi-project build files pairing with the existing `settings.gradle.kts`.
- `docs/moon/roadmaps/developer_tools.md`: architecture plan for a polyglot `dev/` developer-assistant tool, synthesized from prior art across the org's other repos.
- GitHub Project (V2) backlog automation (`git/` + `.git/workflows/agent_sync.yml`).
- `infra/{k8s,helm,terraform,ansible}/` infra-as-code scaffolding, alongside the relocated `infra/docker/`.
- `dev/` developer-assistant tool, milestones D1–D5 of `docs/moon/roadmaps/developer_tools.md`: the `input/protobuf/codegraph.proto` schema, a hand-mirrored Python data model (`core/model.py`), a real AST-based Python import-graph parser (`input/python/parser.py`), multi-source graph aggregation (`core/aggregate.py`), layer classification + forbidden-direction violation detection (`core/layers.py`), Tarjan's-SCC circular-dependency detection (`core/cycles.py`), a self-contained vis.js/Jinja2 HTML report generator (`output/html/report.py`), and a `cli.py` tying it together (`report`/`check` subcommands). 13 passing pytest cases, including a fixture project with an intentional import cycle.

### Changed

- Moved `moon/` directory into `docs/` to integrate with the documentation portal, and updated all referencing files.
- Moved `docker/` to `infra/docker/` to make room for other infra-as-code stacks; updated all referencing files.

## [0.1.0] — 2026-07-30

### Added

- Repository created from scratch as a GitHub template.
