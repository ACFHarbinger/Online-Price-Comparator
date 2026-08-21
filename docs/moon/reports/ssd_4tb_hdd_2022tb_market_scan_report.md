# 4TB SSD (~€400) & 20–22TB HDD (~€400) European Market Scan — Crawler Reference Report

**Date of scan:** 21 August 2026
**Targets:** (A) 4TB SSD, budget ~€400; (B) 20–22TB HDD, budget ~€400. EU-wide, deliverable to Portugal.
**Purpose of this document:** field notes for an automated crawler/price-tracker for these two categories — what was visited, what each site returns, access constraints, and how each budget stacks up against current market reality.

---

## 0. Headline finding — read this first

**The two targets sit on opposite sides of feasibility right now.**

- **4TB SSD at ~€400: easily achievable, multiple options, some well under budget.** SATA 4TB drives start around €329, and 4TB NVMe (the more useful format for a modern desktop/workstation) is available from €399 new-retail. This category has **not** seen the kind of price spike hitting RAM and (to a lesser extent) HDDs this cycle.
- **20–22TB HDD at ~€400: not achievable new, and only marginally achievable used.** Cheapest new 20TB HDD tracked was **€726**; cheapest new 22TB was in the €700s–€1,100 range. Nearline/enterprise HDD prices have also risen sharply through 2025–2026 (the same AI-datacenter storage demand story behind the DDR5 spike reported in the prior RAM scan, plus reports of coordinated manufacturer capacity cuts). The closest match to budget found was a **used, private-seller 22TB WD OEM drive at €500 + €35 shipping (≈€535)** — about 34% over target. Genuinely sub-€400 22TB listings were spotted on the secondhand market but had already sold by the time of this scan, which is itself useful signal (see §2.4).

---

## 1. Summary table — sites visited

| # | Site | Country / Scope | Site type | Cheapest 4TB SSD found | Cheapest 20–22TB HDD found | Ships to Portugal? | Crawler access |
|---|------|------------------|-----------|--------------------------|------------------------------|---------------------|-----------------|
| 1 | geizhals.de | Germany/Austria, aggregates EU retailers | Price-comparison engine | **€329.00** (TeamGroup T-Force Vulcan Z, SATA, 4TB) | **€726.34** (Seagate BarraCuda 20TB, SATA) | Depends on merchant | Structured `asuch=` search works well; no public API |
| 2 | ebay.de | Germany-hosted, sellers worldwide | C2C/B2C marketplace | Not price-checked this scan (Geizhals covered new-retail sufficiently) | **€500 + €35 shipping ≈ €535** (WD 22TB OEM, new-other, private seller) | Yes, seller-dependent | Official Browse API available |
| 3 | leboncoin.fr | France (domestic-first) | C2C classifieds | Not searched this scan | Two sub-€400 matches found but marked **"Vendu" (sold)** — see §2.4 | Not guaranteed (domestic carrier) | No public API |

Amazon (.de/.fr/.it/.es) was not individually re-checked line-by-line in this scan — Geizhals's aggregation (which itself pulls from many German/Austrian/EU retailers, Amazon marketplace offers included in some categories) was used as the primary structured price-floor source given the clear headline finding didn't need per-country Amazon confirmation to establish. If precise Amazon buyability/shipping-to-Portugal confirmation is needed for a specific SKU, that still requires the direct browser-rendered check used in prior scans (robots.txt blocks generic fetchers on all four Amazon EU TLDs, as established previously).

---

## 2. Detailed site notes

