"""Shared polite search-page scraper behaviour for Iberian retailers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
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
from scrapers.structured_data import StructuredProduct, extract_structured_products

LOGGER = logging.getLogger(__name__)

_MIN_INTERVAL_SECONDS: Final = 12.0
_BLOCK_MARKERS: Final = (
    "captcha",
    "access denied",
    "verify you are human",
    "cloudflare",
    "unusual traffic",
)


@dataclass(frozen=True)
class RetailerParserConfig:
    """Site-specific endpoints and CSS selectors for a retailer adapter."""

    site_key: str
    display_name: str
    base_url: str
    search_url_template: str
    card_selector: str
    title_selector: str
    price_selector: str
    link_selector: str


class IberianRetailerScraper:
    """Fail-closed JSON-LD-first scraper with a site-specific CSS fallback."""

    def __init__(self, config: RetailerParserConfig) -> None:
        self._config = config
        self.site_key = config.site_key
        self._limiter = HostRateLimiter(_MIN_INTERVAL_SECONDS)

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        """Return up to ``limit`` listings, or ``[]`` when fetching fails."""
        if limit <= 0 or not query.strip():
            return []

        settings = get_settings()
        breaker = CircuitBreaker()
        if breaker.is_open(self.site_key):
            LOGGER.info(
                "skipping %s because its circuit breaker is open", self.site_key
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

            search_url = self._config.search_url_template.format(
                query=quote_plus(query)
            )
            if not is_allowed(
                search_url,
                DEFAULT_USER_AGENT,
                cache_ttl_hours=settings.robots_cache_ttl_hours,
            ):
                LOGGER.warning(
                    "robots.txt disallows %s; skipping %s", search_url, self.site_key
                )
                return []

            host = self._config.base_url.removeprefix("https://").removeprefix(
                "http://"
            )
            self._limiter.wait(host)
            with build_http_client() as client:
                response = get_with_retry(
                    client,
                    search_url,
                    headers={"Accept-Language": "pt-PT,pt;q=0.9,en;q=0.7"},
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
            LOGGER.warning("%s search failed", self._config.display_name, exc_info=True)
            return []

    def _listings_from_html(self, html: str, *, limit: int) -> list[RawListing]:
        """Parse a search page, preferring complete schema.org product records."""
        if any(marker in html.lower() for marker in _BLOCK_MARKERS):
            LOGGER.warning("%s search appears blocked", self._config.display_name)
            return []

        soup = BeautifulSoup(html, "lxml")
        structured = self._structured_listings(soup, limit=limit)
        if structured:
            return structured

        listings: list[RawListing] = []
        seen_urls: set[str] = set()
        fetched_at = datetime.now().astimezone()
        for card in soup.select(self._config.card_selector):
            if len(listings) >= limit:
                break
            listing = self._parse_card(card, fetched_at)
            if listing is not None and listing.url not in seen_urls:
                seen_urls.add(listing.url)
                listings.append(listing)
        if not listings:
            LOGGER.warning(
                "%s returned no recognizable product cards", self._config.display_name
            )
        return listings

    def _structured_listings(
        self, soup: BeautifulSoup, *, limit: int
    ) -> list[RawListing]:
        fetched_at = datetime.now().astimezone()
        return [
            self._listing_from_structured(product, fetched_at)
            for product in extract_structured_products(soup)[:limit]
        ]

    def _listing_from_structured(
        self, product: StructuredProduct, fetched_at: datetime
    ) -> RawListing:
        return RawListing(
            source=self.site_key,
            source_kind="scraper",
            title=product.title,
            url=urljoin(self._config.base_url, product.url),
            price_text=product.price_text,
            currency_hint=product.currency or "EUR",
            image_url=(
                urljoin(self._config.base_url, product.image_url)
                if product.image_url
                else None
            ),
            site_display_name=self._config.display_name,
            fetched_at=fetched_at,
            extra={"parser": "json_ld"},
        )

    def _parse_card(self, card: Tag, fetched_at: datetime) -> RawListing | None:
        title_element = card.select_one(self._config.title_selector)
        price_element = card.select_one(self._config.price_selector)
        link_element = card.select_one(self._config.link_selector) or card.select_one(
            "a[href]"
        )
        if title_element is None or price_element is None or link_element is None:
            return None
        title = title_element.get_text(" ", strip=True) or _attribute(
            title_element, "aria-label"
        )
        price_text = (
            _attribute(price_element, "content")
            or _attribute(price_element, "data-price")
            or price_element.get_text(" ", strip=True)
        )
        href = _attribute(link_element, "href")
        if not title or not price_text or href is None:
            return None

        image = card.select_one("img")
        image_path = _attribute(image, "src") or _attribute(image, "data-src")
        return RawListing(
            source=self.site_key,
            source_kind="scraper",
            title=title,
            url=urljoin(self._config.base_url, href),
            price_text=price_text,
            currency_hint="EUR" if "€" in price_text else None,
            image_url=urljoin(self._config.base_url, image_path)
            if image_path
            else None,
            site_display_name=self._config.display_name,
            fetched_at=fetched_at,
            extra={"parser": "css"},
        )


def _attribute(element: Tag | None, name: str) -> str | None:
    if element is None:
        return None
    value = element.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else None
