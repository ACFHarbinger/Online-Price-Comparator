# Skill: Build and Test Everything

Run the full build + test cycle across every language module.

```bash
just lint    # runs ruff/eslint/ktlint/clippy/gofmt/clang-format across all modules
just test    # runs pytest/vitest/gradle test/cargo test/go test/ctest across all modules
just docs    # builds the MkDocs + Sphinx documentation site
```

Use this before opening a PR, or whenever asked to "make sure everything still works."
Report which module(s) failed and the first failing assertion/error, not just "tests failed."
