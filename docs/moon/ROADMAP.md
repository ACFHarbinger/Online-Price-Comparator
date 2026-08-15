# Roadmap

**Last updated:** 2026-08-13
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
| **EU-wide, secondhand-inclusive** | High-cost hardware (GPUs, CPUs, motherboards, and other expensive components) | EU + trade-deal countries, including native-language-only sites (e.g. German enterprise-surplus/classifieds markets) — no customs friction inside the EU, and this market segment (datacenter GPU refreshes, etc.) is where the real deals are for expensive parts. |
| **Global** | Small, low-customs-friction categories (RAM, storage, and similar) | Worldwide — item value/size makes customs risk worth it, unlike large or high-value parts. |

This reverses the original "EUR-native, no multi-currency" boundary below —
see [settings_and_config.md](roadmaps/settings_and_config.md#currency-and-fx-normalization)
for the normalized-storage design that makes cross-currency comparison honest
rather than just displaying converted numbers.

This direction, the feature shortlist, the aesthetic direction, and the algorithm
designs below came out of a multi-agent brainstorm (grok researched competitors/UX,
agy researched dashboard aesthetics, codex researched matching/anomaly/alerting
algorithms grounded directly in this repo's actual schema) — see the per-feature
roadmap docs for the full reasoning behind each decision.

## Milestones

### v1 — Trustworthy foundation

The existing search → scrape → normalize → persist → CLI loop, made honest: no
more "search returns whatever loosely matched" — every stored price point is a
confirmed match to the product you actually asked about.

| ID | Item | Status | Roadmap doc |
|---|---|---|---|
| v1.1 | Search-API + scraper abstraction, SQLite persistence, `search` CLI | ✅ Done (abstraction only — see v2.17 caveat: no real `SearchProvider` implementation exists yet, only `null_provider.py`) | — |
| v1.2 | Amazon.es + PcComponentes scrapers | ✅ Done | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v1.3 | Price/text normalization | ✅ Done | — |
| v1.4 | Dash dashboard (snapshot bar + trend line, product image, links) | 🚧 In progress | [dashboard_ux.md](roadmaps/dashboard_ux.md) |
| v1.5 | Product identity matching (rapidfuzz hybrid matcher) | 📋 Planned | [product_matching.md](roadmaps/product_matching.md) |
| v1.6 | Price anomaly flagging (IQR-based) | 📋 Planned | [product_matching.md](roadmaps/product_matching.md) |
| v1.7 | Persistent settings schema (runtime + SQLite-persisted config) | 📋 Planned | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v1.8 | Scraper reliability hardening (robots.txt, circuit breaker, shared rate limiter, structured-data-first parsing) | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v1.9 | `.agent/AGENTS.md` rewrite for the real stack | 📋 Planned | — |

### v2 — Decision + notify, still personal-scale

Turn the tool from "something you run and read" into "something that tells you
when to act": a persistent watchlist, alerts, and the badges/context that make a
price meaningful instead of just a number.

| ID | Item | Status | Roadmap doc |
|---|---|---|---|
| v2.1 | Tracked-product watchlist (persistent, not just ad-hoc searches) | 📋 Planned | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v2.2 | Scheduled/passive refresh (daily) | 📋 Planned | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v2.3 | Price-drop alerting: all-time-low, meaningful-drop, target-price rules | 📋 Planned | [alerting.md](roadmaps/alerting.md) |
| v2.4 | Telegram bot + Discord webhook alert channels | 📋 Planned | [alerting.md](roadmaps/alerting.md) |
| v2.5 | Delta-vs-average callouts in dashboard; badge design **superseded by v2.14's tiered ladder + percentile modes** (30d/90d/180d/365d/ATL and a configurable rarity percentile replace the original two-tier 30-day/ATL badge) | 📋 Planned | [dashboard_ux.md](roadmaps/dashboard_ux.md) |
| v2.6 | Stock / "not seen recently" honesty (stale-data banners) | 📋 Planned | [dashboard_ux.md](roadmaps/dashboard_ux.md) |
| v2.7 | Retailer #3–#5: PCDIGA, Worten, Fnac.pt, then Chip7 | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.8 | KuantoKusta as a candidate-URL hint source (verified against the real shop, not trusted directly) | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.9 | ES/PT shipping-cost sanity (even a per-shop default estimate) | 📋 Planned | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v2.10 | Currency/FX normalization (store native + EUR-equivalent, rate+timestamp persisted) | 📋 Planned | [settings_and_config.md](roadmaps/settings_and_config.md) |
| v2.11 | `condition` as a first-class field (new/used/refurb/enterprise-surplus); anomaly detection bucketed per condition | 📋 Planned | [product_matching.md](roadmaps/product_matching.md) |
| v2.12 | EU-wide tier: German/EU high-cost-hardware retailers + secondhand/classifieds sources, native-language matching (alias lists + translation fallback) | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.13 | Global tier: worldwide RAM/small-item retailers, landed-cost estimate (shipping + customs/VAT + delivery ETA) | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.14 | Per-site refresh cadence (tick script, not a daemon) + tiered/percentile historical-low alert modes + matching dashboard badge | 📋 Planned | [alerting.md](roadmaps/alerting.md), [dashboard_ux.md](roadmaps/dashboard_ux.md) |
| v2.15 | Custom user-added sites: track a specific listing URL (Tier A), custom searchable site (Tier B, later) | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.16 | Site value-proposition scoring: extreme-value + consistency/volatility + inferred proximity + reliability | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |
| v2.17 | Per-product source discovery (needs a real `SearchProvider` implementation first — currently only a stub exists) | 📋 Planned | [scrapers_and_retailers.md](roadmaps/scrapers_and_retailers.md) |

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
| 🅿️ Price forecasting (ARIMA or similar time-series methods) | Genuinely different from v2.14's descriptive tiers — this would be an actual prediction, which the roadmap has twice now explicitly rejected for the shipped product ("prediction theater"). Noted 2026-08-15 as worth investigating **as a separate research track**, not a feature to build | If pursued, must stay clearly separated from the tiered-low alert/badge — never blended into the same UI surface or presented with the same confidence, so a forecast can't be mistaken for the descriptive fact it sits next to. |

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
