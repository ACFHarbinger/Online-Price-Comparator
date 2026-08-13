# Code Review Rules

- Review for correctness first, then simplification, then style — don't bikeshed formatting on a PR with a real bug.
- Flag missing test coverage for new branches/edge cases explicitly, with a concrete failing scenario, not just "add more tests."
- Call out security-sensitive changes (auth, input parsing, secrets, deserialization) even if outside the PR's stated scope.
- Prefer suggesting the specific fix over describing the problem abstractly — reviewers should be able to act on a comment without re-deriving it.
- Approve when the change is a net improvement, not only when it is perfect.
