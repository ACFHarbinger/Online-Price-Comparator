"""Site scraper registry, gated by `ENABLED_SCRAPERS` configuration.

To add a new site: implement `ScraperAdapter` in `scrapers/`, then add one
line to `_build_all_scrapers()` below.
"""

from __future__ import annotations

from config.settings import Settings
from scrapers.amazon import AmazonScraper
from scrapers.base import ScraperAdapter
from scrapers.fnac import FnacScraper
from scrapers.pccomponentes import PcComponentesScraper
from scrapers.pcdiga import PcdigaScraper
from scrapers.worten import WortenScraper


def _build_all_scrapers(settings: Settings) -> list[ScraperAdapter]:
    """Every known scraper. Extend this list to add a site."""
    return [
        PcComponentesScraper(),
        AmazonScraper(domain="amazon.es"),
        PcdigaScraper(),
        WortenScraper(),
        FnacScraper(),
    ]


def registered_site_keys(settings: Settings) -> list[str]:
    """Site keys of every known scraper, ignoring enablement flags."""
    return [scraper.site_key for scraper in _build_all_scrapers(settings)]


def enabled_scrapers(settings: Settings) -> list[ScraperAdapter]:
    """Scrapers allowed by `ENABLED_SCRAPERS` (all of them if unset)."""
    allowlist = settings.enabled_scraper_keys()
    all_scrapers = _build_all_scrapers(settings)
    if allowlist is None:
        return all_scrapers
    return [s for s in all_scrapers if s.site_key in allowlist]
