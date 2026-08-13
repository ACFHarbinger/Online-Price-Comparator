# Architecture Overview

`Python-Module-Template` follows a modular Python package layout designed for speed, type safety, and testability.

```
src/python_module_template/
├── __init__.py      # Public API exports
├── core.py          # Core processing pipeline & DataProcessor class
├── utils.py         # Shared utility functions
├── cli.py           # Command line interface
└── py.typed         # PEP 561 type annotation marker
```

## Core Components

- **`DataProcessor` (`core.py`)**: Stateful pipeline orchestrator operating on dictionary payloads.
- **`calculate_digest` / `format_metadata` (`utils.py`)**: Stateless formatting and cryptographic hashing utilities.
- **`main()` (`cli.py`)**: CLI entry point supporting command argument parsing.
