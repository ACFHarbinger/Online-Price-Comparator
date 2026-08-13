# Workflow: Code Review

1. Read the diff in full before commenting — don't review file-by-file in isolation when a change spans multiple files.
2. Run the test suite and linters locally (or confirm CI is green) before starting a substantive review.
3. Check the change against `.agent/rules/code_review.md` and the relevant language rule file.
4. Leave findings ranked by severity: correctness/security first, then design, then style/nits.
5. For each finding, state the concrete failure scenario (input → wrong output), not just "this looks wrong."
6. Approve once blocking issues are resolved; don't hold a PR hostage over nits.
