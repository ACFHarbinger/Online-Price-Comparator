# Dashboard UX & Aesthetics Roadmap

**Status:** ✅ Done (v1.4) · 📋 Planned (v2.11, v2.13, v2.14) · **Source:** agy research (aesthetics), grok research (borrowed UX patterns); v2.11/v2.13/v2.14 from the 2026-08-15 global-scope brainstorm

## Aesthetic direction: "Financial Terminal" dark-slate

Deliberately not a generic light-mode SaaS template or decorative consumer
dashboard — this should read like a sharp, professional-grade analytics tool
(the lane of Grafana / Linear / CoinGecko Pro), where key numbers pop instantly
and charts dominate the visual space. Chosen dark-first: price time-series charts
read cleaner against deep slate, and hardware deals are often hunted at night.

### Palette

| Role | Value |
|---|---|
| Canvas / background | Deep charcoal `#0D1117` / `#161B22` |
| Cards / panels | `#161B22` fill, `#21262D` borders |
| Primary text | Off-white `#F0F6FC` |
| Secondary / muted text | Slate grey `#8B949E` |
| Positive (price drop / lowest) | Emerald green `#3FB950` |
| Negative (price increase / OOS) | Crimson red `#F85149` |

### Per-retailer color map

A **brand-nodding categorical palette**, not literal retailer brand colors —
using real brand colors would produce a chaotic clash (Amazon/PcComponentes/
Worten/PCDIGA/Fnac/Chip7 all lean orange/red/yellow). Bind these to one
`RETAILER_COLOR_MAP` constant used by both charts, so a given site is always
the same color everywhere.

| Retailer | Color | Hex |
|---|---|---|
| Amazon.es | Warm amber | `#F59E0B` |
| PcComponentes | Electric cyan | `#06B6D4` |
| Worten | Coral crimson | `#EF4444` |
| Fnac | Golden mustard | `#EAB308` |
| PCDIGA | Royal violet | `#8B5CF6` |
| KuantoKusta | Emerald green | `#10B981` |
| Chip7 | Hot magenta | `#EC4899` |

New retailers get the next visually-distinct unused color; don't reuse one.

### Typography

- UI font: **Inter** (or Plus Jakarta Sans) for headers, nav, labels.
- Numeric font: **JetBrains Mono** (or Roboto Mono) with tabular figures for
  prices/percentages/timestamps, so numbers align vertically in tables/cards
  without shifting.

## Layout: single-product view

```
+-----------------------------------------------------------------------------------+
| HERO HEADER: [Product Image]  Product Title & Specs Tags                          |
|                CURRENT LOWEST: EUR 449.90 (PcComponentes) | ATL: EUR 429.00 (-12% 30d) |
+---------------------------------------------------+-------------------------------+
| PRIMARY CHART: Historical Price Trend (Line)      | SNAPSHOT: Current Prices (Bar)|
| - Range selectors (1W, 1M, 3M, 1Y, ALL)           | - Ranked lowest to highest    |
| - Dashed reference line for all-time low          | - Bars color-coded per store  |
+---------------------------------------------------+-------------------------------+
| RETAILER TABLE & LINKS                                                            |
| Store | Price | Stock | Shipping | Price vs Avg | Direct Buy Link                |
+-----------------------------------------------------------------------------------+
```

1. **Hero header** — product image + title + category tag on the left; on the
   right, a large current-lowest-price callout, an all-time-low (ATL) badge, and
   a 30-day delta pill (`-EUR 35.00 / -7.2% vs 30-day avg`).
2. **Chart grid (65/35 split)** — trend line chart (left, larger) with range
   selectors and a dashed ATL reference line; snapshot bar chart (right),
   sorted cheapest-first, bars colored per the retailer map.
3. **Retailer table** — dense rows: store, price, stock status (dot indicator),
   shipping estimate if known, delta vs. average, direct "View Deal ↗" link.

Anomalous listings (see [product_matching.md](product_matching.md)) are excluded
from all of the above by default, with an explicit toggle to reveal them —
never silently included in "cheapest" or the charts.

## Borrowed UX ideas (v2.5, v2.6)

