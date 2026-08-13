# Workflow: Writing Tests

1. Identify the unit under test and its public contract (inputs, outputs, side effects, error modes).
2. Write the happy-path test first, then edge cases (empty input, boundary values, max size), then failure cases.
3. Run the new test and confirm it fails for the right reason before implementing the fix/feature.
4. Implement, then re-run until green. Run the full module's test suite to check for regressions.
5. Check coverage of the new/changed lines; add tests for any branch left uncovered that matters.
