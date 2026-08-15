# Product Matching & Anomaly Detection Roadmap

**Status:** 📋 Planned (v1.5, v1.6, v2.10-v2.13) · **Source:** codex research, grounded directly in this repo's schema; v2.10-v2.13 additions from the 2026-08-15 global-scope brainstorm

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
   - Reject if an excluded bundle/variant term appears and wasn't explicitly allowed.
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

Anomalies are flags, not deletions, and only compare confirmed listings in the
same currency.

**With ≥4 confirmed listings** (IQR method — robust to a single extreme listing,
unlike mean/z-score):

- Compute `Q1`, `Q3`, `IQR = Q3 − Q1` on current prices.
- High-price anomaly: `price > Q3 + 2.0×IQR` **and** `price ≥ 1.75×median`.
- Low-price anomaly: `price < Q1 − 2.0×IQR` **and** `price ≤ 0.60×median`.
- Uses `2.0×IQR` rather than the conventional `1.5×IQR` fence deliberately — real
  retailer price differences happen, and a false positive here is worse than a
  missed warning.

**With <4 confirmed listings** (not enough for statistics — use a semantic flag):

- `price ≥ 2.5×median` of the other matched listings **and** the title has a
  bundle/kit/accessory/conflicting-category signal.
- This flags the €2 531,51 result for review while still preserving it — a
  genuinely expensive exact SKU with no bundle signal stays visible.

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
- Anomaly detection (IQR, semantic bundle-flag) runs **per condition bucket**,
  not across the whole listing set. A `used` listing is only compared against
  other `used` (+ `refurb`/`enterprise_surplus`, which are reasonable to pool
  together as "not new") listings for its median/IQR fence. `unknown`-condition
  listings are never pooled with `new` — treat as their own bucket (or require
  ≥1 confirmed `new` listing to exist before showing a comparison at all,
  since an unknown-condition item can't be honestly compared to anything).
- `new` remains the default assumption **only** for retailers/categories
  where the existing scraper set already only lists new stock (i.e., the
  current Amazon.es/PcComponentes/PT-retailer sources) — don't retroactively
  require condition detection on sources that structurally never carry
  anything else.
- Dashboard implication (see [dashboard_ux.md](dashboard_ux.md)): the
  snapshot bar and retailer table need a condition badge/filter, since
  showing a €700 used listing directly beside a €2200 new one without
  labeling which is which would be actively misleading, not just incomplete.

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