### 2.1 Geizhals.de — 4TB SSD
- Query used: `https://geizhals.de/?cat=hdssd&asuch=4TB+SSD&sort=p` (category `hdssd` = the general SSD category; `asuch=` free-text search-within-category, same pattern as the RAM scan). Returned 187 products across SATA and NVMe.
- **Cheapest overall: TeamGroup T-Force Vulcan Z QLC, 2.5" SATA, 4TB — €329.00** (8 offers), well under budget.
- **Cheapest NVMe (the more broadly useful format — usable in both desktops and most modern laptops, and much faster): Crucial P310, M.2 2280, PCIe 4.0 x4, 4TB — €399.00** (down 6% at time of scan, 26 offers), right at the €400 mark. Close behind: Lexar NQ790 4TB NVMe at €399.88, Kingston NV3 4TB NVMe at €419.90 (47 offers — most-offered SKU in the category, a good liquidity signal).
- Mid-range SATA options (Crucial BX500 4TB at €369.99, 30 offers) sit comfortably inside budget with more headroom than the NVMe options.
- No sign of the RAM-style price spike in this category — pricing looks like normal SSD market pricing, with clear price/performance tiers (SATA cheapest, mainstream PCIe 4.0 NVMe mid-range, PCIe 5.0 NVMe and enterprise U.2/SAS drives far more expensive, topping out at €2,184 for a Kingston enterprise U.2 drive in the same result set — not relevant to this budget but worth excluding via an interface/form-factor filter in a crawler).

### 2.2 Geizhals.de — 20TB HDD
- Query used: `https://geizhals.de/?cat=hde7s&asuch=20TB&sort=p` (category `hde7s` = HDD category). Returned 24 products, all 3.5" enterprise/NAS-class drives (no consumer desktop-class 20TB drives exist at retail — 20TB+ is exclusively a nearline/enterprise/NAS tier right now).
- **Cheapest: Seagate BarraCuda 20TB, SATA — €726.34** (27 offers). This is notable because BarraCuda is normally Seagate's consumer desktop line, but at 20TB it's really a rebadged nearline drive — worth flagging in a crawler as a "consumer-branded but enterprise-tier" edge case.
- Next cheapest: Toshiba Cloud-Scale Capacity MG11ACA 20TB at €778.00, WD Ultrastar DC HC555 20TB (SAS) at €795.00.
- All 24 results are €726–€1,082 — there is no sub-€700 new 20TB drive tracked by Geizhals at scan time.
- A companion search for `asuch=22TB` (not run in full in this scan, but 22TB pricing surfaced via eBay — see below) is expected to land in a similar or slightly higher band given eBay new-retail 22TB prices seen were €700s–€1,100+.

### 2.3 eBay.de — 22TB HDD
- Query used: `_nkw=22TB HDD Exos` with `LH_BIN=1&_sop=15` (Buy-It-Now, price ascending) — same filter pattern as prior scans. 14 direct results plus a broader "fewer keywords" fallback section eBay appends when an exact-match set is small.
- Pricing landscape: new drives (mostly Seagate Exos X22, shipped from China) clustered **€744–€795**; a UK "recertified" (manufacturer-refurbished-equivalent, sold with a 1-year warranty) Seagate 22TB was **€583.36 + €49.67 shipping ≈ €633**; a UK "Refurbished — Hervorragend" (excellent-grade pulled/tested) Seagate Exos X22 SAS was **€701 + €55 ≈ €756**.
- **Best match found: "Western Digital Interne Festplatte 22 TB * 7200rpm * SATA *oem" — €500 + €35 shipping ≈ €535, "Neu (Sonstige)" (new-other), private seller.** This is the closest any listing came to the €400 target across both new and used channels for this capacity tier. "OEM" in the title suggests a bare/white-label drive (likely pulled from a data-center deployment or sold without full retail packaging) rather than a boxed retail unit — worth noting as a distinct condition/provenance category, not equivalent to "new retail."
- A general market-context observation: the eBay 22TB result set is dominated by China-origin new drives and a handful of specialist EU refurbishers (UK-based `dynamix-solutions-de`, `bargain*hardware`, `hdd-store-ref`) who deal in server-pull enterprise HDDs at scale — this vendor type (bulk enterprise-HDD refurbisher) is a distinct and recurring category worth a crawler treating as its own vendor class, since their pricing and stock patterns differ from both retail and casual-private-seller listings.

