"""SQLite persistence for Online Price Comparator."""

from .candidates import CandidateListing, CandidateListingRepository
from .custom_urls import (
    CustomListingUrl,
    CustomListingUrlRepository,
    extract_site_info_from_url,
)
from .db import create_db_engine
from .repository import (
    ListingRepository,
    ListingSummary,
    PriceHistoryRepository,
    ProductRepository,
    SitePricePoint,
)
from .watchlist import (
    SiteOverrideRepository,
    SiteSettingsRepository,
    TrackedProductRepository,
    resolve_site_keys,
)

__all__ = [
    "CandidateListing",
    "CandidateListingRepository",
    "CustomListingUrl",
    "CustomListingUrlRepository",
    "ListingRepository",
    "ListingSummary",
    "PriceHistoryRepository",
    "ProductRepository",
    "SiteOverrideRepository",
    "SitePricePoint",
    "SiteSettingsRepository",
    "TrackedProductRepository",
    "create_db_engine",
    "extract_site_info_from_url",
    "resolve_site_keys",
]
