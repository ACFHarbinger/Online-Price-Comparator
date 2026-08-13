"""Site-specific scraper adapters."""

from .base import ScraperAdapter
from .registry import enabled_scrapers

__all__ = ["ScraperAdapter", "enabled_scrapers"]
