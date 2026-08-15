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