### 2.4 Leboncoin.fr — 20/22TB HDD
- Query used: `text=disque dur 20to OR 22to` — note the site's search does not reliably respect boolean `OR` syntax; the result set was a mix of genuine 20TB/22TB matches and irrelevant 1.5TB drives (the search engine appears to fuzzy-match "1,5 To" against "22to" on some token-overlap basis) — a crawler should not trust this site's search relevance and should instead filter client-side on capacity extracted from each listing's own title.
- 17 total results after that noise. Genuine 20–22TB matches and their status:
  - "1 Disque Dur 20TO WD data center" — €800, listed as available (over budget)
  - "Disque dur 20To Dell Exos" — €500, marked **"Achat en cours"** (a purchase is currently in progress — i.e., someone has initiated a buy but it may not be finalized; a crawler should treat this as a third availability state distinct from "available" and "sold")
  - "Disque dur 20to" — €290, marked **"Vendu"** (sold) — useful as a historical price point (this exact capacity/condition sold under budget) but not purchasable now
  - "Disque dur Western digital 20TB Elements Desktop HDD, USB 3.0" — €360 (dropped from €361.99), marked **"Vendu"** — an external USB enclosure drive, which is a distinct sub-category: external "shucked-in-reverse" or white-label drives inside USB enclosures are often the cheapest way to reach a given capacity, since manufacturers frequently price external drives below the equivalent bare internal enterprise SKU
  - "Disque 22to Toshiba MG10AFA22TE NEUF, jamais ouvert GARANTIE OK" (new, never opened, with warranty) — €599, marked **"Vendu"**
  - "LaCie 5big Thunderbolt 2 - 20To Mac OCCASION" — €400, currently available — but this is a 5-bay Thunderbolt 2 RAID enclosure (likely populated with smaller drives totaling 20TB, not a single 20TB drive), aging interface, and Mac-oriented — not a like-for-like match for "one 20TB+ HDD."
- **Takeaway for the crawler design:** on this site, sold/pending listings are highly informative for price-floor tracking even though they're not purchasable — a scraper should persist "Vendu"/"Achat en cours" listings with their last-shown price as historical data points, not discard them, since they're the best evidence this scan found that sub-€400 20TB pricing does occasionally clear on the used market, just not reliably or predictably in-stock.

---

## 3. Cross-cutting technical notes for crawler design (delta from prior GPU/RAM scans)

