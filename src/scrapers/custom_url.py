"""Single-page fetcher and parser for custom listing URLs (v2.15 Tier A)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from fetch.http_client import build_http_client, get_with_retry
from fetch.rate_limit import HostRateLimiter
from fetch.robots import is_allowed
from models.listing import RawListing
from scrapers.structured_data import extract_structured_products
from storage.custom_urls import extract_site_info_from_url

LOGGER = logging.getLogger(__name__)

# Default rate limiter for custom domains
# (conservative 3.0s between requests to same host)
_CUSTOM_RATE_LIMITER = HostRateLimiter(min_interval_seconds=3.0)


def _extract_meta_tag(soup: BeautifulSoup, *properties: str) -> str | None:
    """Extract content of the first matching meta property or name."""
    for prop in properties:
        tag = soup.find("meta", attrs={"property": prop}) or soup.find(
            "meta", attrs={"name": prop}
        )
        if tag and tag.get("content"):
            val = str(tag.get("content")).strip()
            if val:
                return val
    return None


def _extract_fallback_title(soup: BeautifulSoup) -> str | None:
    """Extract title from meta tags or title/h1 tags."""
    meta_title = _extract_meta_tag(soup, "og:title", "twitter:title", "title")
    if meta_title:
        return meta_title
    if soup.title and soup.title.string:
        title_text = soup.title.string.strip()
        if title_text:
            return title_text
    h1 = soup.find("h1")
    if h1:
        h1_text = h1.get_text().strip()
        if h1_text:
            return h1_text
    return None


def _extract_fallback_price(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Extract price text and currency hint from meta tags or microdata."""
    amount = _extract_meta_tag(
        soup,
        "og:price:amount",
        "product:price:amount",
        "price",
        "twitter:data1",
    )
    currency = _extract_meta_tag(
        soup,
        "og:price:currency",
        "product:price:currency",
        "priceCurrency",
    )
    if amount:
        return amount, currency

    # Check microdata itemprop="price"
    price_tag = soup.select_one('[itemprop="price"]')
    if price_tag:
        content = price_tag.get("content") or price_tag.get_text()
        if content and str(content).strip():
            curr_tag = soup.select_one('[itemprop="priceCurrency"]')
            curr_val = (
                (curr_tag.get("content") or curr_tag.get_text()) if curr_tag else None
            )
            return (
                str(content).strip(),
                str(curr_val).strip() if curr_val else currency,
            )

    return None, None


def _extract_fallback_image(soup: BeautifulSoup) -> str | None:
    """Extract product image URL from meta tags."""
    return _extract_meta_tag(soup, "og:image", "twitter:image")


def fetch_and_parse_custom_url(
    url: str,
    *,
    client: httpx.Client | None = None,
    user_agent: str | None = None,
    as_of: datetime | None = None,
) -> RawListing | None:
    """Fetch a single custom product page URL and parse its structured/meta data.

    Returns a `RawListing` populated with title, price, currency, and parser
    confidence metadata, or None if the URL cannot be fetched or parsed.
    """
    now = as_of or datetime.now(UTC)
    site_key, site_display_name = extract_site_info_from_url(url)

    # 1. Robots.txt check
    try:
        allowed = is_allowed(url, user_agent=user_agent or "Mozilla/5.0")
        if not allowed:
            LOGGER.warning("Robots.txt disallows fetching custom URL: %s", url)
            return None
    except Exception:
        LOGGER.debug("Robots.txt check error on custom URL %s, continuing", url)

    # 2. Rate limit on host
    try:
        parsed = urlparse(url)
        host = parsed.netloc or "custom_host"
        _CUSTOM_RATE_LIMITER.wait(host)
    except Exception:
        pass

    # 3. HTTP GET
    http_client = client or build_http_client()
    try:
        response = get_with_retry(http_client, url)
        if response.status_code != 200:
            LOGGER.warning("HTTP %s fetching custom URL %s", response.status_code, url)
            return None
    except Exception as exc:
        LOGGER.warning("Failed to fetch custom URL %s: %s", url, exc)
        return None

    # 4. Parse HTML
    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception:
        soup = BeautifulSoup(response.text, "html.parser")

    # 5. Try structured data first (JSON-LD)
    structured_products = extract_structured_products(soup, fallback_url=url)
    for p in structured_products:
        if p.title and p.price_text:
            extra: dict[str, Any] = {
                "itemCondition": p.item_condition,
                "parser_source": "json_ld",
                "parser_confidence": 1.0,
            }
            return RawListing(
                source=site_key,
                source_kind="scraper",
                title=p.title,
                url=url,
                price_text=p.price_text,
                currency_hint=p.currency,
                image_url=p.image_url,
                site_display_name=site_display_name,
                fetched_at=now,
                extra=extra,
            )

    # 6. Fallback to OpenGraph / meta tags
    fallback_title = _extract_fallback_title(soup)
    fallback_price, fallback_curr = _extract_fallback_price(soup)
    fallback_image = _extract_fallback_image(soup)

    if fallback_title and fallback_price:
        fallback_extra: dict[str, Any] = {
            "itemCondition": None,
            "parser_source": "meta_tags",
            "parser_confidence": 0.6,
        }
        return RawListing(
            source=site_key,
            source_kind="scraper",
            title=fallback_title,
            url=url,
            price_text=fallback_price,
            currency_hint=fallback_curr,
            image_url=fallback_image,
            site_display_name=site_display_name,
            fetched_at=now,
            extra=fallback_extra,
        )

    LOGGER.info("Could not extract title and price from custom URL: %s", url)
    return None
