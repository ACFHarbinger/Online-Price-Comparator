"""Scraper adapter for PcComponentes search results."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Final
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from config.settings import get_settings
from fetch.circuit_breaker import CircuitBreaker
from fetch.http_client import DEFAULT_USER_AGENT, build_http_client, get_with_retry
from fetch.rate_limit import HostRateLimiter
from fetch.response_cache import get_cached, set_cached
from fetch.robots import is_allowed
from models.listing import RawListing

LOGGER = logging.getLogger(__name__)

_MIN_INTERVAL_SECONDS: Final = 15.0
_BASE_URL: Final = "https://www.pccomponentes.com"
_SEARCH_URL: Final = f"{_BASE_URL}/buscar/?query={{query}}"
_CARD_SELECTOR: Final = (
    "article[data-testid='product-card'], [data-testid='product-card'], "
    "article.product-card, div.product-card"
)
_TITLE_SELECTOR: Final = ".product-card__title, .c-product-card__title, h3"
_PRICE_SELECTOR: Final = (
    ".c-product-card__prices-actual, .product-card__price, "
    "[data-testid='product-price']"
)


class PcComponentesScraper:
    """Fetch product listings from PcComponentes' server-rendered search page."""

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

        try:
            cached = get_cached(self.site_key, query)
            if cached is not None:
                listings = self._listings_from_html(cached, limit=limit)
                if listings:
                    breaker.record_success(self.site_key)
                    return listings
                breaker.record_failure(self.site_key)
                return []

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

            limiter = HostRateLimiter(_MIN_INTERVAL_SECONDS)
            limiter.wait("pccomponentes.com")
            with build_http_client() as client:
                response = get_with_retry(
                    client,
                    search_url,
                    max_attempts=settings.retry_max_attempts,
                    initial_backoff_seconds=settings.retry_initial_backoff_seconds,
                    max_backoff_seconds=settings.retry_max_backoff_seconds,
                )
                response.raise_for_status()

            html = response.text
            listings = self._listings_from_html(html, limit=limit)
            if listings:
                set_cached(self.site_key, query, html)
                breaker.record_success(self.site_key)
                return listings
            breaker.record_failure(self.site_key)
            return []
        except Exception:
            breaker.record_failure(self.site_key)
            LOGGER.warning("PcComponentes search failed", exc_info=True)
            return []

    def _listings_from_html(self, html: str, *, limit: int) -> list[RawListing]:
        """Parse a search-results HTML body into listings (or [] if unusable)."""
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(_CARD_SELECTOR)
        if not cards:
            LOGGER.warning("PcComponentes returned no recognizable product cards")
            return []

        fetched_at = datetime.now().astimezone()
        listings: list[RawListing] = []
        for card in cards:
            if len(listings) >= limit:
                break
            listing = self._parse_card(card, fetched_at)
            if listing is not None:
                listings.append(listing)
        return listings

    def _parse_card(self, card: Tag, fetched_at: datetime) -> RawListing | None:
        """Convert one product card to a listing when all required values exist."""
        title_element = card.select_one(_TITLE_SELECTOR)
        price_element = card.select_one(_PRICE_SELECTOR)
        if title_element is None or price_element is None:
            return None

        title = title_element.get_text(" ", strip=True)
        price_text = price_element.get_text(" ", strip=True)
        link_element = title_element.find("a", href=True) or card.select_one("a[href]")
        href = self._attribute(link_element, "href")
        if not title or not price_text or href is None:
            return None

        image_element = card.select_one("img")
        image_path = self._attribute(image_element, "src")
        if image_path is None:
            image_path = self._attribute(image_element, "data-src")

        image_url = (
            urljoin(_BASE_URL, image_path) if image_path is not None else None
        )
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
