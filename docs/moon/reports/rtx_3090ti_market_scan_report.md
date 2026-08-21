# RTX 3090 Ti (EVGA-priority) European Market Scan — Crawler Reference Report

**Date of scan:** 21 August 2026
**Target:** EVGA GeForce RTX 3090 Ti (any variant), other brands acceptable, budget < €1,800, EU-wide, deliverable to Portugal
**Purpose of this document:** field notes for building an automated crawler/price-tracker for this product category — what was visited, what each site returns, access constraints, and shipping-to-Portugal status.

---

## 1. Summary table — sites visited

| # | Site | Country / Scope | Site type | New/Used stock found | Cheapest EVGA found | Ships to Portugal? | Crawler access |
|---|------|------------------|-----------|----------------------|----------------------|---------------------|-----------------|
| 1 | amazon.de | Germany (EU-wide shipping) | Retail marketplace | Mostly "Currently unavailable"; 1 buyable SKU | €2,299.99 (K\|NGP\|N) | Yes (confirmed) | Blocked for generic fetchers via robots.txt; browser rendering required |
| 2 | amazon.fr | France (EU-wide shipping) | Retail marketplace | Mostly unavailable; 1 buyable SKU | €2,299.99 (K\|NGP\|N) | Yes (confirmed) | Same as above |
| 3 | amazon.it | Italy (EU-wide shipping) | Retail marketplace | Listings present, stock varies | Not confirmed buyable | Yes (confirmed) | Same as above |
| 4 | amazon.es | Spain (EU-wide shipping) | Retail marketplace | 1 buyable SKU, 2 offers | €1,845.61 (3rd-party "New") | Yes (confirmed) | Same as above |
| 5 | geizhals.de | Germany/Austria, aggregates EU retailers | Price-comparison engine | Aggregated — 6 RTX 3090 Ti SKUs tracked, all brands | €2,299.99 (EVGA, only EVGA SKU tracked) | Depends on underlying merchant | Static-ish HTML, well-structured category/product URLs, no confirmed public API |
| 6 | ldlc.com | France | Retail marketplace | 0 — EVGA 3090 Ti explicitly delisted ("n'est plus disponible") | N/A | N/A (out of stock) | Standard e-commerce HTML, filterable via URL query params |
| 7 | ebay.de | Germany-hosted, sellers worldwide | C2C/B2C marketplace | Multiple used + "New (Other)" listings | €1,215.95 + €192.67 shipping (used, from US) | Yes, but from non-EU sellers (customs/VAT risk) | Official REST API available (Browse API, OAuth) |
| 8 | leboncoin.fr | France (domestic-first) | C2C classifieds | 14 results for "evga rtx 3090 ti"; several new-sealed and used | **€1,000** (used) / €1,400–1,700 (used/new-sealed) | Not guaranteed — shipping option is a French domestic carrier | No public API; anti-bot protections likely (Datadome-style); numeric ad IDs in URL |
| 9 | wallapop.es | Spain (domestic-first) | C2C classifieds | 1 exact EVGA match | €1,300 (used, "Buen estado") | Not confirmed — "Envío disponible" tag present but scope unverified | No public API; SPA (client-side rendered), item IDs in URL slug |
| 10 | subito.it | Italy (domestic-first) | C2C classifieds | 0 EVGA; 3 other-brand 3090 Ti | €1,200 (MSI Suprim X, used) | Not confirmed | No public API; SPA, IP-based search filters |
| 11 | kleinanzeigen.de | Germany (domestic-first) | C2C classifieds | Inconclusive — search 1 blocked our IP range after 2nd query | N/A | Not confirmed | No public API; **aggressive rate-limiting / IP-range bans observed firsthand** |

---

## 2. Detailed site notes

