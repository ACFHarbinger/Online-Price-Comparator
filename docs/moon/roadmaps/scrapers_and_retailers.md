# Scrapers & Retailer Coverage Roadmap

**Status:** ✅ v1.8 reliability hardening complete (including structured-data-first parsing for both original live scrapers — verified 2026-08-21) · ✅ v2.17a SerpAPI SearchProvider (2026-08-21) · 🚧 In progress (5 of ~7 retailers live; Chip7 remains in v2.7) · 📋 Planned (v2.12, v2.13, v2.15, v2.17b) · **Source:** codex research (reliability), grok research (retailer priority); v2.12/v2.13/v2.15-v2.17 from the 2026-08-15 global-scope brainstorm

## Current state

| Site | Status | Notes |
|---|---|---|
| Amazon.es | ✅ Scraper live (`src/scrapers/amazon.py`) | Real prices confirmed via `.a-offscreen` spans; parameterized by domain for future `.fr`/`.de`/`.it`. Intermittent Akamai bot-challenge blocking observed even with realistic headers + rate limiting — see [reliability](#reliability-hardening-v18) below. |
| PcComponentes | ✅ Scraper live (`src/scrapers/pccomponentes.py`) | Consistently blocked by a Cloudflare Turnstile challenge with plain `httpx` — needs the Playwright fallback path (site-allowlisted, see below) before it will return real data. |
| PCDIGA | ✅ Scraper live (`src/scrapers/pcdiga.py`) | PT hardware specialist; JSON-LD first with CSS fallback and polite fail-closed fetch safeguards. |
| Worten | ✅ Scraper live (`src/scrapers/worten.py`) | PT major electronics retailer; JSON-LD first with CSS fallback and polite fail-closed fetch safeguards. |
| Fnac.pt | ✅ Scraper live (`src/scrapers/fnac.py`) | JSON-LD first with CSS fallback and polite fail-closed fetch safeguards. |
| Chip7 | 📋 Planned (v2.7, after PCDIGA/Worten/Fnac) | |
| KuantoKusta | 📋 Planned (v2.8) | Use as a **candidate-URL hint source** only — verify against the real shop before trusting a price, don't persist KuantoKusta's own price as authoritative. |
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
| Mindfactory.de, Alternate.de | New retail | Germany's two largest PC-hardware retailers; frequently undercut Iberian prices on new stock alone, before even considering secondhand. |
| eBay.de | Auction / Buy-It-Now marketplace | Structured-ish listings, seller ratings, often ships EU-wide. Separate scraper from Kleinanzeigen. |
| ebay-kleinanzeigen.de | Local classifieds | **A different site** from eBay.de (do not parameterize one scraper as the other). Where many surplus/datacenter-refresh cards actually surface. Individual-seller, local-pickup common — needs per-listing condition/seller-signal extraction and honest `import_regime` / shipping (often `eu_domestic` + pickup, not a shop SLA). |
| Rebuy, refurbed.de (or equivalent EU refurb marketplaces) | Refurb retail | Structured "refurb" listings (graded condition, dealer warranty) are a lower-risk middle ground between new-retail and individual-seller secondhand — worth prioritizing over raw classifieds where available, since condition/warranty claims are more verifiable. |
| Scan.co.uk, Overclockers UK | New retail | UK is outside the EU customs union post-Brexit but still worth including given it's a major hardware market — landed-cost estimation (below) applies to UK sources the same as non-EU global-tier ones, not treated as EU-frictionless. |

All EU-wide-tier sources need the [multilingual matching](product_matching.md#multilingual-matching-v212)
design for non-English listings, and the [condition field](product_matching.md#condition-as-a-first-class-field-v211)
for the secondhand/refurb sources specifically.

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
