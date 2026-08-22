"""Google Custom Search Engine provider (v2.17a remainder).

Web-result URL hints, not a shopping feed. Unconfigured or failed requests
fail closed (log + ``[]``) so other sources keep running. Needs both an
API key and a Programmable Search Engine id (``cx``).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from fetch.http_client import build_http_client
from models.listing import RawListing

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
PROVIDER_NAME = "google_cse"
# CSE allows at most 10 results per request; no pagination this slice.
_MAX_RESULTS = 10


class GoogleCseProvider:
    """Google Programmable Search, gated on API key + cx."""

    name = PROVIDER_NAME

    def __init__(self, api_key: str | None, cx: str | None) -> None:
        self._api_key = api_key.strip() if api_key else None
        self._cx = cx.strip() if cx else None

    def is_configured(self) -> bool:
        """True when both a non-empty API key and cx id are present."""
        return bool(self._api_key) and bool(self._cx)

    def search(self, query: str, *, limit: int = 10) -> list[RawListing]:
        """Fetch CSE web results for ``query``. Never raises."""
        if not self.is_configured() or not query.strip():
            return []
        capped = max(1, min(limit, _MAX_RESULTS))
        params = {
            "key": self._api_key,
            "cx": self._cx,
            "q": query.strip(),
            "num": str(capped),
        }
        try:
            with build_http_client() as client:
                response = client.get(SEARCH_URL, params=params)
        except httpx.HTTPError:
            logger.warning(
                "Google CSE transport error for query %r; returning no results",
                query,
                exc_info=True,
            )
            return []
        except Exception:
            logger.exception(
                "Google CSE unexpected error for query %r; returning no results",
                query,
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "Google CSE HTTP %s for query %r; returning no results",
                response.status_code,
                query,
            )
            return []

        try:
            payload = response.json()
        except ValueError:
            logger.warning(
                "Google CSE returned non-JSON for query %r; returning no results",
                query,
            )
            return []
        if not isinstance(payload, dict):
            logger.warning(
                "Google CSE returned a non-object payload for query %r; "
                "returning no results",
                query,
            )
            return []

        api_error = payload.get("error")
        if isinstance(api_error, dict):
            message = api_error.get("message")
            logger.warning(
                "Google CSE error for query %r: %s; returning no results",
                query,
                message,
            )
            return []

        return listings_from_cse_payload(
            payload, limit=capped, fetched_at=datetime.now().astimezone()
        )


def listings_from_cse_payload(
    payload: dict[str, Any],
    *,
    limit: int,
    fetched_at: datetime,
) -> list[RawListing]:
    """Map a Custom Search JSON body to ``RawListing`` rows.

    Rows without a usable title+URL are skipped. Missing price still
    produces a URL hint (empty ``price_text``); ``persist_snapshot``
    already drops unparseable prices.
    """
    raw_results = payload.get("items")
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
    url = _as_text(item.get("link"))
    if title is None or url is None or not url.startswith(("http://", "https://")):
        return None

    display = _as_text(item.get("displayLink")) or _host_display(url)
    price_text, currency = _price_from_pagemap(item.get("pagemap"))
    return RawListing(
        source=PROVIDER_NAME,
        source_kind="search_api",
        title=title,
        url=url,
        price_text=price_text,
        currency_hint=currency,
        image_url=_image_from_pagemap(item.get("pagemap")),
        site_display_name=display or "Google CSE",
        fetched_at=fetched_at,
        extra={
            "engine": "google_cse",
            "snippet": _as_text(item.get("snippet")),
            "display_link": display,
        },
    )


def _price_from_pagemap(pagemap: object) -> tuple[str, str | None]:
    if not isinstance(pagemap, dict):
        return "", None
    for key in ("offer", "offers"):
        block = pagemap.get(key)
        if not isinstance(block, list) or not block:
            continue
        first = block[0]
        if not isinstance(first, dict):
            continue
        price = _as_text(first.get("price")) or _as_text(first.get("lowprice"))
        currency = _as_text(first.get("pricecurrency") or first.get("priceCurrency"))
        if price is not None:
            return price, currency
    return "", None


def _image_from_pagemap(pagemap: object) -> str | None:
    if not isinstance(pagemap, dict):
        return None
    images = pagemap.get("cse_image")
    if not isinstance(images, list) or not images:
        return None
    first = images[0]
    if not isinstance(first, dict):
        return None
    src = _as_text(first.get("src"))
    if src is not None and src.startswith(("http://", "https://")):
        return src
    return None


def _host_display(url: str) -> str | None:
    host = urlparse(url).hostname
    if not host:
        return None
    return host.removeprefix("www.")


def _as_text(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    return None
