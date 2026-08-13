"""Generic utility helpers for Online Price Comparator."""

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
