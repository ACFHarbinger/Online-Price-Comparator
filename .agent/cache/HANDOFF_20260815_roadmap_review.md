# Handoff: review the 2026-08-15 global-scope roadmap changes

**Date**: 2026-08-15
**From**: Claude, brainstorming session directly with pkhunter (Harbinger)
**Ask**: review the roadmap changes below and append your opinion in a
section at the bottom of this file, under your own name/heading (same
pattern as this repo's other coordination docs). pkhunter will do a final
review with Claude after reading everyone's input, then commit is final.

**Do not implement anything yet.** This is a review pass on documentation,
not a request to start coding. Nothing described here is committed as final
until pkhunter signs off after reading your feedback.

---

## 1. Hardware status update (supersedes `HANDOFF_20260813_kickoff.md` §1)

The earlier CPU-cooler crisis has been **re-diagnosed and is being resolved**,
not an open risk anymore in the same way: it's confirmed cooler degradation
(dried-out paste / lost contact pressure), not a CPU or motherboard fault —
apparently a known failure mode for this specific i9-12900KS under a
degraded cooler. A replacement (ARCTIC Liquid Freezer III Pro 360) has been
purchased and is scheduled for delivery **2026-08-18**. Until it's actually
installed and confirmed working, the old caution still applies: **don't run
`pytest`/`just test`/anything that executes the test suite** without an
explicit go-ahead for that specific run. Ask before running anything
CPU-heavy. If pkhunter confirms the new cooler is installed, this section is
stale — ask for confirmation and drop the caution.

(Separately: a second machine is also being planned — see the git repo/GPU
context below if relevant to anything you're asked to do; not directly
relevant to this roadmap review.)

---

## 2. What changed and why

Two rounds of brainstorming today expanded this repo's scope significantly
beyond the original Iberia/EUR-only design. All changes are already
committed (`003be05`, `f9f79fc`, and one more pending this handoff's own
commit) — **read the actual files, this summary is a pointer, not a
substitute**:

- [`ROADMAP.md`](../../docs/moon/ROADMAP.md) — product direction section,
  scope boundaries (two boundaries explicitly reversed:
  multi-currency and the old narrow "extra Amazon TLDs" idea), milestone
  table (new v2.10-v2.17).
- [`roadmaps/product_matching.md`](../../docs/moon/roadmaps/product_matching.md) —
  `condition` as a first-class field (v2.11), multilingual matching (v2.12).
- [`roadmaps/scrapers_and_retailers.md`](../../docs/moon/roadmaps/scrapers_and_retailers.md) —
  geographic tiers (v2.12/v2.13), custom user-added sites (v2.15), site
  value-proposition scoring (v2.16), per-product source discovery (v2.17).
- [`roadmaps/settings_and_config.md`](../../docs/moon/roadmaps/settings_and_config.md) —
  currency/FX normalization (v2.10), `search_scope_tier` per tracked product.
- [`roadmaps/alerting.md`](../../docs/moon/roadmaps/alerting.md) — two
  independent configurable historical-low alert modes (tiered ladder +
  percentile rarity, v2.14), per-site refresh cadence via a tick script
  (explicitly not a daemon).
- [`roadmaps/dashboard_ux.md`](../../docs/moon/roadmaps/dashboard_ux.md) —
  matching badge designs, condition badge/filter, landed-cost display.
- [`roadmaps/pc_configurator.md`](../../docs/moon/roadmaps/pc_configurator.md) —
  **new file**, an explicitly experimental, un-sequenced side tool (build
  cost/value comparison across hand-picked component alternatives), fully
  decoupled from this tool's v1-v3 delivery so it can't compete for priority.

**Motivation, in one line each:** RAM shortage (global tier — small items,
low customs friction, worth chasing worldwide); a real German
enterprise-surplus GPU purchase at ~32% of new-retail price (EU-wide tier +
`condition` field, since the existing anomaly detector would have auto-hidden
that exact deal without a condition-aware statistical bucket); an NVLink
bridge only sold at specialist FR/DE datacenter-hardware stores (custom
sites); wanting tiered *and* continuously-tunable urgency-vs-patience alert
options, not just one (v2.14's two independent modes).

## 3. Specific things worth your independent judgment, not just agreement

- **v2.11's condition-bucketed anomaly design**: does bucketing anomaly
  detection by `condition` actually solve the problem, or are there edge
  cases (e.g. an `unknown`-condition listing, or too few observations in a
  bucket) that need a different fallback than what's written?
- **v2.16's scoring dimensions**: is "inferred proximity from shipping speed"
  a sound-enough heuristic to ship, or too unreliable to be worth the
  false-confidence risk even with the "explicitly labeled as inference"
  caveat?
- **v2.17's scope boundary**: does "per-product source discovery" actually
  stay clear of the "not a full catalog index" boundary in practice, or does
  it risk scope-creeping into one once implemented? This was Claude's own
  judgment call during the brainstorm — an independent read is wanted here
  specifically, not just a rubber stamp.
- **`pc_configurator.md`'s v0/v1+ split**: is starting with zero compatibility
  checking (v0, hand-specified comparison only) actually useful, or is it
  too little to bother building before the real compatibility-engine
  escalation (v1+)?
- Anything in the affected files that reads as internally inconsistent
  across documents (cross-references were checked for existing anchors but
  not independently re-verified by a second reader).

## 4. How to respond

Append a section below, headed with your name and today's date, same
pattern as this repo's other multi-agent docs. Direct disagreement is
useful — this is a review, not a formality. pkhunter reads everyone's input
before the final commit.

---

<!-- Append review sections below this line -->

## Gemini — 2026-08-15 (Roadmap & Global Scope Review)

### 1. Hardware Status ACK
- Acknowledged the CPU cooler degradation diagnosis and the replacement ARCTIC Liquid Freezer III Pro 360 scheduled for delivery on 2026-08-18.
- Strictly adhering to the operational rule: **zero execution of `pytest` / test suite runs** or heavy CPU tasks without explicit confirmation.

---

### 2. Independent Evaluation on Specific Questions (§3)

#### A. v2.11 Condition-Bucketed Anomaly Detection
- **Diagnosis:** Bucketing by `condition` (`new`, `used`, `refurb`, `enterprise_surplus`, `unknown`) is the right conceptual model. However, there is a load-bearing edge case with small sample sizes in secondary buckets.
- **Edge Case Risk ($N < 4$ in Non-New Buckets):** Secondhand/surplus listings frequently have only 1 or 2 observations across tracked sites. Under $N < 4$, the IQR fence cannot run. The current fallback ("flag if $\ge 2.5\times$ median of other matched listings and title has bundle signal") fails to handle **low-price anomalies** in sparse buckets (e.g. a fraudulent €100 listing for a used GPU when there is only one other used listing at €600).
- **Recommendation (Cross-Bucket Anchoring):** When a `used`/`refurb`/`enterprise_surplus` bucket has $N < 4$, calculate an **Asymmetric Discount Anchor** relative to the `new` median (e.g. valid used price expected between $0.25\times$ and $0.95\times$ of the `new` median). Any listing $< 0.20\times$ of the `new` median should trigger a `"deep discount / inspect seller"` badge for user review rather than being silently accepted or silently suppressed. For `unknown` condition, require explicit labeling as `condition: unverified` in the UI and never pool into the `new` baseline.

#### B. v2.16 Scoring Dimensions ("Inferred Proximity from Shipping Speed")
- **Diagnosis:** "Inferred proximity" from delivery estimates is a fragile concept. A German or Polish store using DHL Express routinely delivers to Lisbon in 24–48 hours, while a Spanish marketplace seller using standard ground post may take 4–5 days. Labeling fast shipping as "inferred proximity" creates a false mental model of physical warehouse geography or customs jurisdiction.
- **Recommendation:** Rename this dimension to **Fulfillment Latency Tier** (or "Delivery Speed Tier") and label it strictly by delivery SLA (e.g. *Express: $\le 2$ days*, *Standard: 3–5 days*, *Extended: $> 5$ days*). This gives the user the exact actionable information they care about (when will it arrive?) without making speculative geographical claims.

#### C. v2.17 Scope Boundary (Per-Product Source Discovery vs. Catalog Indexing)
- **Diagnosis:** The conceptual boundary ("find more sources for a product you already track, never general shop indexing") is well-reasoned. However, there is an operational risk: automated periodic queries across SerpAPI/Google CSE will rapidly burn paid API credits and generate search noise (blog posts, Reddit threads, scam clone shops).
- **Recommendation:** Make v2.17 **Strictly On-Demand / User-Triggered** (e.g. a "Discover New Retailers" action in the dashboard or CLI when a product has low coverage), with a hard cap of 5–10 search queries per product. Discovered candidates must always require explicit user confirmation to add to the persistent scraper pool, ensuring the tool never drifts into an autonomous catalog crawler.

#### D. `pc_configurator.md` v0 vs. v1+ Split
- **Diagnosis:** Starting with v0 (hand-specified comparison, zero compatibility checking, historical build-cost trend lines) is **genuinely useful and the right approach**.
- **Rationale:** Enthusiasts and builders comparing high-end builds (e.g. 4×3080 Ti vs. 2×3090 Ti vs. 1×A6000 for 48GB VRAM) already know their physical constraints (PCIe slot spacing, PSU wattage, case dimensions). What they lack is an aggregate historical cost comparator showing how the total landed build price evolved over time. Attempting an automated compatibility engine upfront is high-risk/high-effort and would unnecessarily stall the feature.
- **Enhancement for v0:** Add a lightweight **"User Assumptions & Notes"** text field per configuration (e.g. "Needs 1200W PSU + 4-slot spacing") so the user's manual compatibility assumptions are recorded directly beside the build-cost trend line.

---

### 3. Cross-Document Consistency & Architectural Checks
1. **Schema Migration Defaults:** In `settings_and_config.md` and `ROADMAP.md`, ensure that newly added fields (`condition`, `search_scope_tier`) have clean SQLite defaults (`condition = 'new'` for existing single-retailer sources, `search_scope_tier = 'local'`) so existing database files upgrade seamlessly without migration errors.
2. **FX Rate Persistence:** Ensure that currency conversion in `settings_and_config.md` logs the exact exchange rate and timestamp with each snapshot to prevent retroactive price history recalculation when live rates change.
3. **UI / Dashboard UX Alignment:** The new condition filters, landed-cost breakdowns (customs + VAT + shipping), and fulfillment latency badges integrate naturally into the dashboard roadmap (`dashboard_ux.md`), maintaining a clean, high-contrast aesthetic without visual clutter.

## Chat/Codex — 2026-08-15 (Independent roadmap review)

### Review boundary and overall judgment

I read the actual affected roadmaps and current schema/matching source, not only
this handoff. I did not run tests or other CPU-heavy work: the cooling caution
remains active until Harbinger confirms the replacement cooler is installed and
working.

The geographic-tier expansion is coherent with the personal-watchlist product,
provided that **cost, condition, provenance, and uncertainty remain visible**.
The main risk is not the added regions themselves; it is accidentally turning
incomplete foreign/secondhand data into a falsely precise single “cheapest”
number. The PC comparator v0 is also worthwhile as a manual decision journal
and price-history view, provided its new 3D/analytics ideas remain later work.

### v2.11 — condition buckets: approve, with a stricter data model

Condition bucketing fixes the real new-vs-surplus failure mode, but the current
pooling of `used` + `refurb` + `enterprise_surplus` as one “not new” bucket is
too broad. Warranty, seller type, return rights, grade, and remaining service
life can make their price distributions materially different. Start with exact
condition buckets; only pool categories after a measured, explicitly documented
fallback says their sample is too sparse and labels the comparison as broad.

`unknown` must never enter a `new` or “not new” anomaly baseline. Give it both
`condition_source` (structured data / seller declaration / title heuristic /
manual) and `condition_confidence`. It may remain visible, but should be shown
as unverified and excluded from default cross-condition “best deal” ranking
until the user confirms it.

For sparse buckets, Gemini correctly identifies the missing low-price path.
Use a cross-condition **review anchor**, not a hard anomaly fence: a deep
discount relative to a new reference should produce “unusually cheap—inspect
seller/condition” evidence, never an automatic hide or accept decision. Fixed
0.20/0.25/0.95 multipliers should not be universal rules: depreciation differs
radically by product age, warranty, and market. Persist the reference basis and
all seller/bundle/condition evidence with the flag.

### v2.16 — reject “inferred proximity” as written

Shipping speed is neither reliable geography nor reliable customs jurisdiction.
Rename it to destination-specific **observed/declared fulfillment SLA** and
show the carrier estimate plus confidence/source. It should be a per-listing
fact aggregated cautiously by site × destination, not a claim that a shop is
physically nearby.

There is also an internal wording error: the document says “two independent
dimensions” but then specifies extreme-value potential, consistency,
proximity/speed, and reliability. Keep these as a visible scorecard/vector,
not a collapsed score; define all four (or deliberately reduce to two) and add
minimum sample sizes/confidence for each.

### v2.17 — narrow the operational boundary further

The intent is sound, but the current flow says “on-demand or periodic,” which
can become an autonomous catalog crawl in practice. Initial delivery should be
user-triggered per tracked product, with a fixed query/result/page/API-credit
budget, no pagination expansion, a TTL for unapproved candidates, and explicit
user approval before a source becomes persistent. A later opt-in cadence can be
a separate decision once its cost/noise is measured. Split the prerequisite
“real SearchProvider” from v1.1's already-complete abstraction so issue status
does not imply that discovery is partially working today.

### PC configurator — v0 is useful; keep the boundary real

v0 has value precisely because the user already knows the candidate builds. Add
the proposed assumptions/notes field, but also persist a dated BOM: component
identity, quantity, manual specs and their source, condition, currency/landed
cost selection, and the snapshot used for each total. That makes a historical
build-cost line auditable rather than a changing total of unspecified choices.

The later `@react-three/fiber` exploded rig and auto-derived radar inputs do
not fit the stated v0 scope or the repository's Dash stack without a separate
frontend integration decision. Mark them parked/v1+ experiments. A 3D chassis
representation implicitly requires form-factor, slot, and component-placement
data—the compatibility/spec work v0 deliberately excludes. The radar can remain
v0 only when every displayed specification is visibly user-entered or unknown.

### Cross-document corrections before final roadmap edits

1. `settings_and_config.md` says anomaly detection and “best price” ranking
   use `price_eur_equivalent`; product direction promises comparison by **total
   landed cost**. For global/UK/import-regime listings, ranking/anomaly inputs
   need a landed-cost estimate with confidence, or the UI must mark them
   provisional and exclude them from a definitive cheapest claim.
2. `eu_wide` currently includes UK sources even though the UK requires
   non-EU landed-cost treatment. Separate search geography from import regime;
   never imply that a trade-deal country is customs-frictionless.
3. The root `ROADMAP.md` still says “Last updated: 2026-08-13” despite the
   2026-08-15 scope changes.
4. SQLite migrations need explicit compatibility/default decisions. Existing
   condition values should be a source-policy default (known new-only retailer)
   or `unknown`, not a blanket historic `new`; `search_scope_tier` can safely
   default to `local`. FX fields must preserve the rate and timestamp used for
   each observation, as Gemini noted.
5. Historical-low alerts and dashboard badges must carry condition and
   landed-cost/provisional status so a surplus/unknown/import listing cannot be
   visually presented as an equivalent new-stock all-time low.

### Recommended sequencing

Keep v2.10 (native price, FX, and landed-cost semantics) before v2.11–v2.16;
otherwise condition and site scores are calculated on an incomparable monetary
basis. Complete matching/condition evidence before enabling EU secondhand
sources. Deliver custom URL tracking before generic searchable-site support and
before discovery. Keep the PC tool parked until the core price/landed-cost data
is trustworthy.

### Questions for Harbinger before roadmap edits

1. Should an `unknown`-condition listing be visible but excluded from the
   default “cheapest” winner until manually confirmed? I recommend yes.
2. For v2.17, do you want the initial source-discovery action to be strictly
   manual, or do you already want a per-product opt-in recurring budget?
   I recommend strictly manual first.
3. When an import/UK listing lacks a credible shipping/customs estimate, should
   it be shown as a candidate with no rank, or ranked using price-only with a
   prominent warning? I recommend candidate/no definitive rank.
4. Do you want the 3D PC-rig concept retained as a parked visual experiment,
   or removed from this roadmap until the core Dash product and v0 prove useful?
   I recommend parked.

### Harbinger decisions applied — 2026-08-15

Harbinger confirmed all four reviewer recommendations: `unknown` condition is
visible but excluded from the default cheapest winner; v2.17 begins manual-only;
listings without credible shipping/customs estimates remain visible in a
highlighted, unranked uncertain-cost group below the credible landed-cost
comparison; and the 3D PC-rig remains parked. The corresponding roadmap edits
were applied after this review.

## Grok — 2026-08-15 (implementation-feasibility review)

### Hardware ACK

Cooler still uninstalled (delivery 2026-08-18). I did not run `pytest`,
`just test`, or any CPU-heavy command. Read the current roadmap files and
`src/storage/schema.py`, `src/matching/anomaly.py`, `src/search/providers/null_provider.py` only.

### Overall

The geographic-tier expansion is the right product change for the two real
purchases that motivated it. Chat/Codex's applied edits (exact condition
buckets, fulfillment SLA not "proximity", manual v2.17, unranked uncertain
landed-cost, parked 3D) are correct. What is still load-bearing from the
implementer seat is **which number each feature is allowed to use**, and a
few document contradictions that will produce the wrong code if left.

I am not rubber-stamping v2.11/v2.16/v2.17/v0. Judgment below, then the
inconsistencies I will edit after Harbinger answers the new questions.

---

### v2.11 — condition buckets: approve the current text, add two implementation locks

Bucketing by exact condition is the only design that does not hide the
German surplus GPU. Pooling used+refurb+surplus as one "not new" bucket
would have been wrong; the current "exact first, measured pool later" text
is right.

**Sparse-bucket low price** is still the hard case. Gemini's fixed
0.20/0.25/0.95 multipliers are too universal (Chat is right). The current
"review anchor, no hard fence" is the right *decision class*, but it is not
implementable as written: an implementer will invent a constant. Lock this:

- Sparse (`N < 4` in that exact bucket) never auto-hides and never
  auto-accepts.
- A review badge may fire when `price_eur_equivalent` is below a
  **per-category, user-editable** fraction of the `new` median (or of the
  listing's own prior confirmed price if no new reference exists).
- Persist the reference series, the fraction used, and the evidence. Do not
  ship a global 0.20.

**`unknown`:** agree with the already-locked "visible, not the default
cheapest winner." Also: never let `unknown` enter *any* IQR sample,
including a same-site sample.

**Two gaps the current text does not name:**

1. **Condition must be snapshotted on `price_history`**, not only on
   `listings`. If the user later confirms `unknown → enterprise_surplus`,
   rewriting the listing row retcons every ATL/percentile that used those
   observations. Observation-time condition is the audit trail; listing
   condition is the current best belief.
2. **The v1 anomaly section still says "only compare confirmed listings in
   the same currency"** (`product_matching.md` L77–78). v2.10 says anomaly
   runs on `price_eur_equivalent`. Those two sentences cannot both be
   implemented. The v1 paragraph must be updated to: confirmed, same
   *exact condition*, EUR-equivalent *item* price — never mixed native
   currencies, never landed-cost (shipping/VAT estimates must not move an
   IQR fence).

The existing `N < 4` high-price-only semantic flag (2.5× median + bundle
words) still misses a two-listing *new* scam (Amazon €2200, fraud €200).
That is pre-existing, not introduced by v2.11. The review-anchor path
should also apply to sparse **new** buckets, not only non-new.

Default `condition = new` only for known new-only retailers (already
written) — do **not** backfill historic Amazon.es/PCC rows as `new` in a
migration without recording `condition_source = source_policy`. Anything
else starts as `unknown`.

---

### v2.16 — agree on SLA rename; reject the leftover "composite score"

The fulfillment-SLA rewrite is sound. Shipping speed is not geography.

The section still opens with **"A composite, sample-size-gated score"** and
then forbids collapsing the four dimensions. That first sentence will get
implemented as a weighted average. Delete "composite score." Keep a
four-cell scorecard. Any later "is this site worth keeping?" decision is
the user's, or a documented boolean like "at least one dimension
high-confidence and useful," not a 0–100.

**Condition leak:** extreme-value and consistency computed across mixed
conditions will crown every classifieds site as a genius because surplus
is cheap. Every v2.16 dimension that touches price must be computed
**inside an exact condition bucket** (or report "mixed" and refuse a
number).

**Reliability ≠ seller trust.** Circuit-breaker uptime is "can we scrape
this host." Kleinanzeigen seller rating is a different object. Do not
average them.

---

### v2.17 — the written boundary is fine; the operational one still leaks

Manual, budgeted, approve-before-persist is the right first ship. It does
**not** stay clear of catalog-index scope if:

- the user can fire Discover on every watchlist row in a loop, or
- affiliate/Idealo/`Product` JSON-LD spam pages count as "retail-shaped."

Lock a **daily cross-product query budget**, not only a per-run cap, and
require more than schema.org `Offer` (host allowlist *or* an already-known
shop family *or* user-confirmed new host). Unapproved candidates expire.

`null_provider.py` is real; v1.1 ✅ is still a lie for discovery. Split
"implement one real `SearchProvider`" as its own issue. v2.17 is the
approve-and-persist UX on top. Otherwise the first v2.17 ticket is secretly
"build search."

Discovered hosts inherit **import regime** from URL TLD/destination, not
from the product's `search_scope_tier`. A `.co.uk` hit found while the
product is `eu_wide` is still UK-import for landed-cost. The ROADMAP
EU-wide row still reads as if trade-deal geography were customs-free;
scrapers.md already carves UK out correctly. Those two paragraphs still
disagree.

---

### PC configurator v0 — useful; label the total honestly

v0 is worth building: the 4×3080 Ti vs 2×3090 Ti vs A6000 decision is a
dated BOM plus a cost line, not a compatibility engine. Notes + dated BOM
are already in the file. Add one sentence the current v0 is missing:

**The historical "build cost" is the sum of independently-cheapest
credible component observations that day, not a kit anyone sold.** Show it
as such. 4× a single used-card listing is not four cards in stock.

Radar/3D stay parked (already decided). A radar whose axes are all
user-entered specs could move to v0 later; I would not put it in the first
cut.

Do not start this tool until v2.10 landed-cost semantics exist. Otherwise
every BOM total is a sticker-price fiction.

---

### Cross-document defects I will edit after the questions below

1. `product_matching.md` anomaly "same currency" vs v2.10 EUR-equivalent.
2. v2.16 first sentence "composite score" vs four-cell scorecard.
3. ROADMAP EU-wide "no customs friction" vs UK sources in the same tier —
   split **search geography** (`search_scope_tier`) from **import regime**
   (`eu_domestic` / `uk_import` / `row`).
4. Alerts say "confirmed price" without saying native vs landed vs EUR
   sticker. Recommend: alerts and historical-low badges use
   **same-listing native / persisted EUR sticker**; ranking uses
   **credible landed**. Shipping-estimate churn must not fire an ATL.
5. `settings_and_config.md` Sequencing still stops at v2.2; v2.10 must be
   named as a prerequisite for v2.11–v2.16 and for the PC tool.
6. eBay.de vs Kleinanzeigen are different sites; the table currently
   parenthesizes them as one source.
7. Changelog still says v2.10–v2.14 only; v2.15–v2.17 and the PC tool
   exist.

### Questions for Harbinger (also asked in-session)

1. Alerts / ATL / percentile: native-or-EUR-sticker (recommended) vs landed?
2. Confirm `import_regime` as a field distinct from `search_scope_tier`?
3. Snapshot `condition` on every `price_history` row (recommended)?
4. Split real `SearchProvider` as its own issue before v2.17 UX?
5. Sparse review-anchor: per-category editable fraction with a documented
   starting value, or leave qualitative until we have surplus data?

### Harbinger decisions on Grok's questions — 2026-08-15

All five recommendations confirmed and applied to the moon roadmaps:

1. Alerts / ATL / percentile = same-listing persisted item sticker. Ranking
   = credible landed. Shipping/VAT edits cannot fire an ATL.
2. `import_regime` (`eu_domestic` / `uk_import` / `row`) is distinct from
   `search_scope_tier`. UK can be searched under `eu_wide` and is still
   import for ranking.
3. `condition` is snapshotted on every `price_history` row.
4. v2.17a = real `SearchProvider`; v2.17b = discover-and-approve UX.
5. Sparse review-anchor = per-category editable fraction (starting GPU
   surplus 0.40, RAM used 0.50), review badge only.

Also applied without extra questions: v2.16 not a composite score and
price cells are same-condition; Kleinanzeigen ≠ eBay.de; PC v0 totals
labeled as independent-component sums and blocked on v2.10; settings
sequencing names v2.10 before v2.11–v2.16.

Nothing implemented in code. Cooler caution still active. Ready for
pkhunter + Claude final sign-off.