### 2.1 Amazon (.de / .fr / .it / .es)
- **Structure:** Product pages keyed by ASIN (e.g. `/dp/B0B8J2NXRG`), stable across all Amazon EU TLDs — the *same* ASIN often resolves on multiple country domains, useful for cross-country price diffing without re-matching products.
- **Price data:** VAT-inclusive, displayed in-page as plain text (`€1,876.12`) plus a secondary "Other sellers... New (n) from €X" block for marketplace offers — both should be scraped, as the featured offer and the cheapest offer frequently differ (seen: €1,876.12 featured vs €1,845.61 third-party on the same ASIN).
- **Stock state:** Most EVGA SKUs are flagged "Currently unavailable. We don't know when or if this item will be back in stock." — a crawler should treat this as a distinct state from "in stock at price X", not as absence of the product page.
- **Access constraints:** Generic `WebFetch`-style HTTP fetch tools were blocked by `robots.txt` on .de/.fr/.it/.es (429/robots-disallowed errors). A rendering browser (headless Chromium, Playwright/Puppeteer) with a real user agent was able to load pages normally. Expect anti-bot defenses (CAPTCHA, IP throttling) at higher crawl volumes.
- **Shipping:** All four sites showed "Deliver to Portugal" / delivery estimates when the location was set to Portugal — Amazon EU marketplaces ship intra-EU by default.
- **Historical price data:** Amazon itself exposes none natively; third-party trackers (Keepa, CamelCamelCamel) cover amazon.de/.fr/.it/.es and would be the practical route for *historical* price series rather than scraping Amazon directly.

### 2.2 Geizhals.de (price-comparison engine)
- **Scope:** Primarily German/Austrian retailers but includes pan-EU merchants; treat as an aggregator layer, not a single "shop."
- **Structure:** Clean category URLs support server-side filtering, e.g. `https://geizhals.de/?cat=gra16_512&asuch=3090+Ti&sort=p` (category `gra16_512` = PCIe graphics cards, `asuch` = search term, `sort=p` = sort by price). Individual product pages have permanent IDs (`v98609`).
- **Value for a crawler:** Each product page already aggregates multiple merchant offers with live prices ("N Angebote ab €X") — cheaper than crawling each individual German/Austrian retailer separately. Geizhals also has its own price-history charts per product (rendered client-side), which could be scraped as a ready-made historical series instead of building one from scratch.
- **API:** No public/documented API found during this scan; would require either HTML scraping (moderate structure, low obfuscation) or checking for a private/partner data feed.
- **Caveat:** Geizhals explicitly disclaims that listed prices are periodic snapshots and may be stale versus the merchant's live site — worth noting if using it as ground truth.