| Idea | Source | Why |
|---|---|---|
| All-time-low (ATL) badge + reference line | Keepa/CamelCamelCamel | Instantly tells you whether today's price is an actual historic deal. |
| "30-day low" badge (not "lowest ever" until ≥90 days of data) | KuantoKusta's "Boa Compra" | More honest than an unqualified "lowest ever" claim on a young database — don't overclaim on thin history. |
| Delta-vs-30-day-average pill | Financial apps (TradingView/Yahoo Finance) | Instant statistical context without forcing a chart read. |
| Stale-data honesty banner ("PCC failed last run") | — | Never show a dead scraper's last-known price as if it were live; ties into the scraper circuit-breaker status from [scrapers_and_retailers.md](scrapers_and_retailers.md). |
| Out-of-stock strikethrough/greyed display | Camel/Keepa | Prevents false "great price" reads on an item you can't actually buy. |

## Historical-low badge: tiered + percentile (v2.14)

Operationalizes the roadmap's parked "wait vs. buy" idea — the parked note
already said descriptive stats would be acceptable ("price is at a 90-day
low" is a fact; a forecast isn't). Two badge styles, matching
[alerting.md](alerting.md#two-configurable-historical-low-modes-v214)'s two
alert modes — the dashboard shows whichever mode(s) the product's
`historical_low_alert_mode` setting has enabled, since the badge and the
alert should never disagree about which mode is active:

- **Tiered**: generalizes the existing [30-day-low / ATL
  badge](#borrowed-ux-ideas-v25-v26) pattern (already planned for v2.5) into
  a full ladder — **30-day / 90-day / 180-day / 365-day / all-time low**,
  badge shows the strongest tier reached. (This supersedes v2.5's original
  two-tier badge design as a UI implementation — same underlying idea, more
  tiers.)
- **Percentile**: a continuous rarity readout (e.g. "cheaper than 95% of the
  last 180 days") for products configured in `percentile` or `both` mode —
  useful specifically because it doesn't collapse to a fixed boundary the way
  the tiered badge does.

Both purely retrospective — no claim about future prices. Same **item
sticker** calculations power the alert; implement once, surface in both
places. Ranking / "cheapest now" uses credible landed cost (v2.10);
badges and alerts do not.

## Condition badge/filter (v2.11)

Once [`condition`](product_matching.md#condition-as-a-first-class-field-v211)
exists as a field, the snapshot bar and retailer table need a visible
condition badge (new/used/refurb/enterprise-surplus) and a filter toggle.
Showing a €700 used listing directly beside a €2200 new one with no label
would be actively misleading, not just incomplete — this isn't optional
polish, it's required alongside the condition field itself, not a later
follow-up.

## Landed cost and delivery context (v2.13)

For global/EU-wide-tier listings, the retailer table's existing "shipping
estimate" column isn't enough on its own — add an estimated **landed cost**
(native price + shipping + estimated customs/import VAT where applicable) and
a **delivery-time estimate**, both explicitly labeled as estimates, not final
checkout numbers (see [scrapers_and_retailers.md](scrapers_and_retailers.md#global-tier-v213--ram-and-other-small-low-customs-friction-categories)
for why precise duty calculation isn't attempted). This is the same
"total value, not sticker price" principle the retailer table already
applies via the shipping column — extended to make foreign-currency listings
honestly comparable instead of just cheaper-looking. Native price displays as
primary (what you'd actually be charged), EUR-equivalent as the comparison
basis (see [settings_and_config.md](settings_and_config.md#currency-and-fx-normalization)).

If shipping, customs, or import-VAT cannot be estimated credibly
(`import_regime` is `uk_import` or `row` and the estimate is missing), do
**not** fold the listing into the ranked cheapest-price table. Show it in a
distinct, highlighted **Needs landed-cost verification** group immediately
alongside the credible comparison: retain its native and FX-normalized
base price, identify the missing cost components, and allow comparison
with other uncertain offers, but give it no ordinal rank or "best price"
badge. The credible landed-cost winner remains the primary recommendation
until the uncertainty is resolved. Historical-low badges on that row still
refer to its sticker series, and must name condition so a surplus ATL
cannot look like a new-stock ATL.

## Explicitly not doing

- Coupon/affiliate-link interception UI (see [ROADMAP.md](../ROADMAP.md) scope
  boundaries).
- Reviews/Q&A/community UI.
- A watchlist-wide "home" dashboard is v2.1-adjacent (depends on the
  [tracked-product watchlist](settings_and_config.md)) — the single-product view
  above is the v1 target; the multi-product home page comes once there's a
  persistent watchlist to show.

## Interactive Data Visualization & Analytics Features (2026-08-15 Update)

To maximize analytical utility and decision speed without visual clutter:

### 1. Brushing, Linking & Cross-Filtering
- **Linked Viewports**: Hovering over a date node on the primary price trend line dynamically highlights the corresponding store's bar in the Snapshot chart and the specific row in the Retailer Table.
- **Condition Slicing**: Instant filter chips (`[All]`, `[New]`, `[Used]`,
  `[Refurbished]`, `[Enterprise Surplus]`, `[Unknown]`) that dynamically
  recalculate the visible price distribution and the selected exact-condition
  IQR baseline in real time. `Unknown` stays visibly unverified and cannot
  produce the default cheapest winner until the user confirms its condition.
- **Landed Cost Breakdown Waterfall Popover**: Hovering over any total price pops up a structured micro-waterfall:
  $$\text{Total Landed} = \text{Base Price (Converted)} + \text{Shipping Fee} + \text{Estimated Import VAT / Duty}$$
  paired with a delivery SLA indicator (*Express $\le 2$d*, *Standard 3–5d*, *Extended $> 5$d*).

### 2. Statistical Anomaly & Trust Telemetry Modals
- **"Why was this flagged?" Anomaly Inspection Card**: Clicking an anomalous deal badge reveals an explainability card showing the sample size, current median, IQR fences, and seller rating signals.
- **Scraper Circuit-Breaker Status Drawer**: A sleek drawer showing per-retailer telemetry (uptime, last scrape timestamp, response latency, and rate-limit backoff status).

### 3. Statistical price attributes (volatility, trend/gradient) — 2026-08-21, priority 1 of 5

Direct user request: visualizing price data isn't only "what is it now" and
"what was it before" (already covered by the v1.4 snapshot/trend charts) —
add the statistical shape of the price series itself, per-site and/or
aggregated across confirmed listings for a product, same
confirmed/non-anomalous/same-condition population the anomaly detector and
historical-low badges already use (never mix populations across features).

- **Volatility/variance indicator**: a small stat tile or sparkline-adjacent
  figure — coefficient of variation (`stdev / mean`) or IQR-as-%-of-median
  over a configurable rolling window (reuse the same 30d/90d/180d/365d
  windows as v2.14's tiered ladder for a consistent mental model), labeled
  plainly ("price has moved ±6% over the last 90 days"), not a bare number
  without units/context.
- **Trend/gradient indicator**: a short rolling linear-regression slope
  (7d/30d) shown as a small directional arrow/sparkline plus a labeled rate
  ("-€3.20/week" or "+1.1%/week") next to the current-lowest-price callout
  in the hero header. **This is a descriptive statistic about observed
  history, not a forecast** — it must never claim to predict a future price.
  See [price_forecasting.md](price_forecasting.md) for the separate,
  explicitly-labeled-as-predictive feature this deliberately is not; the
  trend indicator here is the stepping stone that feature's v0 design
  reuses, kept in this file because it ships as part of the descriptive
  visualization work, not the forecasting one.
- Both figures respect the existing anomalous-listings toggle (v1.4) and
  condition filter chips (above) — recompute when either changes, never
  silently mix hidden anomalous points or cross-condition data into the
  displayed variance/trend.
- Sparse-history guard: below a minimum observation count for the selected
  window, show "not enough history yet" rather than a statistically
  meaningless number from 2-3 points — same discipline as the anomaly
  detector's own sparse-bucket handling in
  [product_matching.md](product_matching.md).

---

## Temporary Changelog

### 2026-08-15 (Gemini UI/UX Review Pass)
- Added specifications for **Brushing, Linking & Cross-Filtering** between the historical trend line, snapshot bar, and retailer table.
- Added **Landed Cost Breakdown Waterfall Popover** with fulfillment latency SLA indicators.
- Added **Statistical Anomaly Inspection Card** and **Scraper Circuit-Breaker Status Drawer** for operational observability.
