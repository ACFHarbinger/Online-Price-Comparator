# Test Writing Rules

- One assertion concept per test; name tests after the behavior under test (`test_<unit>_<condition>_<expected>`), not the implementation.
- Cover the happy path, at least one edge case, and at least one failure case for every new public function.
- Prefer real objects/fixtures over mocks; mock only true external boundaries (network, filesystem, clock, randomness).
- Tests must be deterministic — no reliance on wall-clock time, network access, or test execution order.
- A failing test's assertion message should make the failure diagnosable without opening a debugger.
