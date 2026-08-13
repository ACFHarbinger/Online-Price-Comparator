"""Utility functions for Python-Module-Template."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def calculate_digest(data: dict[str, Any]) -> str:
    """Calculate SHA-256 hex digest for a JSON-serializable dictionary.

    Args:
        data: Dictionary payload.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def format_metadata(
    name: str, version: str, extra: dict[str, Any] | None = None
) -> str:
    """Format metadata attributes into a standardized string descriptor.

    Args:
        name: Module or component name.
        version: Version string.
        extra: Optional additional key-value attributes.

    Returns:
        Formatted descriptor string.
    """
    base = f"{name} v{version}"
    if extra:
        extra_str = ", ".join(f"{k}={v}" for k, v in sorted(extra.items()))
        return f"{base} ({extra_str})"
    return base
