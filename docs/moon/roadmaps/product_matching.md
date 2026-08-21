# Product Matching & Anomaly Detection Roadmap

**Status:** ✅ Done (v1.5, v1.6, v2.11 extraction + IQR-per-condition on EUR-equivalent — 2026-08-21) · 📋 Planned (v2.12-v2.13; dashboard condition badge/filter) · **Source:** codex research, grounded directly in this repo's schema; v2.10-v2.13 additions from the 2026-08-15 global-scope brainstorm

## Why this is the highest-leverage roadmap item

A real search for "Ryzen 9 9950X3D" on Amazon.es returned a genuinely relevant CPU
at 609,82 €, other Ryzen variants (9800X3D, 5800X3D, 9900X) mixed in, and an
unrelated bundle/kit at 2 531,51 €. The current pipeline stores every parseable
[`RawListing`](../../../src/models/listing.py) under the query's product record,
keyed only by `(product_id, site_key, url)` — there is no identity check between
"this is what I searched for" and "this is what got stored." Every downstream
feature (snapshot chart, trend chart, badges, alerts) inherits this problem.
grok's competitor research independently concluded the same thing: *"the feature
that will make or break the roadmap is not charts — it's listing identity."*

## v1 design: deterministic hybrid matcher

Add [`rapidfuzz`](https://rapidfuzz.github.io/RapidFuzz/) as the one new
dependency for this feature. Insert a match-decision stage between
`pipeline.discover` and `pipeline.snapshot.persist_snapshot` — matching is a
filter, not a clustering step, and it never silently merges listings.

### Per-tracked-product identity profile

- `canonical_name` — e.g. `AMD Ryzen 9 9950X3D`
- `required_model_tokens` — model/SKU tokens containing digits, e.g. `["9950x3d"]`
- `required_brand_tokens` — e.g. `["amd", "ryzen"]`
- `excluded_terms` — e.g. `["bundle", "kit", "pack", "lote", "placa base", "motherboard", "combo"]`
- `allowed_variant_terms` — optional, e.g. `["boxed"]`, only when intended
- `match_mode` — `exact_model` / `strict_title` / `manual_review`

### Decision process

1. **Normalize for matching** (separately from `normalize.text.normalize_title`,
   which is display-only): lowercase, Unicode-normalize, normalize hyphens/slashes,
   strip punctuation, extract alphanumeric model tokens containing at least one digit.
2. **Hard gates** (before any fuzzy scoring):
   - If the product has a model token, require an exact normalized model-token match.
   - Reject if an excluded bundle/variant term appears and wasn't explicitly
     allowed. A preceding negation particle (`sin` / `sem` / `without` / `no`,
     optionally plus an article) does **not** count — Amazon.es
     "Sin Ventilador" / "without a cooler" is a no-fan CPU, not a cooler
     listing. Positive mentions (`Cooler para Ryzen…`) still reject.
   - Reject category-conflicting terms (for a CPU: motherboard/PSU/case terms disqualify).
   - Amazon ASIN is a stable *Amazon* listing identifier, not a cross-retailer identity key.
3. **Score the survivors**:
   - `token_sort_ratio(canonical_name, title) >= 88`
   - query-token coverage `>= 0.80` for meaningful non-stopword tokens
   - brand present when known
   - `token_set_ratio` is supporting evidence only, never the acceptance rule — it
     can rate a bundle highly because the requested title is a *subset* of the
     bundle title.
4. **Outcomes**: `confirmed` (hard model match, no conflict) / `likely` (no model
   token available, strict score ≥92 + coverage ≥90) / `review` (score 80–91,
   unclear variant, or model absent) / `rejected` (model mismatch, prohibited
   bundle/variant, or score <80).

For `Ryzen 9 9950X3D`, requiring the `9950x3d` token alone rejects the 9800X3D/
5800X3D/9900X variants; the €2 531,51 kit is rejected on bundle/component terms
even though it technically contains the requested CPU.

Persist the evidence, not just the verdict: listing title, normalized title,
extracted model tokens, `match_status`, `match_score`, `match_reason`. Only
`confirmed` (and optionally user-approved `likely`) listings create
`price_history` points — `review`/`rejected` rows are kept in a
`candidate_listings` table for debugging, never silently deleted.

## v2+ design: structured identifiers

Once available (from JSON-LD/structured data or product pages), site-specific
identifiers should outrank title matching entirely: EAN/GTIN and MPN/manufacturer
part number first, ASIN and merchant SKU as secondary signals. If catalog breadth
grows enough to matter, add a reviewed canonical-product catalog with blocking
keys (brand + model token/category) and consider embedding-based retrieval —
**only** for candidates that already pass the deterministic block. ML should
improve recall, never become the final identity decision.

## Anomaly detection

Anomalies are flags, not deletions, and only compare **confirmed** listings
in the **same exact condition bucket**, using each observation's persisted
`price_eur_equivalent` (v2.10 item price). Never mix native currencies.
Never run IQR or historical-low fences on landed-cost estimates — shipping
and VAT revisions must not move an anomaly fence or an ATL.

**With ≥4 confirmed listings** (IQR method — robust to a single extreme listing,
unlike mean/z-score):

- Compute `Q1`, `Q3`, `IQR = Q3 − Q1` on current prices.
- High-price anomaly: `price > Q3 + 2.0×IQR` **and** `price ≥ 1.75×median`.
- Low-price anomaly: `price < Q1 − 2.0×IQR` **and** `price ≤ 0.60×median`.
- Uses `2.0×IQR` rather than the conventional `1.5×IQR` fence deliberately — real
  retailer price differences happen, and a false positive here is worse than a
  missed warning.

**With <4 confirmed listings in that exact condition bucket** (not enough
for statistics):

- Never auto-hide and never auto-accept (v2.11). A kit/bundle title in a
  sparse bucket stays visible rather than being IQR-flagged from n=2/3.
- An inspect-seller/condition review badge (when EUR-equivalent is a
  documented fraction of the `new` median) is a later surfacing, not an
  auto-hide.

Anomalous listings are excluded from "best price," charts, and alerts by
default, with a way to reveal them. Store `is_anomalous`, `anomaly_reason`, and
`anomaly_basis` (sample size, median, fence) alongside the observation. Later:
add a per-listing history check (flag a one-day jump/drop >40% vs. its 7-day
median) — surfaced, never auto-suppressed, since both sales and pricing errors
are real.

## Condition as a first-class field (v2.11)

**Why:** the IQR anomaly rule as originally specified (`price < Q1 − 2.0×IQR`
**and** `price ≤ 0.60×median` ⇒ excluded by default) would auto-hide exactly
the deals the EU-wide secondhand tier exists to surface — a genuine
enterprise-surplus GPU at ~0.32× the new-retail median is precisely what that
rule was designed to flag as suspicious. The rule isn't wrong for a
same-condition population; the problem is comparing across conditions as if
they were one population.

**Design:** add `condition` to both the listing schema and the identity
profile:

- `condition` enum on every listing: `new` / `used` / `refurb` /
  `enterprise_surplus` / `unknown`. Extracted from structured data where
  available (many EU secondhand/classifieds sources expose this explicitly),
  falling back to title/description keyword detection, falling back to
  `unknown` — never guessed silently into `new`.
- Anomaly detection (IQR and semantic bundle-flag) runs **per exact condition
  bucket**, not across the whole listing set. `used`, `refurb`, and
  `enterprise_surplus` are distinct by default: warranty, seller type, return
  rights, grade, and service life can make their distributions materially
  different. A documented, low-confidence pooled fallback may be introduced
  later only after measuring that it helps a specific sparse bucket.
- Persist `condition` on **every `price_history` row** (observation-time
  snapshot) as well as on the listing (current belief). Confirming
  `unknown → enterprise_surplus` updates the listing and *future*
  observations; it must not retcon ATL / percentile / IQR history.
- Sparse buckets (`N < 4` in that exact condition, including sparse
  **new**) never auto-hide and never auto-accept. They may raise an
  "inspect seller/condition" review badge when `price_eur_equivalent` is
  below a **per-category, user-editable** fraction of the `new` median
  (or of that listing's own prior confirmed sticker if no new reference
  exists). Documented starting values, not universal law: GPU surplus
  `0.40`, RAM used `0.50`. Persist the fraction used, the reference
  series, and the evidence. Do not ship a global 0.20/0.25/0.95 fence.
- `unknown`-condition listings are never pooled with any verified
  condition and never enter any IQR sample. Persist `condition_source`
  (structured data, seller declaration, title heuristic, manual, or
  `source_policy`) and `condition_confidence`; show them as unverified,
  keep them visible, and exclude them from the default cross-condition
  "cheapest" winner until the user confirms the condition.
- `new` remains the default assumption **only** for retailers/categories
  where the existing scraper set already only lists new stock (i.e., the
  current Amazon.es/PcComponentes/PT-retailer sources). Migrations must
  record `condition_source = source_policy` for those rows — do not
  silently backfill historic rows as verified `new`. Don't retroactively
  require condition detection on sources that structurally never carry
  anything else.
- Dashboard implication (see [dashboard_ux.md](dashboard_ux.md)): the
  snapshot bar and retailer table need a condition badge/filter, since
  showing a €700 used listing directly beside a €2200 new one without
  labeling which is which would be actively misleading, not just incomplete.

**Shipped 2026-08-21 (extraction + persistence + IQR buckets):**
`matching.extract_condition` implements structured-data → title heuristic →
`unknown`, with `source_policy` only for known new-stock site keys.
`persist_snapshot` writes current belief on `listings` and an observation-time
copy on `price_history`, then runs `detect_anomalies` per exact condition on
`price_eur_equivalent`. `unknown` and missing EUR never enter a sample;
sparse buckets never auto-hide. Pre-v2.11 rows stay NULL. Dashboard
badges/filters are not this slice.

This does not weaken the anomaly detector's original purpose (catching
mispriced/scam listings within a condition bucket) — it just stops applying
a new-market statistical fence to a fundamentally different population.

