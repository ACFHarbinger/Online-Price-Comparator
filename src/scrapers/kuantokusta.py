"""KuantoKusta outbound-retailer URL hints, deliberately not price listings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Final
from urllib.parse import quote_plus, urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag

from config.settings import get_settings
from fetch.circuit_breaker import CircuitBreaker
from fetch.http_client import DEFAULT_USER_AGENT, build_http_client, get_with_retry
from fetch.rate_limit import HostRateLimiter
from fetch.response_cache import get_cached, set_cached
from fetch.robots import is_allowed

LOGGER = logging.getLogger(__name__)

_BASE_URL: Final = "https://www.kuantokusta.pt"
_SEARCH_URL: Final = f"{_BASE_URL}/search?q={{query}}"
_MIN_INTERVAL_SECONDS: Final = 15.0
_BLOCK_MARKERS: Final = (
    "captcha",
    "access denied",
    "verify you are human",
    "cloudflare",
)
_CARD_SELECTOR: Final = "article, .product-card, [data-testid*='product']"
_TITLE_SELECTOR: Final = "h2, h3, .product-name, [data-testid*='product-name']"


@dataclass(frozen=True)
class RetailerUrlHint:
    """A candidate retailer URL discovered by an aggregator, never a price row."""

    title: str
    destination_url: str
    discovered_at: datetime
    hint_source: str = "kuantokusta"


class KuantoKustaHintSource:
    """Discover external retailer URLs without returning ``RawListing`` values.

    The separate return type makes it impossible for this source to flow through
    ``pipeline.discover`` and persist KuantoKusta's comparison price. A caller
    must fetch and match a hinted retailer URL before it can become a listing.
    """

    site_key = "kuantokusta"

    def __init__(self) -> None:
        self._limiter = HostRateLimiter(_MIN_INTERVAL_SECONDS)

    def search(self, query: str, *, limit: int = 20) -> list[RetailerUrlHint]:
        """Return external retailer URL hints, or ``[]`` on any ordinary failure."""
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
                hints = self._hints_from_html(cached, limit=limit)
                self._record_result(breaker, hints)
                return hints

            search_url = _SEARCH_URL.format(query=quote_plus(query))
            if not is_allowed(
                search_url,
                DEFAULT_USER_AGENT,
                cache_ttl_hours=settings.robots_cache_ttl_hours,
            ):
                LOGGER.warning(
                    "robots.txt disallows %s; skipping %s", search_url, self.site_key
                )
                return []

            self._limiter.wait("www.kuantokusta.pt")
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
            hints = self._hints_from_html(html, limit=limit)
            if hints:
                set_cached(self.site_key, query, html)
            self._record_result(breaker, hints)
            return hints
        except Exception:
            breaker.record_failure(self.site_key)
            LOGGER.warning("KuantoKusta hint search failed", exc_info=True)
            return []

    def _hints_from_html(self, html: str, *, limit: int) -> list[RetailerUrlHint]:
        """Extract only external merchant links; ignore aggregator product links."""
        if any(marker in html.lower() for marker in _BLOCK_MARKERS):
            LOGGER.warning("KuantoKusta search appears blocked")
            return []

        soup = BeautifulSoup(html, "lxml")
        hints: list[RetailerUrlHint] = []
        seen_urls: set[str] = set()
        discovered_at = datetime.now().astimezone()
        for card in soup.select(_CARD_SELECTOR):
            if len(hints) >= limit:
                break
            title_element = card.select_one(_TITLE_SELECTOR)
            title = title_element.get_text(" ", strip=True) if title_element else ""
            if not title:
                continue
            for link in card.select("a[href]"):
                destination_url = _external_url(_attribute(link, "href"))
                if destination_url is None or destination_url in seen_urls:
                    continue
                seen_urls.add(destination_url)
                hints.append(
                    RetailerUrlHint(
                        title=title,
                        destination_url=destination_url,
                        discovered_at=discovered_at,
                    )
                )
                break
        return hints

    def _record_result(
        self, breaker: CircuitBreaker, hints: list[RetailerUrlHint]
    ) -> None:
        if hints:
            breaker.record_success(self.site_key)
        else:
            breaker.record_failure(self.site_key)


def _external_url(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    hostname = parsed.hostname or ""
    if hostname == "kuantokusta.pt" or hostname.endswith(".kuantokusta.pt"):
        return None
    return value


def _attribute(element: Tag, name: str) -> str | None:
    value = element.get(name)
    return value.strip() if isinstance(value, str) and value.strip() else None
