"""Scraper adapter for PcComponentes (.pt) search results.

Plain httpx is tried first (cheap, fast). PcComponentes sits behind a
Cloudflare JS challenge that httpx can never pass, so on failure this falls
back to a headless-browser render (`fetch.browser`) - only when explicitly
enabled and allowlisted via `Settings.browser_fallback_enabled` /
`browser_fallback_sites` (off by default). See `fetch/browser.py`'s module
docstring for what that fallback does and does not do.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Final
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag
from config.settings import Settings, get_settings
from fetch.browser import fetch_rendered_html
from fetch.circuit_breaker import CircuitBreaker
from fetch.http_client import DEFAULT_USER_AGENT, build_http_client, get_with_retry
from fetch.rate_limit import HostRateLimiter
from fetch.response_cache import get_cached, set_cached
from fetch.robots import is_allowed
from models.listing import RawListing

LOGGER = logging.getLogger(__name__)

_MIN_INTERVAL_SECONDS: Final = 15.0
_BASE_URL: Final = "https://www.pccomponentes.pt"
_SEARCH_URL: Final = f"{_BASE_URL}/buscar/?query={{query}}"

# Verified against genuine rendered search-result HTML (not guessed) - see
# docs/moon/roadmaps/scrapers_and_retailers.md for how these were found.
_CARD_SELECTOR: Final = ".product-card"
_TITLE_SELECTOR: Final = "[data-e2e='title-card']"
_PRICE_SELECTOR: Final = "[data-e2e='price-card']"
_LINK_SELECTOR: Final = "a[data-testid='normal-link']"


class PcComponentesScraper:
    """Fetch product listings from PcComponentes' search page."""

    site_key = "pccomponentes"

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        """Return up to ``limit`` listings, or an empty list on any failure."""
        if limit <= 0:
            return []

        settings = get_settings()
        breaker = CircuitBreaker()
        if breaker.is_open(self.site_key):
            until = breaker.open_until(self.site_key)
            until_text = until.isoformat() if until is not None else "unknown"
            LOGGER.info(
                "skipping %s, circuit breaker open until %s",
                self.site_key,
                until_text,
            )
            return []

        cached = get_cached(self.site_key, query)
        if cached is not None:
            listings = self._listings_from_html(cached, limit=limit)
            if listings:
                breaker.record_success(self.site_key)
                return listings

        search_url = _SEARCH_URL.format(query=quote_plus(query))
        if not is_allowed(
            search_url,
            DEFAULT_USER_AGENT,
            cache_ttl_hours=settings.robots_cache_ttl_hours,
        ):
            LOGGER.warning(
                "robots.txt disallows fetching %s; skipping %s",
                search_url,
                self.site_key,
            )
            return []

        html = self._fetch_via_httpx(search_url, settings)
        listings = self._listings_from_html(html, limit=limit) if html else []

        if not listings and self._browser_fallback_allowed(settings):
            headless = settings.browser_fallback_headless
            wait_seconds = (
                settings.browser_fallback_headless_wait_seconds
                if headless
                else settings.browser_fallback_manual_wait_seconds
            )
            LOGGER.info(
                "httpx path failed for %s; trying browser fallback (headless=%s)",
                self.site_key,
                headless,
            )
            html = fetch_rendered_html(
                search_url,
                headless=headless,
                wait_seconds=wait_seconds,
                user_agent=DEFAULT_USER_AGENT,
            )
            listings = self._listings_from_html(html, limit=limit) if html else []

        if listings:
            if html:
                set_cached(self.site_key, query, html)
            breaker.record_success(self.site_key)
            return listings

        breaker.record_failure(self.site_key)
        return []

    def _browser_fallback_allowed(self, settings: Settings) -> bool:
        return (
            settings.browser_fallback_enabled
            and self.site_key in settings.browser_fallback_site_keys()
        )

    def _fetch_via_httpx(self, search_url: str, settings: Settings) -> str | None:
        try:
            limiter = HostRateLimiter(_MIN_INTERVAL_SECONDS)
            limiter.wait("pccomponentes.pt")
            with build_http_client() as client:
                response = get_with_retry(
                    client,
                    search_url,
                    max_attempts=settings.retry_max_attempts,
                    initial_backoff_seconds=settings.retry_initial_backoff_seconds,
                    max_backoff_seconds=settings.retry_max_backoff_seconds,
                )
                response.raise_for_status()
            return response.text
        except Exception:
            LOGGER.warning("PcComponentes httpx fetch failed", exc_info=True)
            return None

    def _listings_from_html(self, html: str, *, limit: int) -> list[RawListing]:
        """Parse a search-results HTML body into listings (or [] if unusable)."""
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(_CARD_SELECTOR)
        if not cards:
            LOGGER.warning("PcComponentes returned no recognizable product cards")
            return []

        fetched_at = datetime.now().astimezone()
        listings: list[RawListing] = []
        seen_urls: set[str] = set()
        for card in cards:
            if len(listings) >= limit:
                break
            listing = self._parse_card(card, fetched_at)
            if listing is None:
                continue
            # PcComponentes sometimes links a refurbished ("Recondicionado")
            # variant card to the exact same product URL as the new one -
            # our schema is one row per (product, site, url), so keep only
            # the first (new-condition) card seen for a given URL.
            if listing.url in seen_urls:
                continue
            seen_urls.add(listing.url)
            listings.append(listing)
        return listings

    def _parse_card(self, card: Tag, fetched_at: datetime) -> RawListing | None:
        """Convert one product card to a listing when all required values exist."""
        title_element = card.select_one(_TITLE_SELECTOR)
        price_element = card.select_one(_PRICE_SELECTOR)
        if title_element is None or price_element is None:
            return None

        # The `[data-testid='normal-link']` anchor wraps the whole card as
        # its *parent*, not a descendant - .select_one() only searches
        # descendants, so this walks up rather than down for it.
        link_element = card.select_one(_LINK_SELECTOR)
        if link_element is None:
            parent = card.parent
            if isinstance(parent, Tag) and parent.name == "a":
                link_element = parent
        if link_element is None:
            return None

        title = title_element.get_text(" ", strip=True)
        price_text = price_element.get_text(" ", strip=True)
        href = self._attribute(link_element, "href")
        if not title or not price_text or href is None:
            return None

        image_element = card.select_one("img")
        image_path = self._attribute(image_element, "src")
        if image_path is None:
            image_path = self._attribute(image_element, "data-src")

        image_url = urljoin(_BASE_URL, image_path) if image_path is not None else None
        return RawListing(
            source=self.site_key,
            source_kind="scraper",
            title=title,
            url=urljoin(_BASE_URL, href),
            price_text=price_text,
            currency_hint="EUR" if "€" in price_text else None,
            image_url=image_url,
            site_display_name="PcComponentes",
            fetched_at=fetched_at,
        )

    @staticmethod
    def _attribute(element: Tag | None, name: str) -> str | None:
        """Return a scalar HTML attribute, ignoring absent and multi-value values."""
        if element is None:
            return None
        value = element.get(name)
        return value if isinstance(value, str) and value else None
