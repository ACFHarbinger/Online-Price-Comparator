"""Online Price Comparator normalization package."""

from __future__ import annotations

from .price import parse_price
from .text import dedupe_key, normalize_title

__all__ = [
    "dedupe_key",
    "normalize_title",
    "parse_price",
]