## Multilingual matching (v2.12)

**Why:** the EU-wide tier explicitly includes native-language-only sites
(e.g. German enterprise-surplus/classifieds sources) where listing titles
won't contain the English/Portuguese tokens the current deterministic
matcher's `required_model_tokens`/`required_brand_tokens` expect to find
verbatim.

**Design — hybrid, per Harbinger's decision (both approaches, not
either/or):**

1. **Per-market alias lists first** (fast, dependency-light, matches the
   existing deterministic-rules-first philosophy): maintain a translated
   alias table for the token *categories* that actually vary by language —
   category/component-type nouns (`Grafikkarte`/`placa gráfica`/`graphics
   card`), condition terms (`gebraucht`/`usado`/`used`,
   `generalüberholt`/`refurbished`), and excluded-bundle terms
   (`Kit`/`Bundle`/`Set` already mostly cognates, but verify per language).
   Model/SKU tokens (e.g. `9950x3d`) are typically language-invariant and
   need no translation — the alias table only needs to cover the
   category/condition/bundle vocabulary, which is a small, stable set worth
   hand-maintaining rather than translating on every run.
2. **Machine translation as a fallback**, only when the alias table doesn't
   resolve a listing (new market, unexpected phrasing) — translate the title
   before running it through the existing English/Portuguese-oriented
   matcher, rather than maintaining a full parallel matcher per language.
   This is explicitly a fallback path, not the primary mechanism, to keep
   the common case dependency-light and keep translation-API failure modes
   (rate limits, cost, availability) from being load-bearing for every match.
3. Persist which path resolved a given match (`alias_table` vs.
   `machine_translation`) alongside the existing match evidence — useful for
   noticing when the alias table needs a new entry instead of silently
   leaning on translation forever for a term that recurs often.

## Out of scope for this feature

- Auto-merging listings purely by title similarity with no hard gates — flagged
  by grok as *"product-risk #1; a wrong merge poisons every chart."*
- ML/embedding-based matching as the primary mechanism for v1 — dependency-light
  deterministic rules first, per the user's explicit choice to adopt the full
  rapidfuzz hybrid matcher now rather than defer to a simpler manual-only v1.
