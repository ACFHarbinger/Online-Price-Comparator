"""eBay Browse API search provider (Issue #40).

Fetches marketplace listings from eBay (default: eBay.de / EBAY_DE) using OAuth2
client-credentials authentication against the official eBay REST Browse API.
Unconfigured or failed requests fail closed (log warning and return ``[]``) so
discovery across other scrapers and search providers is never blocked.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from fetch.http_client import build_http_client
from models.listing import RawListing

logger = logging.getLogger(__name__)

PROVIDER_NAME = "ebay_de"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
DEFAULT_MARKETPLACE_ID = "EBAY_DE"
_MAX_RESULTS = 50

EU_COUNTRIES = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
    }
)


def resolve_import_regime(country_code: str | None) -> str:
    """Tag listing origin regime based on seller/item location."""
    if not country_code:
        return "unknown"
    code = country_code.strip().upper()
    if code in ("GB", "UK"):
        return "uk"
    if code in EU_COUNTRIES:
        return "eu_domestic"
    return "non_eu"


class EbayBrowseProvider:
    """eBay Browse API SearchProvider with OAuth2 client-credentials flow."""

    name = PROVIDER_NAME

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        marketplace_id: str = DEFAULT_MARKETPLACE_ID,
    ) -> None:
        self._client_id = client_id.strip() if client_id else None
        self._client_secret = client_secret.strip() if client_secret else None
        self._marketplace_id = (
            marketplace_id.strip() if marketplace_id else DEFAULT_MARKETPLACE_ID
        )
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    def is_configured(self) -> bool:
        """True when both OAuth2 client ID and secret are set."""
        return bool(self._client_id and self._client_secret)

    def _get_access_token(self) -> str | None:
        """Obtain a valid OAuth2 Bearer token or return cached if still valid."""
        now = datetime.now()
        if (
            self._access_token is not None
            and self._token_expires_at is not None
            and now < (self._token_expires_at - timedelta(seconds=60))
        ):
            return self._access_token

        if not self.is_configured():
            return None

        assert self._client_id is not None
        assert self._client_secret is not None

        creds = f"{self._client_id}:{self._client_secret}"
        encoded_creds = base64.b64encode(creds.encode("utf-8")).decode("ascii")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_creds}",
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        try:
            with build_http_client() as client:
                response = client.post(TOKEN_URL, headers=headers, data=data)
        except httpx.HTTPError:
            logger.warning(
                "eBay OAuth2 token request transport error",
                exc_info=True,
            )
            return None
        except Exception:
            logger.exception("Unexpected error requesting eBay OAuth2 token")
            return None

        if response.status_code != 200:
            logger.warning(
                "eBay OAuth2 token request failed with HTTP %s: %s",
                response.status_code,
                response.text[:200],
            )
            return None

        try:
            payload = response.json()
        except Exception:
            logger.warning("Failed to decode eBay OAuth2 token JSON response")
            return None

        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            logger.warning("eBay OAuth2 token missing from response payload")
            return None

        expires_in = payload.get("expires_in", 7200)
        expires_seconds = (
            int(expires_in) if isinstance(expires_in, int | float) else 7200
        )
        self._access_token = token
        self._token_expires_at = now + timedelta(seconds=expires_seconds)
        return self._access_token

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        """Fetch eBay listings for ``query``. Never raises."""
        if not self.is_configured() or not query.strip():
            return []

        token = self._get_access_token()
        if not token:
            return []

        capped = max(1, min(limit, _MAX_RESULTS))
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self._marketplace_id,
            "Accept": "application/json",
        }
        params = {
            "q": query.strip(),
            "limit": str(capped),
        }

        try:
            with build_http_client() as client:
                response = client.get(SEARCH_URL, headers=headers, params=params)
        except httpx.HTTPError:
            logger.warning(
                "eBay Browse API transport error for query %r; returning no results",
                query,
                exc_info=True,
            )
            return []
        except Exception:
            logger.exception(
                "eBay Browse API unexpected error for query %r; returning no results",
                query,
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "eBay Browse API HTTP %s for query %r; returning no results",
                response.status_code,
                query,
            )
            return []

        try:
            payload = response.json()
        except Exception:
            logger.warning(
                "Failed to parse eBay Browse API JSON response for query %r",
                query,
            )
            return []

        if not isinstance(payload, dict):
            return []

        fetched_at = datetime.now()
        return parse_browse_payload(payload, limit=capped, fetched_at=fetched_at)


def parse_browse_payload(
    payload: dict[str, Any], *, limit: int, fetched_at: datetime
) -> list[RawListing]:
    """Parse eBay Browse API ``item_summary/search`` payload into RawListing items."""
    raw_items = payload.get("itemSummaries")
    if not isinstance(raw_items, list):
        return []

    listings: list[RawListing] = []
    for item in raw_items:
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
    url = _as_text(item.get("itemWebUrl"))
    if title is None or url is None:
        return None

    price_obj = item.get("price")
    price_text = ""
    currency_hint = None
    if isinstance(price_obj, dict):
        val = _as_text(price_obj.get("value"))
        curr = _as_text(price_obj.get("currency"))
        if val is not None:
            price_text = val
            currency_hint = curr

    image_obj = item.get("image")
    image_url = None
    if isinstance(image_obj, dict):
        image_url = _as_text(image_obj.get("imageUrl"))
    if image_url is None:
        thumbnails = item.get("thumbnailImages")
        if (
            isinstance(thumbnails, list)
            and thumbnails
            and isinstance(thumbnails[0], dict)
        ):
            image_url = _as_text(thumbnails[0].get("imageUrl"))

    location = item.get("itemLocation")
    country = None
    if isinstance(location, dict):
        country = _as_text(location.get("country"))
    import_regime = resolve_import_regime(country)

    condition = _as_text(item.get("condition"))
    condition_id = _as_text(item.get("conditionId"))
    item_id = _as_text(item.get("itemId"))

    return RawListing(
        source=PROVIDER_NAME,
        source_kind="search_api",
        title=title,
        url=url,
        price_text=price_text,
        currency_hint=currency_hint or "EUR",
        image_url=image_url,
        site_display_name="eBay.de",
        fetched_at=fetched_at,
        extra={
            "item_id": item_id,
            "condition": condition,
            "condition_id": condition_id,
            "country": country,
            "import_regime": import_regime,
        },
    )


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None
