"""Search-API provider registry, gated by configuration.

To add a new provider: implement `SearchProvider` in `search/providers/`,
then add one line to `_build_all_providers()` below.
"""

from __future__ import annotations

import logging

from config.settings import Settings
from search.base import SearchProvider
from search.providers.ebay import EbayBrowseProvider
from search.providers.google_cse import GoogleCseProvider
from search.providers.null_provider import NullProvider
from search.providers.serpapi import SerpApiProvider

logger = logging.getLogger(__name__)


def _build_all_providers(settings: Settings) -> list[SearchProvider]:
    """Every known provider, configured or not. Extend this list to add a provider."""
    return [
        NullProvider(),
        SerpApiProvider(api_key=settings.serpapi_key or ""),
        EbayBrowseProvider(
            client_id=settings.ebay_client_id,
            client_secret=settings.ebay_client_secret,
            marketplace_id=settings.ebay_marketplace_id,
        ),
        GoogleCseProvider(
            api_key=settings.google_cse_api_key,
            cx=settings.google_cse_cx,
        ),
    ]


def enabled_providers(settings: Settings) -> list[SearchProvider]:
    """Providers that are actually usable right now (have required credentials).

    Never raises: an unconfigured provider is skipped with a log line, not an
    error, so the tool works with zero API keys configured.
    """
    providers = []
    for provider in _build_all_providers(settings):
        if provider.is_configured():
            providers.append(provider)
        else:
            logger.info("Search provider skipped (not configured): %s", provider.name)
    return providers
