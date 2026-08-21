# AGENT_BUS — index

Async, file-based coordination log for the agents working this repo
(currently Claude, opencode, grok, codex, agy — same convention borrowed
from `Image-Toolkit/.agent/bus/`). No shared runtime session — each agent
reads/writes these files independently, so treat them as the source of
truth for "who's doing what" and "what's actually landed," not the roadmap
docs' own inline status notes (those go stale — see the 2026-08-21 entry).

**Post new entries to today's file:** `.agent/bus/<YYYY-MM-DD>.md`
(create it if today doesn't have one yet, same heading convention as
below: `### <agent> — YYYY-MM-DD (topic)`).

**House rules (read before posting):**

1. **Verify against real code before claiming something is done or
   available to build on** — read the file, don't trust a roadmap doc's
   inline status or another agent's summary. `ROADMAP.md`'s status column
   is a pointer, not ground truth; it goes stale exactly like Image-Toolkit's
   GitHub issues did.
2. **Claim disjoint files before starting** — post which files/package
   you're taking so two agents don't collide on the same module. If someone
   else already claimed it, reply here before doing conflicting work.
3. **When you land something**, post: commit hash, what you verified it
   with (`ruff`/`mypy`/`pytest` — name which, and the test count if you ran
   the suite), and **what the next person's code should assume**. Update
   `docs/moon/CHANGELOG.md` and the relevant roadmap doc's inline status
   note (`ROADMAP.md` + the specific `docs/moon/roadmaps/*.md` file) in the
   same commit.
4. **No GitHub issues yet** — `gh` isn't set up in every agent's
   environment. Use the roadmap IDs (`v1.4`, `v1.5`, ...) from
   `docs/moon/ROADMAP.md` as the unit of claim/landing until that changes.
5. **Harbinger** (pkhunter, the user) is the human sign-off role — same as
   Image-Toolkit. Don't invent an agent identity for that; flag anything
   needing a product/scope decision by name, addressed to Harbinger.
6. **No test-execution caution active** — the CPU-cooler issue that used to
   block `pytest`/`just test` is resolved (2026-08-21). Full suite runs are
   fine.

**Reading history:** the current/most-recent day lives under `.agent/bus/`;
once a day stops being "today," move it to `.agent/archive/bus/<date>.md`
and start a fresh dated file (same pattern as Image-Toolkit).

| Day | Location |
|---|---|
| 2026-08-21 (current) | `.agent/bus/2026-08-21.md` |
