# Workflow: GUI Feature

1. Sketch the component tree and identify what state lives where (local vs. shared/store).
2. Build the presentational component first with mock data/props, verify it renders correctly.
3. Wire it to real data/state; handle loading, empty, and error states explicitly.
4. Add keyboard navigation and accessible labels.
5. Add a component/integration test, then manually exercise the golden path and at least one edge case in a running instance.
