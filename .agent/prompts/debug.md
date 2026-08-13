# Prompt: Debug an Issue

Given a bug report:

1. Reproduce it first — do not attempt a fix from the description alone.
2. Follow `.agent/workflows/error_debug.md`.
3. Identify the minimal root cause; explain why the current code produces the wrong result.
4. Fix and add a regression test.
5. Report back with: root cause, fix, and what the regression test now guards against.
