"""Main entry point for Python-Module-Template."""

from __future__ import annotations

import sys

from cli.cli import main


def run() -> None:
    """Execute main entry point and exit with return code."""
    sys.exit(main())


if __name__ == "__main__":
    run()
