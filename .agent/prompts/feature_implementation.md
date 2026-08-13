# Prompt: Feature Implementation

Given a feature request:

1. Restate the feature as concrete acceptance criteria.
2. Identify which language module(s) it touches and read `.agent/rules/<language>.md` for each.
3. Propose the smallest design that satisfies the criteria; flag any ambiguity as a question rather than assuming.
4. Implement with tests written alongside the code, not after.
5. Update `docs/` and `docs/moon/CHANGELOG.md` if the feature is user-visible.
