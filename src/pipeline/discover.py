"""Fan out a product query to every enabled search provider and scraper."""

from __future__ import annotations

from config.settings import Settings
from models.listing import RawListing
from scrapers.registry import enabled_scrapers
from search.registry import enabled_providers


def run_discovery(
    query: str, settings: Settings, *, limit: int = 20
) -> list[RawListing]:
    """Collect raw listings for `query` from every configured source.

    Each provider/scraper is responsible for its own error handling (per the
    `SearchProvider`/`ScraperAdapter` contracts, they return `[]` rather than
    raising), so a single broken source never prevents the others from
    contributing results.
    """
    results: list[RawListing] = []
    for provider in enabled_providers(settings):
        results.extend(provider.search(query, limit=limit))
    for scraper in enabled_scrapers(settings):
        results.extend(scraper.search(query, limit=limit))
    return results
