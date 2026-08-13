# Prompt: Safe Refactor

Given a refactor request:

1. Confirm test coverage exists for the code being touched; add characterization tests first if not.
2. Follow `.agent/workflows/code_refactor.md` — mechanical changes only, no behavior changes in the same commit.
3. Run the full test suite for the affected module(s) before and after.
4. List every call site updated, so the diff is auditable against the stated scope.
5. Flag anything that looked risky enough to warrant a human second look.
