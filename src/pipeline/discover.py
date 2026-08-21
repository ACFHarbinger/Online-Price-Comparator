"""Fan out a product query to every enabled search provider and scraper."""

from __future__ import annotations

from sqlalchemy import Engine

from config.settings import Settings
from models.listing import RawListing
from scrapers.registry import enabled_scrapers
from search.registry import enabled_providers
from storage.watchlist import (
    SiteOverrideRepository,
    SiteSettingsRepository,
    resolve_site_keys,
)


def run_discovery(
    query: str,
    settings: Settings,
    *,
    limit: int = 20,
    engine: Engine | None = None,
    tracked_product_id: int | None = None,
    skip_site_keys: frozenset[str] | None = None,
) -> list[RawListing]:
    """Collect raw listings for `query` from every configured source.

    Each provider/scraper is responsible for its own error handling (per the
    `SearchProvider`/`ScraperAdapter` contracts, they return `[]` rather than
    raising), so a single broken source never prevents the others from
    contributing results.

    When ``engine`` is provided, globally disabled ``site_settings`` rows and
    (if ``tracked_product_id`` is set) per-product site overrides further
    filter scrapers. Search-API providers are not site-keyed and are left
    unchanged. ``engine is None`` preserves the pre-v2.1 env-allowlist-only
    behaviour.

    ``skip_site_keys`` (v2.14 per-site cadence) lets a caller - the scheduled
    refresh tick - tell discovery not to re-query sites whose own
    ``min_refresh_interval_hours`` has not elapsed, independent of the
    product-level cadence. ``None`` means "no site-level gating" (e.g. a manual
    dashboard search).
    """
    results: list[RawListing] = []
    for provider in enabled_providers(settings):
        results.extend(provider.search(query, limit=limit))

    scrapers = enabled_scrapers(settings)
    if engine is not None:
        overrides = (
            SiteOverrideRepository(engine).as_map(tracked_product_id)
            if tracked_product_id is not None
            else {}
        )
        allowed = set(
            resolve_site_keys(
                [scraper.site_key for scraper in scrapers],
                globally_disabled=SiteSettingsRepository(engine).disabled_keys(),
                overrides=overrides,
            )
        )
        scrapers = [scraper for scraper in scrapers if scraper.site_key in allowed]

    if skip_site_keys:
        scrapers = [
            scraper for scraper in scrapers if scraper.site_key not in skip_site_keys
        ]

    for scraper in scrapers:
        results.extend(scraper.search(query, limit=limit))
    return results
