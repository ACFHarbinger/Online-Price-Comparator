# Scrapers & Retailer Coverage Roadmap

**Status:** 🚧 In progress (2 of ~7 retailers live) · **Source:** codex research (reliability), grok research (retailer priority)

## Current state

| Site | Status | Notes |
|---|---|---|
| Amazon.es | ✅ Scraper live (`src/scrapers/amazon.py`) | Real prices confirmed via `.a-offscreen` spans; parameterized by domain for future `.fr`/`.de`/`.it`. Intermittent Akamai bot-challenge blocking observed even with realistic headers + rate limiting — see [reliability](#reliability-hardening-v18) below. |
| PcComponentes | ✅ Scraper live (`src/scrapers/pccomponentes.py`) | Consistently blocked by a Cloudflare Turnstile challenge with plain `httpx` — needs the Playwright fallback path (site-allowlisted, see below) before it will return real data. |
| PCDIGA | 📋 Planned (v2.7, next priority) | PT-based hardware specialist. |
| Worten | 📋 Planned (v2.7) | PT major electronics retailer. |
| Fnac.pt | 📋 Planned (v2.7) | |
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
- **Structured-data-first parsing**: prefer `application/ld+json` or embedded JSON
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

## Retailer priority rationale (v2.7–v2.8)

Per grok's research: Amazon + PcComponentes alone isn't a real comparator for
this market. PCDIGA and Worten/Fnac.pt are next because they're PT-specific and
fill the biggest coverage gap; Chip7 after. KuantoKusta is valuable but
structurally different — it's an aggregator with its own feed-quality/staleness
issues, so it's used to **discover** candidate listings (a URL to go verify),
never to directly populate `price_history` from its own displayed price.
