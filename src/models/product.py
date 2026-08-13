"""Canonical product identity a user is tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Product:
    """A product tracked across one or more site listings.

    Mirrors the `products` table: `query_text` is the original search
    keywords, `canonical_name` is filled in once a match is confirmed.
    """

    id: int
    query_text: str
    canonical_name: str | None
    created_at: datetime
