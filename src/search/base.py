"""Protocol every search-API provider must implement."""

from __future__ import annotations

from typing import Protocol

from models.listing import RawListing


class SearchProvider(Protocol):
    """A general search-API provider (e.g. SerpAPI, Google CSE). Structurally
    identical to `scrapers.base.ScraperAdapter` so `pipeline.discover` can
    treat every source uniformly."""

    name: str

    def is_configured(self) -> bool:
        """Return True if this provider has the credentials it needs to run."""
        ...

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        """Fetch listings for `query` via this provider's API.

        Must not raise on ordinary failures (no results, API error) — log and
        return `[]` instead. Only called when `is_configured()` is True.
        """
        ...
