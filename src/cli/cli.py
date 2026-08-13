"""Command-line interface entry point for Python-Module-Template."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from core import DataProcessor, ProcessorConfig
from utils import format_metadata


def main(argv: Sequence[str] | None = None) -> int:
    """CLI main execution entry point.

    Args:
        argv: Optional command line argument list.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = argparse.ArgumentParser(
        prog="python-module-template",
        description="Standardized Python-Module-Template CLI Runner",
    )
    parser.add_argument("--version", action="store_true", help="Show version info")
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Batch size parameter"
    )

    args = parser.parse_args(argv)

    if args.version:
        print(format_metadata("python-module-template", "0.1.0"))
        return 0

    config = ProcessorConfig(batch_size=args.batch_size)
    processor = DataProcessor(config)
    print(f"Initialized processor with batch size: {processor.config.batch_size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
