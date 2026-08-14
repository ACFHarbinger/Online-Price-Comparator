"""Scraper adapter for Amazon storefront search results.

Parameterized by domain (``amazon.es``, later ``amazon.fr`` / ``amazon.de``, …)
via ``_DOMAIN_CONFIG``. Only ``amazon.es`` is wired up here.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Final, TypedDict
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

_MIN_INTERVAL_SECONDS: Final = 8.0

_CARD_SELECTOR: Final = (
    'div[data-component-type="s-search-result"], div.s-result-item[data-asin]'
)
_TITLE_HEADING_SELECTOR: Final = "h2"
_PRICE_SELECTOR: Final = "span.a-price"
_PRICE_TEXT_SELECTOR: Final = "span.a-offscreen"
_PRICE_FALLBACK_SELECTOR: Final = "span.a-color-price, span.a-price-whole"
_IMAGE_SELECTOR: Final = "img.s-image, img"
_RATING_SELECTOR: Final = "span.a-icon-alt"
_BLOCK_MARKERS: Final = (
    "bm-verify",
    "triggerinterstitialchallenge",
    "/_sec/verify",
    "validatecaptcha",
    "opfcaptcha",
    "api-services-support@amazon.com",
    "to discuss automated access",
    "enter the characters you see",
)
_NON_TITLE_HEADINGS: Final = frozenset({"sponsored", "patrocinado"})


class _DomainConfig(TypedDict):
    currency: str
    locale: str
    display_name: str


_DOMAIN_CONFIG: Final[dict[str, _DomainConfig]] = {
    "amazon.es": {
        "currency": "EUR",
        "locale": "es-ES",
        "display_name": "Amazon.es",
    },
}


class AmazonScraper:
    """Fetch product listings from an Amazon storefront search page."""

    def __init__(self, domain: str = "amazon.es") -> None:
        if domain not in _DOMAIN_CONFIG:
            supported = ", ".join(sorted(_DOMAIN_CONFIG))
            raise ValueError(
                f"unsupported Amazon domain {domain!r}; configured domains: {supported}"
            )
        self.domain = domain
        self.site_key = domain
        self._config = _DOMAIN_CONFIG[domain]
        self._base_url = f"https://www.{domain}"
        self._limiter = HostRateLimiter(_MIN_INTERVAL_SECONDS)

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        """Return up to ``limit`` listings, or an empty list on any failure."""
        if limit <= 0 or not query.strip():
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

            search_url = f"{self._base_url}/s?k={quote_plus(query)}"
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

            locale = self._config["locale"]
            language = locale.split("-", 1)[0]
            self._limiter.wait(self.domain)
            with build_http_client() as client:
                response = get_with_retry(
                    client,
                    search_url,
                    headers={
                        "Accept-Language": (f"{locale},{language};q=0.9,en;q=0.8"),
                    },
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
            LOGGER.warning("Amazon (%s) search failed", self.domain, exc_info=True)
            return []

    def _listings_from_html(self, html: str, *, limit: int) -> list[RawListing]:
        """Parse a search-results HTML body into listings (or [] if unusable)."""
        if _is_blocked_page(html):
            LOGGER.warning("Amazon search blocked or challenged for %s", self.domain)
            return []

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(_CARD_SELECTOR)
        if not cards:
            LOGGER.warning(
                "Amazon (%s) returned no recognizable product cards",
                self.domain,
            )
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
        """Convert one search-result card when title, URL, and price exist."""
        asin = _attribute(card, "data-asin")
        if not asin:
            return None

        title = self._extract_title(card)
        price_text = self._extract_price_text(card)
        url = self._extract_url(card, asin)
        if not title or not price_text or url is None:
            return None

        return RawListing(
            source=self.site_key,
            source_kind="scraper",
            title=title,
            url=url,
            price_text=price_text,
            currency_hint=self._config["currency"],
            image_url=self._extract_image_url(card),
            site_display_name=self._config["display_name"],
            fetched_at=fetched_at,
            extra=_extract_extra(card, asin),
        )

    def _extract_title(self, card: Tag) -> str:
        """Return the product title from an ``h2`` or the image alt text."""
        for heading in card.select(_TITLE_HEADING_SELECTOR):
            aria = _attribute(heading, "aria-label")
            if aria and aria.strip().lower() not in _NON_TITLE_HEADINGS:
                return aria.strip()
            text = heading.get_text(" ", strip=True)
            if text and text.lower() not in _NON_TITLE_HEADINGS:
                return text

        image = card.select_one(_IMAGE_SELECTOR)
        alt = _attribute(image, "alt")
        return alt.strip() if alt else ""

    def _extract_price_text(self, card: Tag) -> str:
        """Return the raw on-page price string, skipping struck-through list prices."""
        for price in card.select(_PRICE_SELECTOR):
            if _attribute(price, "data-a-strike") == "true":
                continue
            offscreen = price.select_one(_PRICE_TEXT_SELECTOR)
            if offscreen is not None:
                text = offscreen.get_text(" ", strip=True)
                if text:
                    return text

        fallback = card.select_one(_PRICE_FALLBACK_SELECTOR)
        if fallback is None:
            return ""
        return fallback.get_text(" ", strip=True)

    def _extract_url(self, card: Tag, asin: str) -> str | None:
        """Return an absolute product URL, preferring a non-sponsored ``h2`` link."""
        for link in card.select("h2 a[href]"):
            href = _attribute(link, "href")
            if href and "/sspa/" not in href:
                return urljoin(f"{self._base_url}/", href)
        return urljoin(f"{self._base_url}/", f"dp/{asin}")

    def _extract_image_url(self, card: Tag) -> str | None:
        """Return an absolute product image URL when one is present."""
        image = card.select_one(_IMAGE_SELECTOR)
        for name in ("src", "data-src"):
            value = _attribute(image, name)
            if value and not value.startswith("data:"):
                return urljoin(f"{self._base_url}/", value)

        srcset = _attribute(image, "srcset")
        if not srcset:
            return None
        first = srcset.split(",", 1)[0].strip().split(None, 1)[0]
        if first and not first.startswith("data:"):
            return urljoin(f"{self._base_url}/", first)
        return None


def _attribute(element: Tag | None, name: str) -> str | None:
    """Return a scalar HTML attribute, ignoring absent and multi-value values."""
    if element is None:
        return None
    value = element.get(name)
    return value if isinstance(value, str) and value else None


def _extract_extra(card: Tag, asin: str) -> dict[str, str]:
    """Collect easy optional fields; empty values are omitted."""
    extra: dict[str, str] = {"asin": asin}
    rating = card.select_one(_RATING_SELECTOR)
    if rating is not None:
        rating_text = rating.get_text(" ", strip=True)
        if rating_text:
            extra["rating"] = rating_text
    return extra


def _is_blocked_page(html: str) -> bool:
    """True when the response is a CAPTCHA / bot-check interstitial, not results."""
    lowered = html.lower()
    return any(marker in lowered for marker in _BLOCK_MARKERS)
