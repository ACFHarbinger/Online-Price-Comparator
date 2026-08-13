# Workflow: Refactoring

1. Confirm test coverage exists for the code being refactored; add characterization tests first if it doesn't.
2. Make one mechanical change at a time (rename, extract function, move file) and re-run tests after each.
3. Never mix a refactor with a behavior change — split into separate commits if both are needed.
4. Update all call sites and documentation references in the same change as the rename/move.
5. Delete now-dead code rather than commenting it out.
