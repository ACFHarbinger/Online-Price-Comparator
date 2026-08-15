# PC Configuration Comparator — Experimental Side Tool

**Status:** 🅿️ Experimental / not sequenced — explicitly decoupled from the
core watchlist tool's v1-v3 delivery. **Source:** 2026-08-15 brainstorm,
motivated by real Image-Toolkit/ASP hardware-build decisions made earlier the
same session.

## What this is, and why it's a separate document

Comparing hand-picked hardware configurations against cost and historical
price data — e.g. 4×RTX 3080 Ti vs. 2×RTX 3090 Ti vs. 1×RTX A6000 to hit a
≥48GB single-machine VRAM target with a 64-128GB system RAM range, or 2×32GB
vs. 4×16GB DIMMs for the same RAM total, or comparing the top AMD GPU against
the top NVIDIA GPU by historical price trend. This is materially different
software from the core watchlist tool, not a natural extension of it:

- It needs a **structured hardware-spec database** (VRAM per GPU model, DIMM
  capacities, socket/RAM-channel compatibility, PSU wattage requirements) —
  the core tool tracks price + listing identity only, never technical specs.
- Full automatic enumeration of *valid* builds needs real compatibility
  constraints (PCIe lanes/slots for multi-GPU, case physical clearance, PSU
  headroom, RAM channel/slot limits) — this is a real compatibility engine,
  which the core roadmap's original "dumb basket" idea explicitly disclaimed
  ("no compatibility engine"). Building that is a substantial, different
  scope of work from a price-history watchlist.

Kept explicitly experimental and un-sequenced so it can't compete for
priority against the core product, and can be picked up, paused, or dropped
without touching v1-v3.

## v0 (start here): hand-specified comparison, no enumeration

The user specifies the alternative configurations explicitly (e.g. "4×3080Ti"
vs. "2×3090Ti" vs. "1×A6000" as three named candidate builds); the tool:

- Depends on core **v2.10** landed-cost / `import_regime` semantics. Do not
  start this tool on sticker-only totals.
- Looks up each named component against the core watchlist tool's existing
  tracked-product/price-history data (reuses `tracked_products`,
  `price_history` — no new pricing infrastructure).
- Sums cost per candidate build using the core tool's current **best credible
  landed cost**, and historically over time — a build-cost trend line, not just
  a snapshot total. **Label the total as a sum of independently-cheapest
  credible component observations that day, not a kit anyone sold.**
  Quantity `4` against a single used-card listing is not four cards in
  stock. Components without a credible landed-cost estimate remain
  visible as explicitly uncertain inputs, never silently selected as the best.
  Condition mix (e.g. 3 new + 1 surplus) is visible on the BOM, not
  flattened into one "the price."
- Displays alongside whatever spec data is manually entered per component at
  this stage (no automated spec database yet) — VRAM, RAM, TDP, etc. entered
  by the user, not scraped or inferred.
- Persists each configuration as a dated, user-authored BOM: component identity,
  quantity, manual specification values and their source, condition,
  currency/landed-cost selection, and an **Assumptions & Notes** field. This
  makes build-cost snapshots and trend lines auditable without pretending to
  validate compatibility.
- **No compatibility checking at v0** — the user is asserting these
  configurations are physically valid; the tool compares cost/value only.
  This is a deliberate, honest limitation, not a gap to silently paper over.

This is the whole of v0: no constraint solving, no automated enumeration, no
spec scraping. It answers "given these specific alternatives I already have
in mind, which is the better value over time" — nothing more.

## v1+ (later, explicit escalation, not assumed)

Only pursue if v0 proves genuinely useful in practice:

- **Structured spec database**: a maintained (likely hand-curated,
  not scraped — spec-sheet scraping is its own reliability problem)
  component-spec table, keyed to the same product identity used elsewhere
  in this tool.
- **Constraint-based enumeration**: given a target (≥48GB VRAM, 64-128GB
  RAM), generate valid candidate configurations automatically, respecting
  compatibility constraints (PCIe/case/PSU/RAM-channel limits) — this is the
  actual "compatibility engine" the original roadmap note disclaimed
  building. Treat this as a real, separate engineering decision to make
  explicitly when reached, not an assumed next step.
- **Cross-vendor/cross-class value comparison**: e.g. top AMD GPU vs. top
  NVIDIA GPU by historical price-per-VRAM-GB or similar derived metric —
  generalizes the core roadmap's existing narrow "price-per-GB derived
  column (storage/RAM only)" v3+ note into a broader comparison, but only
  once a real spec database exists to normalize against.

## Explicitly not doing (v0, and likely longer)

- Automated component discovery/recommendation beyond what the user
  explicitly names — this is a comparator for choices you're already
  weighing, not a build-recommendation engine.
- Real-time compatibility validation against a live parts database (that's
  PCPartPicker's actual job; duplicating it isn't this tool's purpose even
  in the experimental v1+ escalation).

## Parked visual exploration — not v0 scope

These ideas remain available for a later, explicit frontend/spec-data decision;
they do not belong to the Dash-based manual v0 comparator. A 3D chassis model
implicitly needs the form-factor, slot, and component-placement data that v0
deliberately does not collect.

### 1. Interactive 3D Exploded-View Rig (`@react-three/fiber` / WebGL, parked)
- **Stylized Blueprint Schematic**: Renders a clean architectural wireframe or matte chassis model populated with the user's selected components.
- **Exploded View Control**: An interactive slider expands components outward from the chassis (AIO cooler lifts up, GPUs slide out, RAM sticks elevate), with HUD callouts connecting 3D parts to their live landed prices.
- **Interactive Component Highlighting**: Clicking any component in the cost table isolates and highlights that exact slot in the 3D rig.

### 2. Multi-Build Value Radar & Historical Cost Scrubber (parked)
- **Multi-Metric Spider/Radar Chart**: Visualizes multi-dimensional trade-offs between competing configurations (e.g. 4×3080 Ti vs. 2×3090 Ti vs. 1×A6000):
  - Total Landed Cost (€)
  - VRAM Capacity (GB)
  - Aggregate Memory Bandwidth (GB/s)
  - Estimated Total System TDP (Watts)
  - Component Sourcing Volatility
- **Historical Cost Timeline Scrubber**: A global timeline slider enabling users to scrub back across 1M, 3M, 6M, and 1Y to see what each total build configuration cost historically.

---

## Temporary Changelog

### 2026-08-15 (Gemini UI/UX Review Pass)
- Recorded the **Interactive 3D Exploded-View Rig** (`@react-three/fiber` /
  WebGL) as a parked visual experiment, not v0 scope.
- Added **Multi-Build Value Radar** and **Historical Cost Timeline Scrubber** specifications.
- Added **User Assumptions & Notes** field requirement for v0 configurations.
