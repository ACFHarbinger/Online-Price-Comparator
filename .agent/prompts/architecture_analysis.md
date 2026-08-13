# Prompt: Architecture Analysis

Given a request to analyze or propose architecture changes:

1. Read `docs/ARCHITECTURE.md` and `docs/structurizr/` (if present) for the current system model.
2. Identify the module boundaries affected and cross-reference `.agent/AGENTS.md` §3.
3. Present trade-offs (at least two options) rather than a single prescriptive answer, unless the choice is clear-cut.
4. Note migration cost and backward-compatibility impact for any proposed change.
5. If the analysis leads to a decision, record it as an ADR under `docs/adr/`.
