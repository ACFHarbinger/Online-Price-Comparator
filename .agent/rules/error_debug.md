# Error Handling & Debugging Rules

- Reproduce the bug with a failing test before fixing it, when practical; the test stays in the suite afterward as a regression guard.
- Fix root causes, not symptoms — do not silence an exception/warning just to make a run "pass."
- Include enough context in error messages to debug from logs alone: what operation failed, on what input, and why.
- When a fix touches shared/critical code, check for other callers relying on the old (broken) behavior before changing it.
- Never use bare `except:`/catch-all handlers that swallow errors silently; log or re-raise.
