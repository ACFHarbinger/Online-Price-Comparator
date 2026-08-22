# Client-Side Monitor (Browser Extension) Roadmap

**Status:** 🚧 In progress (v2.20) — v0/v1 infra shipped 2026-08-21/22 (content script, JSON-lines + localhost-callback handoff, loopback-enforced, `collection_method` column). **Scope decision, 2026-08-22 (Harbinger)**: every tracked site gets a client-extension content script, not just Leboncoin — rollout order **PT/ES first, then FR, then DE, then the rest**. **PT/ES + FR + DE tiers shipped 2026-08-22**, and the **"others" tier (minus eBay.de) shipped 2026-08-22** (Scan.co.uk, Overclockers.co.uk, Newegg added to `SITES` + `manifest.json`). **eBay.de intentionally excluded** pending a Harbinger decision (the roadmap flags eBay's official Browse API as the likely better mechanism). All patterns remain code-only/unverified against live pages; `site_fallbacks.js` stays empty. No site is flipped to `client_extension` yet — `server_scrape` stays the default per site until each script is verified working. See [Scope expansion](#scope-expansion-2026-08-22-every-site-not-just-leboncoin) below · **Source:** direct user request, 2026-08-21 —
un-parks `ROADMAP.md`'s "Browser extension / userscript" Parked row under a
new, much more specific motivation than the original entry's "real UX win."

## Scope expansion (2026-08-22): every site, not just Leboncoin

Harbinger's call: `client_extension` becomes the collection method for
**every** tracked site except where a better mechanism already exists
(SerpAPI's `search_api`, KuantoKusta's `hint_only`) — not only the sites
whose ToS specifically objects to server-side automation. This is a
different (bigger) rationale than v2.20's original motivation, worth
stating plainly: browser-based collection also sidesteps this repo's two
worst *reliability* problems (Amazon.es's intermittent Akamai challenge,
PcComponentes's Cloudflare Turnstile block — both documented in
[Reliability hardening](scrapers_and_retailers.md#reliability-hardening-v18)
as unsolved without the still-off-by-default Playwright fallback), reduces
server-side request volume across the board, and gets fresher data for
free whenever the user is naturally browsing a tracked listing. Existing
`scrapers/` adapters are **not removed** — `collection_method` still
defaults to `server_scrape` per site until its extension content script
actually ships and is flagged over, so there's no coverage gap mid-rollout.

**Rollout priority** (build order, not a hard gate — land and flip each
site's `collection_method` as its script ships, don't batch a whole tier):

1. **Portugal + Spain**: Amazon.es, PcComponentes, PCDIGA, Worten, Fnac.pt,
   Chip7, Wallapop.es (Wallapop was already approved server-side/Tier-A-only
   on 2026-08-21 — extension coverage is additive here, not a policy
   change), KuantoKusta (stays `hint_only`, no extension needed — it never
   becomes a price source, see v2.8).
2. **France**: LDLC.com, Leboncoin.fr (done).
3. **Germany**: Mindfactory.de, Alternate.de, Geizhals.de, Kleinanzeigen.de.
4. **Others**: Scan.co.uk, Overclockers UK, Newegg (global tier) — shipped
   2026-08-22. **eBay.de decided 2026-08-22 (Harbinger): `search_api`, not
   `client_extension`** — eBay's official Browse API (OAuth2
   client-credentials) is purpose-built for this, same shape as v2.17a's
   `SerpApiProvider`. Not yet implemented; see
   `scrapers_and_retailers.md`'s eBay.de row.

**Technical approach — generalize, don't duplicate per site.** Leboncoin's
`content.js` (`findProduct`/`extractSnapshot`) already reads generic
schema.org `Product`/`Offer` JSON-LD, the same structured-data-first
preference every Python scraper uses — only `site_key="leboncoin"` and
`manifest.json`'s `host_permissions`/`matches` are Leboncoin-specific. The
right shape for N sites is **one shared content script** whose site_key
derives from `window.location.hostname`, with `manifest.json`'s
`host_permissions`/`content_scripts.matches` listing every site's known
listing-page URL pattern (one array, added to per tier) — not N
near-duplicate files. Per-site CSS-selector fallback (for a site whose
listing pages lack complete JSON-LD) stays a small per-site module,
mirroring how `scrapers/retailer_base.py` already splits shared plumbing
from per-site fallback parsing. Reuse that Python-side fallback logic's
*shape*, not the code itself (different language) — same design
discipline, not a shared file.

## Why this exists: a legal/ethical distinction, not a technical workaround

Harbinger researched Leboncoin's actual posture on automated monitoring
(see [#37](https://github.com/ACFHarbinger/Online-Price-Comparator/issues/37))
and found a real, substantive distinction — not a loophole — between two
things that look similar but aren't:

- **Server-initiated automated polling**: OPC's backend (`src/scrapers/`,
  `src/pipeline/`) makes an HTTP request to a target site on its own
  schedule, from a process the target site never invited. This is what
  Leboncoin's `robots.txt` and terms-of-service text object to — a bot
  acting as an independent actor against the site.
- **Client-initiated local monitoring, executed from the user's own
  browser session**: the same detection outcome ("did this listing's
  price change"), but the check happens as a real page load in the user's
  own browser, at a cadence gated by the browser actually being open —
  structurally the same thing as "a human who refreshes the page, but
  faster" (the framing Harbinger's research used). This is the same
  mechanism legitimate commercial products (Distill Web Monitor,
  Visualping) use specifically because it sits in a different, more
  defensible category — under French law as researched, extracting a
  non-substantial portion of public data (a single tracked listing) this
  way is not the same act as bulk/automated extraction.

**This is a per-site collection-method decision, not a general replacement
for scraping.** Most of this tool's sources (Amazon.es, PcComponentes, the
PT retailers, Mindfactory/Alternate, SerpAPI) have no stated objection to
ordinary polite server-side requests and stay exactly as they are. This
feature exists specifically to unlock sites whose own stated terms draw
the line at server-initiated automation — Leboncoin.fr is the concrete
motivating case, found and decided via #37.

## Design

### New per-site `collection_method`

Extends `site_settings` (or a new column there): `server_scrape` (today's
default — `scrapers/` registry adapter) / `client_extension` (this
feature) / `search_api` (v2.17a) / `hint_only` (v2.8's KuantoKusta
pattern). A site's `collection_method` determines which pipeline path is
even allowed to touch it — `pipeline.discover`/`pipeline.refresh` must
never fall back to server-side scraping for a `client_extension`-flagged
site just because the extension hasn't reported in recently. No silent
downgrade to a more aggressive collection method.

### Extension architecture

1. **Content script**, injected only into tabs matching a tracked
   listing's own URL (from v2.15's `custom_listing_urls`, or a future
   `client_extension`-specific tracked-URL table if that turns out
   cleaner) — never a general-purpose page scraper injected everywhere.
2. **DOM read, not a network request**: reads the specific price/title/
   stock elements already rendered in the page the user's browser loaded
   — same structured-data-first preference (JSON-LD `Product`/`Offer`)
   this tool already uses server-side, CSS-selector fallback only if
   needed, mirroring `AGENTS.md` §5's existing scraper pattern so the
   parsing logic is genuinely shared/portable, not reinvented for the
   extension.
3. **Local snapshot + diff**: the last-seen value is stored in the
   extension's own local storage (`chrome.storage.local` / IndexedDB) and
   compared on each check. Only a detected *change* produces any outbound
   activity toward OPC — this also happens to minimize load on the
   tracked site, a secondary but real benefit of the same design.
4. **Check cadence**: a background tab reload at a conservative interval
   (reuse `site_settings.min_refresh_interval_hours`, the same field
   v2.14's per-site tick-script reads, so there's one source of truth for
   "how often is this site allowed to be touched," not two divergent
   cadence configs) — but the check **only runs while the user's own
   browser is open and the extension active**. No headless/background
   server process drives it; that's the whole point. This is a natural,
   honest rate limit, not a workaround to simulate one.
5. **Reporting back to OPC** — recommend the simpler of two options for
   v0, matching this tool's existing "tick script, not a daemon"
   philosophy (v2.2, v2.14):
   - **v0 (recommended first): local file handoff.** The extension
     appends detected changes to a JSON-lines file in a well-known local
     directory (e.g. via the browser's native-messaging or downloads API,
     or a file the user points the extension at once during setup). OPC's
     existing `cli refresh` reads and imports any new lines on its next
     run, through the *same* identity-matching → condition-detection →
     FX-normalization → `persist_snapshot` pipeline every other source
     uses — an extension-sourced observation is not a trust shortcut
     either, same principle already established for v2.15 Tier A.
     Decoupled: works even if the Dash dashboard process isn't running
     when a check happens.
   - **v1 (later): local HTTP callback.** A `localhost`-bound endpoint on
     the existing Dash app's underlying Flask server (Dash *is* Flask)
     the extension POSTs to directly for near-real-time dashboard updates.
     Only worth building once v0 proves the detection/parsing side works;
     adds a new network surface (even if localhost-only) this tool
     otherwise doesn't have, so it's deliberately not the starting point.
6. **Manifest V3, minimal permissions**: `activeTab` + host permissions
   scoped only to the specific domains that actually have a
   `client_extension`-flagged tracked URL, not a blanket `<all_urls>` —
   this is a personal tool, the extension should ask for exactly what it
   needs and nothing that would read as a general-purpose scraper to
   someone reviewing the permission list.

### Explicitly not this feature

- Not a general web-scraping engine — content-script logic is scoped to
  the same handful of known-tracked URLs the rest of this tool already
  tracks via v2.15, not arbitrary pages.
- Not a way to bypass a site that has actually IP-banned or CAPTCHA-gated
  the user's own browsing (Kleinanzeigen's observed behavior) — if a
  site blocks the user's own normal browsing, that block applies to the
  extension too; this feature doesn't attempt evasion of any kind, same
  standing rule as [Reliability hardening](scrapers_and_retailers.md#reliability-hardening-v18).
- Not a replacement for `client_extension` being a deliberate, per-site,
  documented decision — a site doesn't get this treatment by default;
  it's the exception path for sites whose own terms specifically object
  to server-initiated automation but not to user-initiated browsing,
  same reasoning Leboncoin's case established.

## Sequencing

Depends on v2.15 Tier A (custom-URL tracking, done — #32) for the
identity-matching/condition/FX pipeline the extension's reported
observations flow through. Not gated on anything else currently planned.
The first real use case is unblocking Leboncoin.fr per #37, once this
lands and Harbinger confirms Leboncoin should be flagged
`collection_method = client_extension`.
