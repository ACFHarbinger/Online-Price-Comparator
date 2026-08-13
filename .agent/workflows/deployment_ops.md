# Workflow: Deployment / Ops Change

1. Confirm the change is covered by CI (build, test, lint) before touching deployment config.
2. Stage the change in a non-production environment first when one exists.
3. Review the diff for secrets or environment-specific values that shouldn't be committed.
4. Roll out with a rollback plan already identified (previous image tag, feature flag, revert commit).
5. Monitor logs/metrics immediately after rollout for the specific failure modes the change could introduce.
