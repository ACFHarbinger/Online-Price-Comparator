"""SerpAPI Google Shopping search provider (v2.17a).

Returns retailer-shaped ``RawListing`` rows from Google Shopping. Unconfigured
or failed requests never raise — they log and return ``[]`` so discovery for
other sources keeps running. This is the candidate-source fetch; approve-
before-persist (v2.17b) is a separate slice.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from fetch.http_client import build_http_client
from models.listing import RawListing

logger = logging.getLogger(__name__)

SEARCH_URL = "https://serpapi.com/search.json"
PROVIDER_NAME = "serpapi"
_DEFAULT_GL = "es"
_DEFAULT_HL = "es"
_DEFAULT_GOOGLE_DOMAIN = "google.es"
_MAX_RESULTS = 20


class SerpApiProvider:
    """Google Shopping via SerpAPI, gated on ``SERPAPI_KEY``."""

    name = PROVIDER_NAME

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key.strip() if api_key else None

    def is_configured(self) -> bool:
        """True when a non-empty SerpAPI key is present."""
        return bool(self._api_key)

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        """Fetch Google Shopping rows for ``query``. Never raises."""
        if not self.is_configured() or not query.strip():
            return []
        capped = max(1, min(limit, _MAX_RESULTS))
        params = {
            "engine": "google_shopping",
            "q": query.strip(),
            "api_key": self._api_key,
            "gl": _DEFAULT_GL,
            "hl": _DEFAULT_HL,
            "google_domain": _DEFAULT_GOOGLE_DOMAIN,
            "num": str(capped),
        }
        try:
            with build_http_client() as client:
                response = client.get(SEARCH_URL, params=params)
        except httpx.HTTPError:
            logger.warning(
                "SerpAPI transport error for query %r; returning no results",
                query,
                exc_info=True,
            )
            return []
        except Exception:
            logger.exception(
                "SerpAPI unexpected error for query %r; returning no results", query
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "SerpAPI HTTP %s for query %r; returning no results",
                response.status_code,
                query,
            )
            return []

        try:
            payload = response.json()
        except ValueError:
            logger.warning(
                "SerpAPI returned non-JSON for query %r; returning no results", query
            )
            return []
        if not isinstance(payload, dict):
            logger.warning(
                "SerpAPI returned a non-object payload for query %r; "
                "returning no results",
                query,
            )
            return []

        api_error = payload.get("error")
        if isinstance(api_error, str) and api_error.strip():
            logger.warning(
                "SerpAPI error for query %r: %s; returning no results",
                query,
                api_error.strip(),
            )
            return []

        return listings_from_shopping_payload(
            payload, limit=capped, fetched_at=datetime.now().astimezone()
        )


def listings_from_shopping_payload(
    payload: dict[str, Any],
    *,
    limit: int,
    fetched_at: datetime,
) -> list[RawListing]:
    """Map a SerpAPI Google Shopping JSON body to ``RawListing`` rows.

    Exposed for tests so parsing can be checked without an HTTP round-trip.
    Rows without a usable title+URL are skipped; a missing price still
    produces a row (empty ``price_text``) so v2.17b can treat it as a URL
    hint. ``persist_snapshot`` already drops unparseable prices.
    """
    raw_results = payload.get("shopping_results")
    if not isinstance(raw_results, list):
        return []

    listings: list[RawListing] = []
    for item in raw_results:
        if len(listings) >= limit:
            break
        if not isinstance(item, dict):
            continue
        listing = _listing_from_item(item, fetched_at=fetched_at)
        if listing is not None:
            listings.append(listing)
    return listings


def _listing_from_item(
    item: dict[str, Any], *, fetched_at: datetime
) -> RawListing | None:
    title = _as_text(item.get("title"))
    url = _first_http_url(item.get("link"), item.get("product_link"))
    if title is None or url is None:
        return None

    merchant = _as_text(item.get("source"))
    price_text = _price_text(item)
    return RawListing(
        source=PROVIDER_NAME,
        source_kind="search_api",
        title=title,
        url=url,
        price_text=price_text,
        currency_hint=_currency_hint(item, price_text),
        image_url=_as_text(item.get("thumbnail")),
        site_display_name=merchant or "SerpAPI",
        fetched_at=fetched_at,
        extra={
            "engine": "google_shopping",
            "merchant": merchant,
            "product_id": _as_text(item.get("product_id")),
            "extracted_price": item.get("extracted_price"),
        },
    )


def _price_text(item: dict[str, Any]) -> str:
    text = _as_text(item.get("price"))
    if text is not None:
        return text
    extracted = item.get("extracted_price")
    if isinstance(extracted, int | float) and not isinstance(extracted, bool):
        return str(extracted)
    return ""


def _currency_hint(item: dict[str, Any], price_text: str) -> str | None:
    alternative = item.get("alternative_price")
    if isinstance(alternative, dict):
        alt_currency = _as_text(alternative.get("currency"))
        if alt_currency is not None:
            return alt_currency
    if "€" in price_text or "EUR" in price_text.upper():
        return "EUR"
    if "$" in price_text or "USD" in price_text.upper():
        return "USD"
    if "£" in price_text or "GBP" in price_text.upper():
        return "GBP"
    return "EUR" if price_text else None


def _first_http_url(*values: object) -> str | None:
    for value in values:
        text = _as_text(value)
        if text is not None and text.startswith(("http://", "https://")):
            return text
    return None


def _as_text(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None
