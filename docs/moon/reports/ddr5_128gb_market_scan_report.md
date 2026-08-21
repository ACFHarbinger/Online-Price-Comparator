# 128GB DDR5 Kit European Market Scan — Crawler Reference Report

**Date of scan:** 21 August 2026
**Target:** 128GB DDR5 desktop memory kit, budget ~€1,000, EU-wide, deliverable to Portugal
**Purpose of this document:** field notes for an automated crawler/price-tracker for this product category — what was visited, what each site returns, access constraints, and a critical market-context finding that changes how this budget should be read.

---

## 0. Headline finding — read this first

**A €1,000 budget for a new 128GB DDR5 kit is not currently achievable anywhere checked in this scan.** DRAM prices spiked sharply through 2025–2026 (widely attributed to AI-datacenter memory demand pulling supply away from consumer channels). Multiple independent signals confirmed this during the scan:

- Geizhals (DE/AT price-comparison engine) shows the **cheapest of 38 tracked 128GB DDR5 kits, any brand, at €1,799.00** — roughly double-to-triple the per-GB pricing implied by older Amazon reviews on the same SKUs (customers who bought the same Kingston/Crucial kits in 2023–2024 reported $400–600 USD; one Japanese Amazon reviewer noted a specific 128GB kit going from ¥56,380 in July 2025 to a price they called unaffordable by March 2026; a French reviewer wrote "achetée en cette période d'infamie des prix" — "bought in this era of scandalous prices").
- Amazon .de/.fr/.it/.es: most 128GB kits are either flagged "Currently unavailable" / "cannot be dispatched to your selected delivery location," or priced €1,845–€2,130 where actually buyable.
- eBay.de: cheapest 128GB listing found was €1,040.61 + €55.33 shipping (≈€1,096 total) for **ECC Registered (RDIMM) server memory**, not standard desktop UDIMM — see compatibility caveat below.
- Even the **used/private-seller market reflects the new-retail price level**, not pre-shortage pricing — most secondhand 128GB DDR5 listings on Leboncoin.fr and Wallapop.es cluster in the €1,600–€2,000 range, since sellers are pricing against current replacement cost.

The one credible match found under €1,000 is a used/private listing (below). Treat any "new, ~€1,000, 128GB DDR5" listing found elsewhere with suspicion until verified — at current market pricing it is more likely mispriced, a scam, or a different product (e.g., SO-DIMM laptop memory mislabeled, or ECC server memory needing an incompatible motherboard) than a genuine bargain.

---

## 1. Summary table — sites visited

| # | Site | Country / Scope | Site type | Cheapest 128GB DDR5 found | Condition | Ships to Portugal? | Crawler access |
|---|------|------------------|-----------|------------------------------|-----------|---------------------|-----------------|
| 1 | amazon.de | Germany (EU-wide shipping) | Retail marketplace | Kingston Fury Beast 128GB (4x32GB) 5600MT/s — "cannot be dispatched to your selected delivery location" | New (blocked for PT) | No (this SKU) | Browser rendering required; robots.txt blocks generic fetchers |
| 2 | amazon.fr | France (EU-wide shipping) | Retail marketplace | Corsair Vengeance 128GB (4x32GB) 5600MHz — "Currently unavailable" | N/A (OOS) | N/A | Same as above |
| 3 | amazon.it | Italy (EU-wide shipping) | Retail marketplace | Corsair Vengeance RGB 128GB (4x32GB) 5600MHz — listed, price not confirmed buyable in this scan | New | Presumed yes | Same as above |
| 4 | amazon.es | Spain (EU-wide shipping) | Retail marketplace | Corsair Vengeance 128GB (2x64GB) up to 6400MHz — **€2,129.62** (in stock) | New | Yes (confirmed) | Same as above |
| 5 | geizhals.de | Germany/Austria, aggregates EU retailers | Price-comparison engine | Corsair Vengeance RGB 128GB (2x64GB) DDR5-6000 CL40 — **€1,799.00** (cheapest of 38 tracked SKUs) | New | Depends on merchant | Structured category/filter URLs; no public API found |
| 6 | ldlc.com / materiel.net | France | Retail marketplace | Not price-checked directly this scan (found via search only) | New | Presumed yes | Standard e-commerce HTML |
| 7 | ebay.de | Germany-hosted, sellers worldwide | C2C/B2C marketplace | Kingston Fury Renegade Pro 128GB (8x16GB) ECC RDIMM — **€1,040.61 + €55.33 shipping** (from Newegg via eBay, US) | New | Yes, but non-EU origin (customs/VAT risk) | Official Browse API available |
| 8 | leboncoin.fr | France (domestic-first) | C2C classifieds | **128GB Ram Corsair Dominator (4x32GB, Dominator Platinum DDR5-5200 CL40) — €900** | Used, "Très bon état" | Not guaranteed (domestic carrier) | No public API; numeric ad IDs |
| 9 | wallapop.es | Spain (domestic-first) | C2C classifieds | 128GB Crucial DDR5 5600MHz SODIMM — €2,000 (no sub-€1,000 128GB kit found) | Used | Not confirmed | No public API; SPA |

