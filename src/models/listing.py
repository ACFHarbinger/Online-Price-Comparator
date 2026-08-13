"""Shared data contract produced by both search providers and scrapers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass(frozen=True)
class RawListing:
    """A single unnormalized listing result from a search provider or scraper.

    Both `search.base.SearchProvider` and `scrapers.base.ScraperAdapter`
    implementations return lists of this type, so `pipeline.discover` can
    treat every source uniformly regardless of how the data was fetched.
    """

    source: str
    source_kind: Literal["search_api", "scraper"]
    title: str
    url: str
    price_text: str
    currency_hint: str | None
    image_url: str | None
    site_display_name: str
    fetched_at: datetime
    extra: dict[str, Any] = field(default_factory=dict)