### 2.3 LDLC.com (France, specialized hardware retailer)
- Confirmed EVGA RTX 3090 Ti models are permanently delisted (LDLC's own UI labels them under "Nostalgeek ? Ces produits ne sont plus disponibles à la vente"). Useful as a *negative signal* source — LDLC could still be crawled periodically to detect if any RTX 3090 Ti (any brand) reappears in their catalog, since filtering by chipset (`fv121-20300`) and brand is URL-parameterized.

### 2.4 eBay.de
- **Structure:** Search results are server-rendered (accessible without JS execution), each listing has a stable numeric item ID visible in the URL, condition (`Neu`, `Gebraucht`, `Neu (Sonstige)`), price, and shipping cost as distinct fields — good for structured scraping.
- **API:** eBay publishes an official **Browse API** (REST, OAuth2 client-credentials flow) that covers search and item detail — this is the recommended integration path over HTML scraping for reliability and to stay within terms of service. Rate limits apply per developer key tier.
- **Cross-border caveat:** The two cheapest EVGA hits shipped from the United States — a crawler surfacing "total price" should add potential import VAT/customs duties for non-EU-origin listings, which eBay's own checkout will calculate at purchase time but is not shown in search-result-level data.
- **Filter used:** `_nkw=<query>&LH_BIN=1&_sop=15` (`LH_BIN=1` = Buy-It-Now only, `_sop=15` = sort by price+shipping ascending) — good default filter set for price-focused crawling.

### 2.5 Leboncoin.fr
- **Structure:** `/recherche?text=<query>` for search, `/ad/<category>/<numeric-id>` for individual ads. Ads carry: condition (`État neuf` / used), price, "dès €X" (price incl. their optional buyer-protection fee), post date, seller name/rating/member-since/response-rate, and an optional "Livraison" (shipping) flag with a starting price (e.g. "dès 2,99 €").
- **Shipping to Portugal:** Not confirmed. Leboncoin's built-in shipping is a French domestic parcel/relay-point network; cross-border shipping to Portugal is not a standard, guaranteed feature and would need per-listing/per-seller confirmation, or the buyer arranging their own forwarding.
- **Buyer protection:** Listings with "Transaction sécurisée" support in-app escrow-style payment; this is a useful field to capture as it changes the practical risk profile of a listing.
- **Access constraints:** No official public API located. The site does not appear to aggressively block a single-session browser crawl (no block encountered during this scan, unlike Kleinanzeigen), but expect anti-bot systems (common on major classifieds sites) to activate at scraping scale — throttle requests and rotate sessions/IPs accordingly.
- **This was the most productive source in this scan** — 14 results for "evga rtx 3090 ti" alone, 7 of them under €1,800, including two at exactly €1,000.

### 2.6 Wallapop.es
- **Structure:** Client-side rendered SPA (`es.wallapop.com/search?keywords=...`); item detail pages live at `/item/<slug>-<numeric-id>`. A crawler needs a JS-executing browser (not a plain HTTP fetch) to get search results — static HTML fetch returned near-empty content in this scan.
- **Data fields available per listing:** title, price, condition (`Buen estado`, etc.), city, seller name, seller rating + review count, "Envío disponible" (shipping available) badge, view count, like count, free-text description (often contains real usage history, e.g. the one EVGA hit described being used for AI inference workloads under undervolt).
- **Shipping to Portugal:** Badge present ("Envío disponible") but scope (Spain-only vs. EU-wide) not verified in this scan; the seller's own listing text for the one EVGA match suggested a preference for in-person handover or "verified users," so shipping willingness may vary seller-to-seller even when the badge is shown.
- **API:** No official public API found; the site's own frontend calls an internal API (visible via browser network inspection) that is undocumented/unofficial and likely subject to change without notice — fragile basis for a long-term crawler.

### 2.7 Subito.it
- **Structure:** `/annunci-italia/vendita/informatica/?q=<query>`, SPA-rendered, similar shape to Wallapop. No EVGA-specific hits in this scan, only other-brand 3090 Ti cards.
- **Shipping to Portugal:** Not confirmed; Italian classifieds shipping options are typically domestic-first with an optional national carrier add-on ("spedizione disponibile").
- **API:** None found publicly.

### 2.8 Kleinanzeigen.de
- **Outcome:** First query (`/s-rtx-3090-ti/k0`) returned only a "Gesuch" (wanted ad, not a sale). A second, more specific query (`/s-evga-3090-ti/k0`) triggered an explicit IP-range block ("IP-Bereich vorübergehend gesperrt") citing suspected abuse — this happened after only two automated requests in short succession.
- **Crawler implication:** This is the most bot-defensive of the classifieds sites encountered. Any production crawler targeting Kleinanzeigen should assume low request-per-minute budgets, session/IP rotation, and realistic pacing (this is consistent with widely reported behavior of the platform, formerly eBay Kleinanzeigen). No official public API exists.

---

## 3. Cross-cutting technical notes for crawler design

- **Currency/VAT:** All observed prices were in EUR, VAT-inclusive on retail sites (Amazon, LDLC) and simply seller-stated on C2C sites (Leboncoin, Wallapop, Subito, Kleinanzeigen, eBay private listings) — no VAT breakdown to parse there.
- **Rendering requirement:** Retail sites (Amazon, LDLC, Geizhals, eBay) are largely scrapeable from server-rendered HTML. C2C classifieds (Leboncoin, Wallapop, Subito, Kleinanzeigen) lean SPA/client-rendered and need a real browser context (headless Chromium) rather than a plain HTTP GET.
- **Anti-bot posture (observed, most→least aggressive):** Kleinanzeigen.de (outright IP ban after 2 requests) > Amazon (`robots.txt` disallow + occasional 429 on non-browser fetches) > Leboncoin/Wallapop/Subito (no block encountered in this small scan, but standard rotate/throttle precautions still advised) > Geizhals/LDLC/eBay (no blocking encountered).
- **Stable product identifiers to key on:** Amazon ASIN, eBay item ID, Geizhals product slug (e.g. `v98609`), Leboncoin/Wallapop/Subito numeric ad ID. None of these IDs are shared across sites, so cross-site matching for the "same" physical listing isn't possible — matching should instead happen at the *product model* level (e.g. "EVGA RTX 3090 Ti FTW3 Ultra" as a canonical key) with each site/listing as a separate observation.
- **"New" vs "Used" vs "New Old Stock" ambiguity:** Since EVGA exited the GPU business in 2022, "new" listings today are old (2022–2023-dated) unsold retailer/reseller stock, not manufacturer-current production — worth a dedicated `stock_age`/`nos_flag` field distinct from plain condition, since it materially affects both price and warranty expectations.
- **Historical pricing:** None of the sites scanned expose first-party historical price charts for individual listings except Geizhals (aggregate product-level history, not per-listing). For genuine time-series tracking, the crawler itself needs to snapshot prices on a recurring schedule and persist them — there's no shortcut via any single site here.
- **Shipping-to-Portugal as a first-class field:** This was inconsistent across sites and often not verifiable from listing metadata alone (especially on C2C classifieds). Recommend capturing whatever shipping badge/text is shown verbatim, plus a `shipping_confirmed_pt: true/false/unknown` field, rather than assuming shipping scope from a generic "shipping available" flag.

---

## 4. Best current leads found in this scan (for reference)

| Listing | Site | Country | Condition | Price | Notes |
|---|---|---|---|---|---|
| EVGA RTX 3090 Ti EVGA | leboncoin.fr | France | Used | €1,000 | La Fare-les-Oliviers |
| EVGA GeForce RTX 3090 Ti FTW3 Ultra Gaming | leboncoin.fr | France | Used | €1,000 | Paris |
| EVGA RTX 3090 Ti FTW3 ULTRA HYBRID | wallapop.es | Spain | Used, "Buen estado" | €1,300 | Zaragoza; seller 4.8★ (14); used for AI inference |
| RTX3090Ti EVGA KINGPIN | leboncoin.fr | France | Used | €1,400 | Voiron |
| EVGA FTW3 RTX 3090 Ti Gaming, sealed | leboncoin.fr | France | New, sealed, invoice provided | €1,600 | Chelles; seller 4.9★ (25), price non-negotiable |
| Carte graphique NEUVE RTX 3090 Ti 24GB (FTW3) | leboncoin.fr | France | New | €1,600 | Coubron |
| EVGA RTX 3090 Ti FTW3 GAMING (used) | ebay.de | Germany (seller in US) | Used | ~€1,409 incl. shipping | Customs/VAT not included |
| EVGA RTX 3090 Ti FTW3 BLACK GAMING (New Other) | ebay.de | Germany (seller in US) | New (Other) | ~€1,419 incl. shipping | Last unit, 27 watchers |
| RTX3090Ti EVGA KINGPIN | leboncoin.fr | France | Used | €1,700 | Voiron |
| Carte graphique NEUVE RTX 3090 Ti Gaming 24GB | leboncoin.fr | France | New | €1,700 | Courtry |

All above are under the €1,800 budget; none had Portugal shipping fully confirmed at time of writing except the eBay.de (US-seller) listings, which ship internationally but may incur import charges not shown in the listed price.
