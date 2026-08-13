# Code Refactoring Rules

- Refactors must not change observable behavior in the same change as a behavior fix — separate the two into different commits/PRs.
- Run the existing test suite before and after; a refactor that requires rewriting tests to pass is probably a behavior change in disguise.
- Prefer extracting/renaming over rewriting from scratch — smaller diffs are easier to review and revert.
- Remove dead code you find along the way instead of leaving it "just in case"; git history is the safety net.
- Don't introduce a new abstraction for a pattern used only once or twice — wait for a third occurrence.
