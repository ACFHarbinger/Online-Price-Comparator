# Workflow: Data Pipeline Change

1. Identify the schema of the data entering and leaving the pipeline stage being changed.
2. Add/update a migration if the change touches a persisted schema; never mutate historical data in place without a backup.
3. Run the pipeline against a representative sample before a full run.
4. Validate row counts and a few spot-checked records against expectations post-run.
5. Document the schema change in `docs/` and bump any versioned data contract.
