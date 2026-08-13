# Testing Strategy

We enforce strict test coverage and type checking for all production code.

## Test Suite Overview

- **Framework**: `pytest`
- **Coverage**: `pytest-cov` (target: 95%+)
- **Type Checking**: `mypy` strict mode

## Running Tests

```bash
just test
```

## Writing Tests

Place new unit test modules under `test/` named `test_*.py`. Use standard `pytest` fixtures defined in `test/conftest.py`.
