# Workflow: Debugging an Error

1. Reproduce the failure deterministically — capture the exact input, command, and environment.
2. Read the full stack trace/log before forming a hypothesis; don't guess from the last line alone.
3. Bisect: comment out / isolate halves of the suspect code path until the failure localizes to a small region.
4. Write a minimal failing test that reproduces the bug in isolation.
5. Fix the root cause, confirm the new test passes, then run the broader suite for regressions.
6. Document the root cause and fix in the commit message — not just "fixed bug."
