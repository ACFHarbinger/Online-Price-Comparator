# Dashboard UX & Aesthetics Roadmap

**Status:** 🚧 In progress (v1.4) · **Source:** agy research (aesthetics), grok research (borrowed UX patterns)

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

## Explicitly not doing

- Coupon/affiliate-link interception UI (see [ROADMAP.md](../ROADMAP.md) scope
  boundaries).
- Reviews/Q&A/community UI.
- A watchlist-wide "home" dashboard is v2.1-adjacent (depends on the
  [tracked-product watchlist](settings_and_config.md)) — the single-product view
  above is the v1 target; the multi-product home page comes once there's a
  persistent watchlist to show.