---

## 2. Detailed site notes

### 2.1 Amazon (.de / .fr / .it / .es)
- Same structural notes as prior GPU scan apply: ASIN-keyed product pages, VAT-inclusive pricing, robots.txt blocks generic fetch tools (browser rendering required), "Deliver to Portugal" shown when purchasable.
- **New this scan:** several 128GB SKUs show a specific failure mode not seen with the GPU — *"This item cannot be dispatched to your selected delivery location. Please choose a different delivery location"* — distinct from "Currently unavailable." This indicates the SKU exists and may even show a price in a size/style selector, but is not actually purchasable to Portugal from that listing. A crawler should treat this as a third stock-state (`undispatchable_to_location`) alongside `in_stock` and `unavailable`, and should not treat a price visible in a variant selector as a confirmed purchasable price without checking the "Add to Cart"/"Buy Now" state.
- Prices seen for 128GB kits ranged from ~€968 (a stale/undispatchable variant price, Crucial 2x64GB on amazon.de — **not actually purchasable**) up to €2,129.62 (Corsair 2x64GB 6400MHz, in stock, amazon.es). This spread illustrates why a crawler must always confirm purchasability, not just scrape a displayed number.

### 2.2 Geizhals.de (price-comparison engine)
- Same mechanics as the GPU scan (category/filter URL params, aggregated multi-merchant offers, per-product price-history charts, periodic-snapshot disclaimer).
- **Filter note:** the RAM category's filter query-string codes (`xf=...`) are non-obvious and attempts to guess them (e.g. `xf=1454_DDR5~253_128+GB`) silently fell back to an unfiltered "all RAM sorted by price" result rather than erroring — a crawler should discover valid filter codes by inspecting the rendered filter sidebar's own links/checkboxes rather than guessing the query string, or should filter client-side using the "Standard"/"Kapazität"/"Datenmenge pro Modul" facets exposed per-product in results.
- A free-text `asuch=` (search-within-category) parameter worked reliably and is the simplest scrape path: `https://geizhals.de/?cat=ramddr3&asuch=128GB+Kit+DDR5&sort=p` (note: `cat=ramddr3` is Geizhals's actual category code for the general RAM/Speicher category, despite the name).
- This search returned 38 structured product cards, each with brand, exact part number, form factor, module count/size, data rate, CAS latency, voltage, ECC type, and current cheapest offer price — a clean, low-effort structured source for tracking this category's price floor over time.

### 2.3 eBay.de
- Same mechanics as GPU scan (stable item IDs, condition field, `LH_BIN=1&_sop=15` for Buy-It-Now sorted by price+shipping, official Browse API recommended over scraping).
- **New observation:** search results for this category are dominated by (a) US-origin new stock at elevated prices, (b) "Aufrüstkit" bundles (RAM + motherboard + cooler as a package, sometimes cheaper per-GB but not a pure RAM purchase — a crawler should detect and separately flag bundle listings vs. standalone RAM), and (c) server/ECC RDIMM kits which are **not drop-in compatible with a standard consumer desktop motherboard** — a crawler targeting "RAM for a normal desktop build" must filter out `RDIMM`/`ECC Registered` listings, or tag them distinctly, since they require a server/workstation-class board (e.g. Threadripper Pro, Xeon W, EPYC) to function at all.
- One used/private listing stood out as priced well below the new-stock cluster: "128GB (32GB x4) Kingston FURY Beast KF556C40BBAK4-128" — €1,217.51 + ~€65.05 shipping from a UK private seller, "Neu" (new) condition per listing but sold by a private individual rather than a retailer.

### 2.4 Leboncoin.fr
- Same mechanics as GPU scan (numeric ad IDs, condition field, seller rating/verification, optional "Livraison" shipping starting at ~€2.49–2.99, "Transaction sécurisée" buyer protection).
- This was again the most productive source for anything close to budget: 18 results for "128gb ddr5," ranging from €900 (the best match, detailed below) up to €4,000 (a laptop with 128GB RAM, not a standalone kit — a crawler should exclude full-system listings by checking whether the ad's own category is "Accessoires informatique" vs. "Ordinateurs").
- **Best match found, full detail:** "128GB Ram Corsair Dominator" — €900 (buy-now) / listing shows "dès 901,99 €" with buyer-protection fee included. Description (seller's own words, translated): "Selling due to CPU change. 4 sticks Corsair Dominator Platinum DDR5 32GB 5200MHz 40-40-40-77, 128GB total." Condition: "Très bon état" (very good condition). Seller "admlux," member since November 2015, marked "Réactif" (responsive) and phone-number-verified, located in Bagnols-en-Forêt. Listed 16 March 2026 (~5 months old at time of scan — worth confirming it's still available before relying on it). Shipping available from €2.49; in-person handover also offered.
- Other near-budget paths on this same site involved combining two 64GB kits (e.g., two listings around €500–€650 each) to reach 128GB — cheaper in aggregate than most single 128GB listings, but carries real risk: two separately-sourced kits are not guaranteed to be the same revision/binning and may not run stably together at rated speed/timings (this exact failure mode was reported in several Amazon reviews of 4-DIMM 128GB kits in the GPU/RAM scans generally). Flag this as a distinct "assembled-from-parts" match type, not equivalent to a matched-set kit.

### 2.5 Wallapop.es
- Same mechanics as GPU scan (SPA, JS rendering required, `/item/<slug>-<id>` detail pages, condition/seller-rating/shipping-badge fields).
- No standalone 128GB DDR5 kit was found near €1,000 in this scan; the only close match was "128GB Crucial DDR5 5600MHz SODIMM RAM" at €2,000, consistent with the broader price-spike finding. Most other results in the search were full pre-built PCs or laptops with 128GB storage (SSD), not 128GB of RAM — a crawler must disambiguate "128GB" applied to RAM vs. storage in free-text listing titles, since Wallapop's own search does not separate these.

---

## 3. Cross-cutting technical notes for crawler design (delta from the GPU scan)

- **New stock-state to model:** beyond `in_stock` / `unavailable`, Amazon showed a third state — *listed with a price, but undeliverable to the buyer's selected country* — which must not be conflated with either of the other two.
- **Category disambiguation is now load-bearing, not cosmetic:** with GPUs, "is this actually the product" was mostly unambiguous. With RAM, a single free-text search returns full PCs, laptops, storage devices, and RAM-plus-motherboard bundles all matching "128GB" — a crawler needs stronger structured filtering (module count, form factor DIMM vs. SO-DIMM, "kit" vs. "bundle") to avoid false matches, more so than in the GPU category.
- **ECC/RDIMM vs. UDIMM is a hard compatibility fork, not just a spec variant:** unlike GPU tiers (which mostly differ in performance), RDIMM/ECC Registered 128GB kits are **electrically and functionally incompatible** with the vast majority of consumer desktop motherboards. A crawler serving a "will this work in my PC" use case should treat `module_type` (UDIMM vs. RDIMM/SODIMM) as a hard filter dimension, not a sort/display attribute.
- **Price volatility warrants a "market regime" flag:** because this scan found a sudden, broad, cross-site price step-up versus what's implied by even recent (2025) product reviews on the same exact SKUs, a serious price-tracking crawler for this category should snapshot frequently enough (e.g., daily) to detect and flag step-changes in the category price floor, not just gradual drift — a monthly snapshot cadence would have entirely missed this shift's timing.
- **Everything else** (rendering requirements, anti-bot posture ranking, stable product identifiers, VAT/currency handling, lack of native historical-price data on any site except Geizhals's aggregate charts) carries over unchanged from the prior GPU-market report and is not repeated here.

---

## 4. Best current leads found in this scan (for reference)

| Listing | Site | Country | Condition | Price | Notes |
|---|---|---|---|---|---|
| 128GB Ram Corsair Dominator (4x32GB, Dominator Platinum DDR5-5200 CL40) | leboncoin.fr | France | Used, "Très bon état" | **€900** | Best match under budget; seller verified/responsive; listing ~5 months old, confirm availability |
| Kingston Fury Renegade Pro 128GB (8x16GB) ECC RDIMM DDR5-5600 | ebay.de (Newegg, US) | Germany listing / US origin | New | €1,040.61 + €55.33 shipping ≈ €1,096 | **Server ECC RDIMM — requires compatible workstation/server motherboard, will not work in a standard consumer desktop** |
| Kingston FURY Beast 128GB (4x32GB) KF556C40BBAK4-128 5600MT/s | ebay.de (UK private seller) | Germany listing / UK origin | New (private seller) | €1,217.51 + ~€65.05 shipping ≈ €1,283 | Private seller, not a retailer — no formal retail warranty path |
| Corsair Vengeance RGB 128GB (4x32GB) 5600MHz CL40 | ebay.de (Austria, private) | Austria | New | €1,350 + €15 shipping ≈ €1,365 | |
| Corsair Vengeance RGB 128GB (2x64GB) DDR5-6000 CL40 (CMH128GX5M2D6000C40) | Geizhals-tracked retailer | Germany/Austria | New | **€1,799.00** | Cheapest new/retail 128GB kit found anywhere in this scan |
| Corsair Vengeance 128GB (2x64GB) up to 6400MHz CL42 | amazon.es | Spain | New, in stock | €2,129.62 | Confirmed purchasable, ships to Portugal |

**Bottom line:** at current European market prices, closing on a genuine 128GB DDR5 kit near €1,000 realistically means either the €900 Leboncoin used listing (subject to it still being available and the usual private-sale caveats — verify seller, inspect/test before paying, use Leboncoin's buyer protection), or accepting a compromise: buying two separate 64GB kits used (~€500–650 each, several available on Leboncoin) to reach 128GB with matched-set risk, or waiting out the current DRAM price spike if the purchase isn't urgent.
