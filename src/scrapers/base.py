"""Protocol every site-specific scraper must implement."""

from __future__ import annotations

from typing import Protocol

from models.listing import RawListing


class ScraperAdapter(Protocol):
    """A site-specific scraper. Structurally identical to `search.base.SearchProvider`
    so `pipeline.discover` can treat every source uniformly."""

    site_key: str

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        """Fetch and parse listings for `query` from this site.

        Must not raise on ordinary failures (no results, network error, layout
        change) — log and return `[]` instead, so one broken scraper doesn't
        take down discovery for every other source.
        """
        ...
