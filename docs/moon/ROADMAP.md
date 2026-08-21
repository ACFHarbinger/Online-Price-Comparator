# Roadmap

**Last updated:** 2026-08-21
**Status legend:** ✅ Done · 🚧 In progress · 📋 Planned · 🅿️ Parked (open question, not scheduled) · 🚫 Won't do

## Product direction

Online Price Comparator is a personal, solo-run watchlist tool: you track a small
number of specific products (starting with PC hardware), it builds real price
history over time, and it tells you three things on one screen — who's cheapest
right now (accounting for total landed cost, not just sticker price), whether
that's actually a good price against history, and a direct link to buy. It
deliberately does **not** try to be a broad shopping index (Idealo, KuantoKusta)
or an Amazon-only deep-dive tool (Keepa, CamelCamelCamel) — see [Scope
boundaries](#scope-boundaries).

**Geographic scope is per-category, not a single toggle** (revised 2026-08-15,
motivated directly by the 2026 DRAM shortage and a real German-market
enterprise-surplus GPU purchase — see [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md#geographic-tiers)):

| Tier | Applies to | Geography |
|---|---|---|
| **Local** (original scope) | Default for any category without a wider tier | Portugal + Spain |
| **EU-wide, secondhand-inclusive** | High-cost hardware (GPUs, CPUs, motherboards, and other expensive components) | Search geography: EU + nearby hardware markets (DE/FR/NL/IT plus UK as a *search* target). **Search geography is not import law.** Intra-EU listings are `import_regime = eu_domestic` (no customs). UK listings found under this tier are `uk_import` and need the same landed-cost treatment as global-tier non-EU sources — never implied customs-free because they appeared in an EU-wide search. This market segment (datacenter GPU refreshes, DE surplus) is where the real deals are for expensive parts. |
| **Global** | Small, low-customs-friction categories (RAM, storage, and similar) | Worldwide — item value/size makes customs risk worth it, unlike large or high-value parts. `import_regime` is `row` unless the seller is EU-domestic. |

This reverses the original "EUR-native, no multi-currency" boundary below —
see [settings_and_config.md](roadmaps/settings_and_config.md#currency-and-fx-normalization)
for the normalized-storage design that makes cross-currency comparison honest
rather than just displaying converted numbers.

This direction, the feature shortlist, the aesthetic direction, and the algorithm
designs below came out of a multi-agent brainstorm (grok researched competitors/UX,
agy researched dashboard aesthetics, codex researched matching/anomaly/alerting
algorithms grounded directly in this repo's actual schema) — see the per-feature
roadmap docs for the full reasoning behind each decision.

## Current priorities (2026-08-21)

Direct steer from Harbinger, layered on top of the v1/v2/v3 milestone
structure below (which sequences by *trust-building order*, not by
near-term want-it-now priority — this section is the latter). In priority
order:

1. **Different ways to visualize price data** — historical prices, cross-site/
   cross-distributor comparison, historical-vs-historical, **and statistical
   attributes (variance, current trend/gradient)**. Top priority. Maps to
   v1.4 (✅ done) plus the new **v2.19** [Statistical price attributes](roadmaps/dashboard_ux.md#3-statistical-price-attributes-volatility-trendgradient--2026-08-21-priority-1-of-5)
   section added today — that's the un-speced, not-yet-implemented part of
   this ask.
2. **Persistent settings/config**: customize the app, add other websites to
   the comparator, enable/disable websites per comparison. Maps to v1.7
   (✅ done — runtime fields only, see that row's note), v2.1 (✅ watchlist
   tables + CLI `track`/`sites` + per-product site overrides, 2026-08-21),
   and the [Per-comparison site
   management](roadmaps/settings_and_config.md#per-comparison-site-management-2026-08-21-priority-2-of-5)
   section (per-tracked-product site inclusion override, on top of global
   `site_settings.enabled`). Dashboard settings UI and v2.15 "add a site"
   are still later.
3. **Search feature**: browse the web for more sites carrying a tracked
   product. Maps to existing v2.17a (✅ real `SearchProvider` — SerpAPI Google
   Shopping, 2026-08-21) + v2.17b (discover-and-approve UX, still planned).
4. **Visual aesthetics + other relevant roadmap items**. Maps to the
   existing "Financial Terminal" aesthetic direction in
   [dashboard_ux.md](roadmaps/dashboard_ux.md) (already shipped in v1.4) and
   whatever else is next-most-ready when this priority's turn comes up — not
   a fixed scope, revisit against the milestone tables below at that point.
5. **Price prediction**: how prices are likely to evolve over a future
   window. Lowest of the five, but real — **un-parks** the "Price
   forecasting" row this document's Parked table twice explicitly rejected.
   That rejection was specifically about blending a forecast into the
   descriptive tiered-low badge ("prediction theater"); this request is the
   escalation path the parked note itself anticipated ("worth investigating
   as a separate research track"). New milestone **v2.18**, new doc
   [price_forecasting.md](roadmaps/price_forecasting.md) — see that file for
   the separate-surface/confidence-band/never-blended design this un-parking
   is conditioned on.

## Milestones

### v1 — Trustworthy foundation

The existing search → scrape → normalize → persist → CLI loop, made honest: no
more "search returns whatever loosely matched" — every stored price point is a
confirmed match to the product you actually asked about.

| ID | Item | Status | Roadmap doc |
|---|---|---|---|
| v1.1 | Search-API + scraper abstraction, SQLite persistence, `search` CLI | ✅ Done (abstraction only — the first real `SearchProvider` is v2.17a, not implied by this row) | — |
| v1.2 | Amazon.es + PcComponentes scrapers | ✅ Done | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v1.3 | Price/text normalization | ✅ Done | — |
| v1.4 | Dash dashboard (snapshot bar + trend line, product image, links) | ✅ Done (hero ATL badge + 30d delta pill, trend range selectors + dashed ATL reference line, table stock/shipping/delta-vs-avg columns, anomaly reveal toggle, repository stats — verified 2026-08-21) | [dashboard_ux.md](roadmaps/dashboard_ux.md) |
| v1.5 | Product identity matching (rapidfuzz hybrid matcher) | ✅ Done (query-token-coverage gate, `match_mode`, ASIN-is-not-a-cross-retailer-key, `test/matching/test_matcher.py` — 2026-08-21. `token_sort_ratio >= 88` is the no-model-token/`likely` path, not the hard-model confirm path: verbose exact-SKU titles score ~40-65.) | [product_matching.md](roadmaps/product_matching.md) |
| v1.6 | Price anomaly flagging (IQR-based) | ✅ Done (IQR n>=4 fence + sparse n=2/3 excluded-term fallback unchanged; covered by `test/matching/test_anomaly.py` — 2026-08-21) | [product_matching.md](roadmaps/product_matching.md) |
| v1.7 | Persistent settings schema (runtime + SQLite-persisted config) | ✅ Done (runtime `Settings` additions landed `792b90c` — 2026-08-21, per `settings_and_config.md`'s "v1.7 ships the runtime `Settings` additions only" sequencing note. The SQLite-persisted tables, `tracked_products` etc., are v2.1, not v1.7.) | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v1.8 | Scraper reliability hardening (robots.txt, circuit breaker, shared rate limiter, structured-data-first parsing) | ✅ Done (the existing `fetch/` hardening is joined by JSON-LD-first Product/Offer parsing with CSS fallback for both live scrapers — verified 2026-08-21) | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v1.9 | `AGENTS.md` rewrite for the real stack | ✅ Done (landed `c6e615b`; stale status caught and fixed 2026-08-21) | — |

### v2 — Decision + notify, still personal-scale

Turn the tool from "something you run and read" into "something that tells you
when to act": a persistent watchlist, alerts, and the badges/context that make a
price meaningful instead of just a number.

| ID | Item | Status | Roadmap doc |
|---|---|---|---|
| v2.1 | Tracked-product watchlist (persistent, not just ad-hoc searches) | ✅ Done (watchlist tables + `cli track`/`watchlist`/`untrack`/`sites`, global `site_settings.enabled` and per-product `tracked_product_site_overrides`, discovery honors both — 2026-08-21, [#10](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/10). `product_identity_rules` / `candidate_listings` / `alert_deliveries` / `price_analysis` deferred to the features that write them.) | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v2.2 | Scheduled/passive refresh (daily) | ✅ Done (scheduled & passive refresh runner `src/pipeline/refresh.py`, CLI `refresh [--force] [--watch]`, per-product interval override and due-filtering — 2026-08-21, [#11](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/11)) | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v2.3 | Price-drop alerting: all-time-low, meaningful-drop, target-price rules | ✅ Done (all three rules land in `src/alerting/rules.py` per `alerting.md`'s exact thresholds — ATL uses `max(2%, EUR 5)` below prior sticker ATL, meaningful-drop requires **both** `10%` and `EUR 10` below the 7-day rolling median with a 3-observation minimum — on `price_eur_equivalent`; `AlertingService` wired into `pipeline.refresh.refresh_tracked_product` so a scheduled/passive refresh actually evaluates and dispatches, fail-safe so an alerting error never breaks the refresh — 2026-08-21, [#12](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/12). Condition-bucketing not yet applied — all conditions pooled, same known gap as v1.6.) | [alerting.md](roadmaps/alerting.md) |
| v2.4 | Telegram bot + Discord webhook alert channels | ✅ Done (one `AlertDispatcher` protocol; raw Telegram `sendMessage` + plain Discord webhook `POST`, `alert_channel`-selected, fail-closed — 2026-08-21) | [alerting.md](roadmaps/alerting.md) |
| v2.5 | Delta-vs-average callouts in dashboard; badge design **superseded by v2.14's tiered ladder + percentile modes** (30d/90d/180d/365d/ATL and a configurable rarity percentile replace the original two-tier 30-day/ATL badge) | 📋 Planned | [dashboard_ux.md](roadmaps/dashboard_ux.md) |
| v2.6 | Stock / "not seen recently" honesty (stale-data banners) | ✅ Done (circuit breaker open status banners, PAUSED badges, out-of-stock strikethrough/styling, and stale observation badges in retailer table — 2026-08-21, [#15](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/15)) | [dashboard_ux.md](roadmaps/dashboard_ux.md) |
| v2.7 | Retailer #3–#5: PCDIGA, Worten, Fnac.pt, then Chip7 | ✅ Done (all four PT retailers use polite JSON-LD-first/CSS-fallback adapters with parser fixtures — 2026-08-21) | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.8 | KuantoKusta as a candidate-URL hint source (verified against the real shop, not trusted directly) | ✅ Done (manual external-URL verification fetches/matches the real retailer page into the shared pending-candidate queue; aggregator prices never persist — 2026-08-21) | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.9 | ES/PT shipping-cost sanity (even a per-shop default estimate) | 📋 Planned | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v2.10 | Currency/FX normalization (store native + EUR-equivalent, rate+timestamp persisted) | ✅ Done (ECB daily reference rates + scrape-time `price_eur_equivalent` persisted beside native sticker; anomaly/ranking/forecast still on native `price_amount` this slice — 2026-08-21, [#28](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/28)) | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v2.11 | `condition` as a first-class field (new/used/refurb/enterprise-surplus); anomaly detection bucketed per condition | ✅ Done (extraction + persistence + IQR per exact condition on `price_eur_equivalent`; `unknown`/missing EUR excluded from samples; sparse n<4 never auto-hides — 2026-08-21, [#29](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/29). Dashboard condition badge/filter still open.) | [product_matching.md](roadmaps/product_matching.md) |
| v2.12 | EU-wide tier: German/EU high-cost-hardware retailers + secondhand/classifieds sources, native-language matching (alias lists + translation fallback) | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.13 | Global tier: worldwide RAM/small-item retailers, landed-cost estimate (shipping + customs/VAT + delivery ETA) | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.14 | Per-site refresh cadence (tick script, not a daemon) + tiered/percentile historical-low alert modes + matching dashboard badge | 📋 Planned | [alerting.md](roadmaps/alerting.md), [dashboard_ux.md](roadmaps/dashboard_ux.md) |
| v2.15 | Custom user-added sites: track a specific listing URL (Tier A), custom searchable site (Tier B, later) | ✅ Done (Tier A custom listing URLs: `custom_listing_urls` table, single-page fetcher `src/scrapers/custom_url.py`, pipeline processor `src/pipeline/custom_url.py`, refresh loop integration, dashboard UI — 2026-08-21, [#32](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/32). Tier B later.) | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.16 | Site value-proposition scorecard: extreme-value, consistency/volatility, destination-specific fulfillment SLA, and reliability | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.17a | Real `SearchProvider` (SerpAPI or Google CSE) behind the existing Settings keys — v1.1 delivered only the abstraction + `null_provider.py` | ✅ Done (SerpAPI Google Shopping behind `SERPAPI_KEY`, fail-closed, mocked HTTP tests — 2026-08-21, [#26](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/26). Google CSE still unwired.) | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.17b | Manual, per-product source discovery UX (approve-before-persist; depends on v2.17a) | ✅ Done (additive `candidate_listings` table, daily budget tracking, SerpAPI discovery runner `src/pipeline/source_discovery.py`, dashboard review & approve/reject panel — 2026-08-21, [#30](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/30)) | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.18 | Price forecasting: confidence-banded, separate-surface future-price projection, never blended with descriptive tiered-low/anomaly features | 🚧 In progress (Holt 80% confidence-band model + separate projected-range panel landed; refresh-cadence persistence follows v2.2, [#27](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/27)) | [price_forecasting.md](roadmaps/price_forecasting.md) |
| v2.19 | Statistical price attributes: volatility/variance indicator + descriptive trend/gradient indicator | ✅ Done (single `src/dashboard/stats.py` module: CV/IQR volatility + rolling linear-regression trend, sparse-history guards, hero-metrics integration, currency-grouped so native currencies never mix; repository stays a thin query layer. Redundant repository-side stats models consolidated away during reconciliation — verified 2026-08-21, [#25](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/25)) | [dashboard_ux.md](roadmaps/dashboard_ux.md#3-statistical-price-attributes-volatility-trendgradient--2026-08-21-priority-1-of-5) |

### v3+ — Later

Valuable but not urgent, or genuinely needs v1/v2 trust to be worth building.

| Item | Notes |
|---|---|
| ~~Dumb basket / build-list totals~~ | **Superseded** by [pc_configurator.md](roadmaps/pc_configurator.md) — a separate, explicitly experimental side tool, decoupled from this tool's v1-v3 delivery sequence so it can't block or dilute the core watchlist product. |
| ~~Extra Amazon TLDs (.fr/.de/.it)~~ | **Superseded** by the geographic-tier model above (v2.10-v2.12) — no longer a narrow optional-column idea, folded into the EU-wide/global tiers with real scraper coverage, not just Amazon TLD parameterization. |
| Category price-trend view | "GPU street prices this month" — needs a bigger catalog to be meaningful. |
| Price-per-GB / per-core | Derived column for storage/RAM listings only, not a platform feature. |

### Parked (open questions, not ruled out)

| Item | Why parked | Notes |
|---|---|---|
| 🅿️ Browser extension / userscript | Real UX win, real maintenance cost | Revisit only if you're opening Amazon/PCC in-browser more than the dashboard. Personal userscript first, not a store listing. |
| 🅿️ Simple buy-now-vs-wait guidance | Explicitly **not** ML/prediction — grok's warning against "prediction theater" stands | Operationalized as descriptive stats via v2.14's two configurable modes (tiered historical-low, and percentile rarity for when you can afford to wait for something genuinely unusual). Kept parked here only for true forecasting (see next row), which is still out of scope. |
| ~~🅿️ Price forecasting~~ | **Un-parked 2026-08-21** — direct user request, now v2.18, see [price_forecasting.md](roadmaps/price_forecasting.md) | This row's original separate-surface/never-blended-with-the-tiered-low-badge constraint is preserved as v2.18's actual design, not dropped by un-parking. |

### Scope boundaries

Explicitly out of scope — revisit only with a real, specific reason:

- 🚫 Coupons / affiliate-link interception (Honey-style) — trust-eroding anti-pattern.
- ~~🚫 Multi-currency support~~ — **reversed 2026-08-15**: the global/EU-wide
  tiers make non-EUR retailers a real buy path (exactly the condition this
  boundary said would trigger a revisit). See
  [settings_and_config.md](roadmaps/settings_and_config.md#currency-and-fx-normalization).
- 🚫 Full catalog indexing — this is a watchlist tool, not a shop index; that's Idealo/KuantoKusta's job.
- 🚫 CAPTCHA-solving services, proxy rotation, IP-reputation evasion — not legitimate for a personal tool.
- 🚫 Reviews, Q&A, "community" features.
- 🚫 Real-time (<15 min) tracking — daily/scheduled snapshots are enough for a watchlist; sub-15-minute polling is how you get banned.

## Feature roadmaps

- [Product matching & anomaly detection](roadmaps/product_matching.md)
- [Scrapers & retailer coverage](roadmaps/scrapers_and_retailers.md)
- [Dashboard UX & aesthetics](roadmaps/dashboard_ux.md)
- [Alerting](roadmaps/alerting.md)
- [Settings & persistent config](roadmaps/settings_and_config.md)
- [PC configuration comparator (experimental side tool)](roadmaps/pc_configurator.md)
