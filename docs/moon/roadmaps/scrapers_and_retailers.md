# Scrapers & Retailer Coverage Roadmap

**Status:** ✅ v1.8 reliability hardening complete (including structured-data-first parsing for both original live scrapers — verified 2026-08-21) · ✅ v2.7 Portugal retailer coverage (2026-08-21) · ✅ v2.8 KuantoKusta external-URL hints + real-shop verification (2026-08-21) · ✅ v2.15 Tier A custom listing URLs (2026-08-21) · ✅ v2.17a SerpAPI SearchProvider (2026-08-21) · ✅ v2.17b discover-and-approve UX (2026-08-21) · 📋 Planned (v2.12, v2.13, v2.15 Tier B, v2.16) · **Source:** codex research (reliability), grok research (retailer priority); v2.12/v2.13/v2.15-v2.17 from the 2026-08-15 global-scope brainstorm

## Current state

| Site | Status | Notes |
|---|---|---|
| Amazon.es | ✅ Scraper live (`src/scrapers/amazon.py`) | Real prices confirmed via `.a-offscreen` spans; parameterized by domain for future `.fr`/`.de`/`.it`. Intermittent Akamai bot-challenge blocking observed even with realistic headers + rate limiting — see [reliability](#reliability-hardening-v18) below. |
| PcComponentes | ✅ Scraper live (`src/scrapers/pccomponentes.py`) | Consistently blocked by a Cloudflare Turnstile challenge with plain `httpx` — needs the Playwright fallback path (site-allowlisted, see below) before it will return real data. |
| PCDIGA | ✅ Scraper live (`src/scrapers/pcdiga.py`) | PT hardware specialist; JSON-LD first with CSS fallback and polite fail-closed fetch safeguards. |
| Worten | ✅ Scraper live (`src/scrapers/worten.py`) | PT major electronics retailer; JSON-LD first with CSS fallback and polite fail-closed fetch safeguards. |
| Fnac.pt | ✅ Scraper live (`src/scrapers/fnac.py`) | JSON-LD first with CSS fallback and polite fail-closed fetch safeguards. |
| Chip7 | ✅ Scraper live (`src/scrapers/chip7.py`) | JSON-LD first with CSS fallback and the same polite, fail-closed fetch safeguards as the other PT retailers. |
| KuantoKusta | ✅ Candidate URL hints + verification live | Typed external retailer URL hints are manually fetched and identity-matched against the real retailer page before entering the shared **pending** candidate queue. Aggregator prices never persist; user approval remains required. |
| Amazon.fr / .de / .it | 🗓️ v3+ | Optional columns with an import-duty/"not a local buy" tag, not default-on. |

## Reliability hardening (v1.8)

Roadmap this tool as a **polite, failure-tolerant collector**, not an anti-bot
evasion system. Real blocking has already been observed twice in this repo
(Cloudflare on PcComponentes, intermittent Akamai on Amazon.es), so this is
grounded in actual behavior, not hypotheticals.

**Worth implementing:**

- Respect `robots.txt` before fetching a scraper route; cache it 24h
  (`urllib.robotparser` exposes `can_fetch`, `crawl_delay`, `request_rate`).
- Make `HostRateLimiter` shared/process-wide by host — today `PcComponentesScraper`
  creates a new limiter per `search()` call, so it doesn't retain timing across
  searches. Per-site defaults should start deliberately slower than the current
  global 1.5s: **8s for Amazon, 15s for PcComponentes** after the observed
  blocking, relaxing only if reliability supports it.
- Minimum host interval + 0–20% random jitter; use the stricter of configured
  delay vs. declared `crawl-delay`.
- Retry only transient failures (connection errors, 429/500/502/503/504) — two
  retries, exponential backoff ~2s then 4s, capped at 30s, jittered, respecting
  `Retry-After`.
- On 403, challenge-page markers, or repeated 429: **stop**, don't retry
  aggressively. Open a per-site circuit breaker after 2 such failures, pause the
  source 24h, record a clear "blocked" status (visible in the dashboard as a
  stale-data banner — see [dashboard_ux.md](dashboard_ux.md)).
- Cache successful responses 10 minutes, keyed by site + normalized query —
  cheap dashboard refreshes, less accidental repeat traffic.
- One persistent HTTP client/session per source run; realistic locale-specific
  `Accept-Language`; explicit response validation.
- A small, current, manually curated set of User-Agent strings if needed — one
  per scraper *session*, not per request. Prefer an honest, application-identifying
  UA where a retailer's policy permits it.
- **Structured-data-first parsing** (✅ complete for Amazon.es and
  PcComponentes): prefer `application/ld+json` or embedded JSON
  state over brittle CSS selectors when a site provides it (more robust to layout
  changes than the current selector-based approach).
- Fixture-based parser tests from saved, sanitized HTML for normal / changed-layout
  / blocked / no-results pages — building on the fixture pattern already started
  in `test/fixtures/html/`.
- Playwright, **allowlisted per site, disabled by default** — only for sites that
  genuinely require JS rendering for ordinary browser access (PcComponentes is
  the first candidate). Never used to bypass challenges/access controls — if a
  site's Cloudflare/Turnstile challenge specifically blocks non-human traffic,
  that site's data isn't scraped, full stop.

**Explicitly not worth pursuing:**

- CAPTCHA-solving services.
- Residential/datacenter proxy rotation or IP-reputation evasion.
- Login/session farming, fingerprint spoofing, stealth-browser tooling.
- Escalating request volume after a block.

When a source is blocked, the pipeline should return a clean partial result set
from the other sources (already true today — `pipeline.discover` fans out and
each adapter fails independently) and surface the blocked source's status
honestly rather than silently showing stale data as current.

## Geographic tiers (v2.12–v2.13)

Added 2026-08-15, motivated by the DRAM shortage (RAM needs worldwide reach)
and a real German enterprise-surplus GPU purchase (high-cost hardware needs
EU-wide reach with secondhand sources) — see
[ROADMAP.md](../ROADMAP.md#product-direction) for the tier table. This
section is retailer/source detail; the per-product `search_scope_tier` field
is in [settings_and_config.md](settings_and_config.md#search_scope_tier--per-tracked-product-geography-v21-extended).

### EU-wide tier (v2.12) — high-cost hardware, secondhand-inclusive

Candidate sources, in rough priority order — **not exhaustive, a starting
set to validate the tier before expanding it**:

| Source | Type | Notes |
|---|---|---|
| Mindfactory.de, Alternate.de | New retail | Germany's two largest PC-hardware retailers; frequently undercut Iberian prices on new stock alone, before even considering secondhand. `robots.txt` verified 2026-08-21: general catalog/search browsing is **not** disallowed for either, no crawl-delay specified — self-impose the usual 8–15s conservative default anyway. **In progress**, see v2.12 (#34). |
| Geizhals.de | Price-comparison aggregator (DE/AT, pan-EU merchants) | Found during the 2026-08-21 DDR5/RTX-3090-Ti market scans (`docs/moon/reports/`) — **not previously in this list**, and high-leverage: a single product page already aggregates live offers from many DE/AT retailers plus a client-rendered price-history chart, cheaper than scraping each merchant separately. **robots.txt caveat (verified 2026-08-21): the search/filter method the scan reports actually used (`?...asuch=...`) is explicitly disallowed** (`Disallow: /*?*asuch=`). Individual product-page URLs (not reached via that query param) are not confirmed either way. **Do not build a v2.12 registry scraper against Geizhals's search.** Treat it as a v2.15 Tier A custom-URL source instead — the user finds a specific Geizhals product page themselves (browser, not automation) and the tool just re-fetches that one already-known page, which is a materially different (and lower-risk) request pattern than automated search crawling. |
| eBay.de | Auction / Buy-It-Now marketplace | Structured-ish listings, seller ratings, often ships EU-wide. Separate scraper from Kleinanzeigen. eBay publishes an official **Browse API** (REST, OAuth2 client-credentials) — per the 2026-08-21 scan reports, **prefer the official API over HTML scraping** here specifically; it's the recommended integration path for reliability and staying within terms of service, and the search-result HTML itself is server-rendered/scrapeable as a fallback if the API integration is deferred. |
| ebay-kleinanzeigen.de | Local classifieds | **A different site** from eBay.de (do not parameterize one scraper as the other). Where many surplus/datacenter-refresh cards actually surface. Individual-seller, local-pickup common — needs per-listing condition/seller-signal extraction and honest `import_regime` / shipping (often `eu_domestic` + pickup, not a shop SLA). **Operational finding, 2026-08-21**: the market-scan reports observed an outright IP-range ban after only **two** automated search requests ("IP-Bereich vorübergehend gesperrt"). This is the most bot-defensive site in either scan. Per this doc's own "explicitly not worth pursuing" list below (no IP-reputation evasion, no escalating volume after a block), **do not build an automated search scraper for this site** — a permanently-blocked host key defeats the purpose anyway. If it's wanted at all, scope it to the same v2.15 Tier A custom-URL pattern as Geizhals (one known listing, manually found, periodically re-fetched at a very conservative interval), not a `scrapers/` registry entry, and drop it immediately (no retry) on any block signal. |
| Rebuy, refurbed.de (or equivalent EU refurb marketplaces) | Refurb retail | Structured "refurb" listings (graded condition, dealer warranty) are a lower-risk middle ground between new-retail and individual-seller secondhand — worth prioritizing over raw classifieds where available, since condition/warranty claims are more verifiable. |
| Scan.co.uk, Overclockers UK | New retail | UK is outside the EU customs union post-Brexit but still worth including given it's a major hardware market — landed-cost estimation (below) applies to UK sources the same as non-EU global-tier ones, not treated as EU-frictionless. |
| LDLC.com | New retail (France) | Found during the 2026-08-21 scans. `robots.txt` verified 2026-08-21: `/recherche` (search) is disallowed, but general catalog/category pages are not — matches the scan report's own suggestion to use it as a **restock/negative-signal source** (periodically check known chipset/category URLs for a product reappearing) rather than a search-driven scraper. A v2.15 Tier A custom-URL entry is the safest fit; a full `scrapers/` category-page monitor is a smaller, later option if this pattern turns out to matter for other products too. |
| Wallapop.es | C2C classifieds (Spain) | **Approved 2026-08-21 for v2.15 Tier A only** (Harbinger's explicit call on #37): `robots.txt` disallows `/search` and any querystring path, which this tool reads as "no automated searching for the cheapest listing across the store," but a specific known item URL (`/item/<slug>-<id>`, no query string) isn't disallowed — Harbinger's own interpretation is that tracking one already-found listing is within the site's actual objection, unlike a search crawler. **Do not build a `scrapers/` registry entry or anything that queries `/search`** — Tier A custom-URL tracking only, one page at a time, user-initiated. |
| Leboncoin.fr | C2C classifieds (France) | **Decided 2026-08-21 (#37): server-side collection stays ruled out** (`robots.txt` blocks named AI/LLM bots from `/ad/` and states *"forbidden to use search robots or other automatic methods"*), **but user-browser-initiated monitoring is approved** — Harbinger's research draws a real distinction between a server acting as an independent bot and a check run as the user's own browser session, "a human who refreshes the page, but faster," the same reasoning legitimate products like Distill Web Monitor/Visualping rely on. **Gated on [v2.20](client_side_monitor.md) shipping** — not even v2.15 Tier A (server-side) applies here in the meantime. Was the single most productive source in either 2026-08-21 market scan (the €900 DDR5 match, several €1,000 RTX 3090 Ti matches) — worth the wait. |

All EU-wide-tier sources need the [multilingual matching](product_matching.md#multilingual-matching-v212)
design for non-English listings, and the [condition field](product_matching.md#condition-as-a-first-class-field-v211)
for the secondhand/refurb sources specifically.

### Sites investigated 2026-08-21 and not currently pursued

Real market-scan work (`docs/moon/reports/ddr5_128gb_market_scan_report.md`,
`docs/moon/reports/rtx_3090ti_market_scan_report.md`) found these C2C
classifieds sites productive for near-budget used-hardware leads — but
productivity isn't the bar this tool uses (see [Reliability
hardening](#reliability-hardening-v18)'s "polite, failure-tolerant
collector, not an anti-bot evasion system" stance). `robots.txt` was
checked directly (2026-08-21) against each. (Wallapop.es and Leboncoin.fr
were originally listed here too — both moved to the candidates table above
2026-08-21 after Harbinger's explicit review on #37; Leboncoin's approval
is conditional on v2.20 shipping first.)

| Site | Finding | Status |
|---|---|---|
| Subito.it | `robots.txt` itself returned **HTTP 403 Forbidden** to a plain fetch (2026-08-21) — the site refused even the compliance-check request. | **Won't do.** Not pursued further; a host that blocks robots.txt retrieval itself is not a credible target for a "polite collector," full stop. |

**Kleinanzeigen.de's aggressive IP-banning (above) belongs in this same
category in practice**, even though it's still listed as a v2.12 candidate
above under the manual/custom-URL carve-out — the default assumption for
any new source should be "verify `robots.txt` and do one cautious manual
probe before writing a scraper," not "productive in a market scan implies
safe to automate," since this pass found three-of-four scanned classifieds
sites actively hostile to automation.

### Cross-cutting crawler-design findings (2026-08-21 market scans)

From the same two reports, findings that affect scraper/model design
beyond source selection:

- **Third stock-state**: Amazon EU showed listings priced and displayed,
  but flagged *"This item cannot be dispatched to your selected delivery
  location"* — distinct from both `in_stock` and `unavailable`. A crawler
  must not treat a price shown in this state as a confirmed purchasable
  price. Worth a `stock_state` enum (`in_stock` / `unavailable` /
  `undispatchable_to_location`) instead of the implicit two-state model
  scrapers currently use.
- **RAM compatibility is a hard filter, not a spec/sort attribute**:
  server/workstation ECC Registered (RDIMM) memory is electrically
  incompatible with the vast majority of consumer desktop motherboards —
  unlike GPU tiers, which mostly just differ in performance. A `module_type`
  field (`UDIMM` / `RDIMM` / `SODIMM`) should hard-gate RAM matches the same
  way [product_matching.md](product_matching.md)'s category-conflict gate
  already hard-gates a CPU search against a motherboard listing — see that
  doc for the specific addition.
- **Category disambiguation matters more for RAM than GPUs**: a single
  free-text "128GB" search returns full PCs, laptops, storage devices, and
  RAM+motherboard bundles, not just RAM kits — this is exactly the kind of
  bundle/category-conflict problem [product_matching.md](product_matching.md)'s
  `excluded_terms` gate already exists for; RAM-category profiles need a
  richer default exclusion list than the CPU-focused one currently shipped.
- **"Market regime" price-step detection**: the DDR5 scan found a sudden,
  broad, cross-site price step-up not visible in older product reviews on
  the same SKUs — a monthly or slower snapshot cadence would have missed
  the timing of this shift entirely. Reinforces the case for v2.14's daily
  per-site refresh cadence over anything slower for volatile categories,
  and is a candidate input for [v2.19](dashboard_ux.md#3-statistical-price-attributes-volatility-trendgradient--2026-08-21-priority-1-of-5)'s
  trend/gradient indicator (a step-change is a distinct shape from a
  gradual drift, potentially worth its own flag later).
- **New-old-stock (NOS) ambiguity**: EVGA exited the GPU business in 2022,
  so "new" RTX 3090 Ti listings today are unsold old-dated retailer stock,
  not current production — materially affects both price expectations and
  warranty. A `stock_age`/`nos_flag` distinct from `condition=new` is a
  candidate future field, not built yet.
- **Buyer-protection/escrow as a trust signal**: Leboncoin's "Transaction
  sécurisée" badge (and equivalents) changes a listing's practical risk
  profile — worth capturing verbatim if/when any such site is ever
  integrated, though per the table above none of the scanned ones currently
  qualify for automated collection.
- **Shipping-to-Portugal should be captured verbatim, not inferred**: badge
  text/scope was frequently unverifiable from listing metadata alone,
  especially on classifieds. Recommend a `shipping_confirmed_pt`
  tri-state (`true`/`false`/`unknown`) alongside whatever raw shipping text
  is shown, rather than assuming scope from a generic "shipping available"
  flag — feeds v2.9/v2.13's landed-cost work.

**Storage-category findings (SSD/HDD, 2026-08-21 3rd market scan —
`docs/moon/reports/ssd_4tb_hdd_2022tb_market_scan_report.md`):**

- **Two more stock states, both worth persisting rather than discarding**:
  Leboncoin's `"Achat en cours"` (purchase in progress — a buy was
  initiated but may not finalize) and `"Vendu"` (sold). Extends the
  `stock_state` enum above to `in_stock` / `unavailable` /
  `undispatchable_to_location` / `purchase_in_progress` / `sold`. **Design
  principle**: a sold/pending listing's last-shown price is still a real,
  useful historical price-floor data point — the scan's own best evidence
  that sub-budget pricing does occasionally clear came from exactly these
  "sold" rows. A tracked listing (e.g. a v2.15 Tier A custom URL) that
  transitions to `sold`/`purchase_in_progress` should record that final
  price as one last `price_history` observation before the tracker marks
  it inactive, not silently stop without capturing it.
- **Search relevance cannot be trusted for numeric/capacity queries on
  Leboncoin**: free-text search fuzzy-matched "1,5 To" against a "22to"
  query. Not directly actionable today (Leboncoin has no automated
  collection method pending [v2.20](client_side_monitor.md)), but the
  same client-side capacity re-filtering (parse from the listing's own
  title, don't trust search relevance) will matter once that extension
  actually parses Leboncoin pages.
- **Form-factor/interface is a hard filter for SSDs**, same class of
  finding as RAM's `module_type`: SATA vs. NVMe (and PCIe generation
  within NVMe) span a wide price range for the same capacity — see
  [product_matching.md](product_matching.md#category-compatibility-hard-gates-2026-08-21-from-market-scan-findings)
  for the matching addition.
- **Brand is not a reliable tier proxy at high capacities**: Seagate
  BarraCuda (normally consumer-budget) is the *cheapest* 20TB option
  specifically because 20TB+ BarraCuda is manufactured on the same
  nearline platform as Seagate's enterprise lines — a crawler/matcher
  should key on capacity + form factor + interface, not brand-implied
  market tier.
- **External (USB-enclosure) drives are a legitimate, distinct, cheaper
  path to a given capacity** — manufacturers sometimes price the external
  SKU below the equivalent bare internal drive. Capture as its own
  sub-category (an `enclosure`/`interface` value, not excluded from
  results) rather than filtered out as "not a real internal HDD."
- **Condition labels are richer in storage than in GPU/RAM**: "New,"
  "New (Other)," "OEM" (bare/white-label, often ex-datacenter),
  "Recertified" (manufacturer-equivalent warranty), "Refurbished — graded/
  tested/warrantied," and plain "Used" all appeared as materially
  different risk/price tiers, particularly from specialist bulk
  enterprise-HDD resellers. **Design guidance**: keep `condition`'s
  statistical bucket enum coarse (the v2.11 IQR-per-bucket design needs
  enough samples per bucket to be meaningful — more buckets fragments
  that) but capture the seller's own verbatim condition/grading text in
  a separate free-text field alongside it, so a "Recertified, 1-yr
  warranty" listing displays as such to the user even while it's
  statistically pooled with plain "refurb" for anomaly-detection
  purposes. Don't silently collapse the display label; do keep the
  statistical bucket set small.
- **Bulk enterprise-hardware resellers are a recurring, distinct vendor
  class** (seen on both eBay and, per the RAM/GPU scans, elsewhere) with
  pricing/stock patterns that differ from both retail and casual private
  sellers — a candidate input for [v2.16](#site-value-proposition-scoring-v216)'s
  scoring if/when per-seller (not just per-site) granularity is ever
  worth the complexity; not proposed as a v2.16 requirement today.

### Global tier (v2.13) — RAM and other small, low-customs-friction categories

Candidate sources: Newegg (US), Amazon global TLDs (.com, .de already covered
above, .co.uk, others as needed), B&H Photo/Micro Center (US, strong PC-parts
inventory), plus whichever regional retailers turn out to have real RAM
pricing advantages during the current shortage — this list should be driven
by where the actual price data points during v2.13's rollout, not
front-loaded speculatively.

**Landed-cost estimation is required alongside any global-tier source**, not
an optional nice-to-have — a raw foreign-currency price without shipping +
customs/import-VAT + delivery-ETA context is actively misleading, not just
incomplete, for exactly the reason [dashboard_ux.md](dashboard_ux.md#landed-cost-and-delivery-context-v213)
covers. Precise customs/duty calculation is genuinely hard (depends on
declared value, carrier, IOSS pre-collection) — ship an honest **estimate**
labeled as such, not a false-precision number, and never claim a landed cost
as final before actual checkout.

## Custom user-added sites (v2.15)

**Why:** the geographic tiers cover categories of retailers, not genuinely
niche sources — e.g. an NVLink bridge sold almost nowhere in the EU except a
couple of specialized French/German datacenter-hardware stores. No fixed
tier list will anticipate every such case.

**Two tiers, deliberately different scope:**

- **Tier A (v2.15, build first): track a specific product-page URL.** User
  pastes one known listing URL against a tracked product; the tool
  periodically re-fetches *that exact page* and extracts price/stock via the
  same structured-data-first parsing (`application/ld+json` schema.org
  `Product`/`Offer`) already committed to for reliability hardening. No
  search capability needed — directly solves the "I already found the one
  listing" case. New table: `custom_listing_urls` (tracked_product_id, url,
  added_at, last_checked_at, parser_confidence). Goes through the same
  identity-matching, condition-detection, and currency-normalization
  pipeline as every other listing — a custom URL is not a trust shortcut.
- **Tier B (later, more valuable, more fragile): a custom *searchable*
  site.** User provides a search-URL template; a new `GenericScraperAdapter`
  (implementing the existing `ScraperAdapter` protocol) substitutes the
  query and applies the same structured-data-first parsing to extract
  multiple results, not just one page. Keeps discovering new listings on
  that site over time. Explicitly lower-reliability than the purpose-built
  scrapers (no site-specific tuning) — surfaced honestly as such, same
  spirit as the stale-data/circuit-breaker honesty already built into the
  dashboard.

## Site value-proposition scoring (v2.16)

A **four-cell scorecard** per site (or site × product-category × exact
condition), used to help decide whether a custom-added or discovered site
is worth keeping tracked — a ranking/prioritization signal, never a hard
gate, and **not a composite 0–100**. Do not implement a weighted average
of the cells.

**Four independent dimensions** (same principle as keeping v2.14's tiered
and percentile alert modes separate rather than merged):

- **Extreme-value potential**: reuses v2.14's percentile-rank calculation
  on **item sticker** (`price_eur_equivalent`), aggregated per-site
  **inside an exact condition bucket**. Mixed-condition aggregates are
  forbidden (they crown classifieds sites for being surplus-cheap).
- **Consistency**: `median_percentile_rank` (this site's *typical* position
  in the same-condition cross-site sticker distribution) paired with
  `price_volatility` (coefficient of variation of this site's own sticker
  over time). Low volatility + good median rank = a reliable fallback
  while waiting to see if a more volatile, occasionally-spectacular site
  hits a real low.
- **Destination-specific fulfillment SLA**, from declared or observed
  delivery estimates, bucketed (for example express ≤2 days, standard
  3–5 days, extended >5 days). This describes delivery latency, not
  inferred warehouse geography or customs jurisdiction; record its
  source/confidence and aggregate cautiously by site × destination.
  First observation is not a sample — same min-n rule as alerts.
- **Scraper reliability**: circuit-breaker/uptime telemetry (v1.8, v2.6)
  as a fetch-health signal. **Not** seller trust. Kleinanzeigen seller
  ratings are a different object if shown at all.
- Any dimension with too few observations reports as low-confidence rather
  than silently scoring — same minimum-sample-size discipline used
  throughout this roadmap (meaningful-drop, all-time-low, rarity alerts all
  already gate on sample size).

## Per-product source discovery (v2.17)

**Scope discipline first, since this is adjacent to an explicit boundary:**
this stays "find more sources for a product you already track," never
general web/shop indexing — the [scope boundary](../ROADMAP.md#scope-boundaries)
against full catalog indexing is not being softened. Every discovered
candidate goes through the existing identity-matching pipeline (v1.5) before
it's trusted at all, and is surfaced as a suggestion for the user to
approve — never auto-promoted to persistent tracking, generalizing the
existing "KuantoKusta as hint source, verify before trusting" principle
(v2.8) to any discovered source, not just one aggregator.

**Groundwork gap found while scoping this:** v1.1 ("Search-API + scraper
abstraction") is marked ✅ Done, but `src/search/providers/` currently only
has `null_provider.py` — no real SerpAPI/Google CSE implementation exists
yet, despite the credential fields already being present in `Settings`.

**Split:** **v2.17a** implements one real `SearchProvider` (SerpAPI or
Google CSE) behind those keys. **v2.17b** is the discover-and-approve UX
and must not start until v2.17a returns real rows.

**v2.17a shipped 2026-08-21:** `SerpApiProvider` (`src/search/providers/serpapi.py`)
queries Google Shopping (`engine=google_shopping`, `gl=es`/`hl=es`) when
`SERPAPI_KEY` is set, maps `shopping_results` to `RawListing` (`source_kind=
search_api`), and fail-closes to `[]` on transport/HTTP/API/parse errors.
Unconfigured keys are skipped by `enabled_providers()`. Google CSE is still
a commented registry stub. v2.17b (approve-before-persist, host allowlist,
credit budget) is not this slice — `run_discovery` will currently persist
SerpAPI rows through the existing matcher when a key is configured.

**Flow (v2.17b):** initial discovery is strictly **manual and
user-triggered** for one tracked product, never periodic. Query the real
provider for the canonical name + region-relevant terms under a fixed
per-run query/result/page budget **and** a documented **daily
cross-product** API-credit budget (Discover-on-every-watchlist-row in a
loop is a catalog crawl). Filter results for retail-shaped pages —
schema.org `Product`/`Offer` alone is not enough (affiliate spam has it);
require a host allowlist, a known shop family, or a user-confirmed new
host. Run survivors through identity matching; tag each candidate with
`import_regime` from seller destination (not from the product's
`search_scope_tier`); score survivors via v2.16; present them as
time-limited suggestions. The user must explicitly approve a candidate
before it becomes a persistent source. Unapproved candidates expire. A
recurring discovery cadence is a separate future decision after
manual-use cost and noise are measured.

## Retailer priority rationale (v2.7–v2.8)

Per grok's research: Amazon + PcComponentes alone isn't a real comparator for
this market. PCDIGA and Worten/Fnac.pt are next because they're PT-specific and
fill the biggest coverage gap; Chip7 after. KuantoKusta is valuable but
structurally different — it's an aggregator with its own feed-quality/staleness
issues, so it's used to **discover** candidate listings (a URL to go verify),
never to directly populate `price_history` from its own displayed price.
