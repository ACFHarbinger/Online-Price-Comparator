# Product Matching & Anomaly Detection Roadmap

**Status:** 📋 Planned (v1.5, v1.6) · **Source:** codex research, grounded directly in this repo's schema

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

## Out of scope for this feature

- Auto-merging listings purely by title similarity with no hard gates — flagged
  by grok as *"product-risk #1; a wrong merge poisons every chart."*
- ML/embedding-based matching as the primary mechanism for v1 — dependency-light
  deterministic rules first, per the user's explicit choice to adopt the full
  rapidfuzz hybrid matcher now rather than defer to a simpler manual-only v1.