- **Two more availability states to model**, on top of `in_stock` / `unavailable` / `undispatchable_to_location` from prior scans: Leboncoin's **`purchase_in_progress`** ("Achat en cours") and **`sold`** ("Vendu"). Both are distinct from a listing simply disappearing — the listing page remains live and its last price remains visible and valuable as a historical data point.
- **Search relevance cannot be trusted on Leboncoin for numeric/capacity queries** — free-text search appears to fuzzy-match on partial token overlap (e.g. "1,5 To" matching a "22to" query). Any crawler pulling from this site must re-filter results by parsing capacity out of each listing's own title/description rather than trusting that returned results match the query's intent.
- **Form-factor/interface must be a first-class filter for SSDs**, similarly to how ECC/RDIMM was a hard fork for RAM: SATA vs. NVMe (and within NVMe, PCIe generation) span a wide price range for the same capacity, and a budget-constrained buyer needs the cheaper SATA tier surfaced distinctly from the faster-but-pricier NVMe tier rather than blended into one "4TB SSD" price floor.
- **"Consumer-branded but enterprise-tier" products are a real edge case at high capacities**: Seagate BarraCuda (normally a budget consumer desktop line) shows up as the *cheapest* 20TB option specifically because at 20TB+ it's manufactured on the same nearline platform as Seagate's enterprise Exos/IronWolf lines — brand-name alone is not a reliable proxy for market tier at these capacities, and a crawler should key primarily on capacity + form factor + interface rather than brand-implied tier.
- **Provenance/condition labels are more varied in storage than in the GPU/RAM categories scanned previously** — this scan surfaced "New," "New (Other)," "OEM," "Recertified" (with manufacturer-equivalent warranty), "Refurbished — Hervorragend/Excellent" (graded, tested, warrantied), and plain "Used/Gebraucht" as distinct tiers with materially different risk/price tradeoffs, particularly common among specialist bulk enterprise-HDD resellers. A crawler serving buyers in this category should preserve the seller's own condition/grading label verbatim rather than collapsing everything to a binary new/used flag.
- **External (USB-enclosure) drives are a legitimate lower-cost path to a given capacity** and should be captured as a distinct sub-category rather than excluded, since manufacturers sometimes price the external SKU below the equivalent bare internal drive — a capacity-focused crawler that only looks at "internal HDD" listings would miss this.
- Everything else (Geizhals `asuch=` search mechanics and per-product structured specs, eBay Browse API recommendation, Amazon robots.txt/rendering requirements, VAT-inclusive EUR pricing, lack of native historical-price data outside Geizhals's own charts) carries over unchanged from the GPU and RAM scans and is not repeated here.

---

## 4. Best current leads found in this scan (for reference)

### 4TB SSD (target ~€400) — comfortably achievable
| Listing | Site | Interface | Price | Notes |
|---|---|---|---|---|
| TeamGroup T-Force Vulcan Z QLC 4TB | Geizhals-tracked retailer | SATA 2.5" | **€329.00** | Cheapest overall; 8 offers |
| Crucial BX500 4TB | Geizhals-tracked retailer | SATA 2.5" | €369.99 | 30 offers, well-known brand |
| Crucial P310 4TB | Geizhals-tracked retailer | NVMe PCIe 4.0 | **€399.00** | 26 offers, currently -6% |
| Lexar NQ790 4TB | Geizhals-tracked retailer | NVMe PCIe 4.0 | €399.88 | 31 offers |
| Kingston NV3 4TB | Geizhals-tracked retailer | NVMe PCIe 4.0 | €419.90 | 47 offers — most liquid SKU in category |

### 20–22TB HDD (target ~€400) — not currently achievable new; closest used match ~34% over
| Listing | Site | Capacity | Condition | Price | Notes |
|---|---|---|---|---|---|
| WD Interne Festplatte 22TB SATA OEM | ebay.de (private, DE listing) | 22TB | New (Other), OEM/bare | **€500 + €35 shipping ≈ €535** | Closest match found to budget |
| Disque dur 20To Dell Exos | leboncoin.fr | 20TB | Used | €500 | Marked "purchase in progress" — may not be available |
| Seagate 22TB Recertified (ST22000NM000C) | ebay.de (UK) | 22TB | Recertified, 1-yr warranty | €583.36 + €49.67 ≈ €633 | |
| Seagate BarraCuda 20TB | Geizhals-tracked retailer | 20TB | New | €726.34 | Cheapest new 20TB tracked anywhere in this scan |
| Toshiba MG10AFA22TE, new/sealed | leboncoin.fr | 22TB | New, sealed, warranty | €599 | **Sold** — historical price point only |
| WD 20TB Elements (external USB) | leboncoin.fr | 20TB | Used | €360 | **Sold** — historical price point; external-drive route worth monitoring going forward |

**Bottom line:** the 4TB SSD goal is done — several good options land at or under €400, comfortably within budget with some margin (SATA route especially). The 20–22TB HDD goal at €400 is not realistic right now; budgeting closer to €500–€600 for a used/OEM/recertified drive, or ~€730+ for new retail, reflects current market reality. Watching the used/private market (Leboncoin, eBay private sellers) for the occasional sub-€450 clearance — as this scan's "sold" listings show does happen — is the most realistic path to closing that gap.
