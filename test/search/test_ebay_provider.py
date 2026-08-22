"""Tests for the eBay.de Browse API SearchProvider (Issue #40)."""

from __future__ import annotations

from datetime import datetime

import httpx
import respx

from search.providers.ebay import (
    SEARCH_URL,
    TOKEN_URL,
    EbayBrowseProvider,
    parse_browse_payload,
    resolve_import_regime,
)

_FETCHED_AT = datetime(2026, 8, 22, 12, 0, 0)


def _token_payload() -> dict[str, object]:
    return {
        "access_token": "mock-ebay-access-token-xyz",
        "expires_in": 7200,
        "token_type": "Application Access Token",
    }


def _browse_payload() -> dict[str, object]:
    return {
        "itemSummaries": [
            {
                "itemId": "v1|123456789|0",
                "title": "AMD Ryzen 7 7800X3D CPU Box",
                "itemWebUrl": "https://www.ebay.de/itm/123456789",
                "price": {"value": "369.90", "currency": "EUR"},
                "condition": "New",
                "conditionId": "1000",
                "itemLocation": {"country": "DE", "postalCode": "10115"},
                "image": {"imageUrl": "https://i.ebayimg.com/images/g/abc/s-l500.jpg"},
            },
            {
                "itemId": "v1|987654321|0",
                "title": "AMD Ryzen 7 7800X3D Used",
                "itemWebUrl": "https://www.ebay.de/itm/987654321",
                "price": {"value": "310.00", "currency": "EUR"},
                "condition": "Used",
                "conditionId": "3000",
                "itemLocation": {"country": "GB", "postalCode": "SW1A"},
                "thumbnailImages": [
                    {"imageUrl": "https://i.ebayimg.com/images/g/def/s-l225.jpg"}
                ],
            },
            {
                "itemId": "v1|555555555|0",
                "title": "AMD Ryzen 7 7800X3D US Import",
                "itemWebUrl": "https://www.ebay.de/itm/555555555",
                "price": {"value": "299.00", "currency": "EUR"},
                "condition": "Open box",
                "itemLocation": {"country": "US"},
            },
            {
                "title": "Invalid item without url",
                "price": {"value": "10.00", "currency": "EUR"},
            },
        ]
    }


def test_is_configured() -> None:
    assert EbayBrowseProvider(None, None).is_configured() is False
    assert EbayBrowseProvider("id", None).is_configured() is False
    assert EbayBrowseProvider(None, "secret").is_configured() is False
    assert EbayBrowseProvider("", "secret").is_configured() is False
    assert EbayBrowseProvider("id", "").is_configured() is False
    assert EbayBrowseProvider("id", "secret").is_configured() is True


def test_unconfigured_search_does_not_hit_network() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={}))
        router.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={}))
        assert EbayBrowseProvider(None, None).search("ryzen 7800x3d") == []
        assert router.calls.call_count == 0


def test_resolve_import_regime() -> None:
    assert resolve_import_regime("DE") == "eu_domestic"
    assert resolve_import_regime("pt") == "eu_domestic"
    assert resolve_import_regime("FR") == "eu_domestic"
    assert resolve_import_regime("ES") == "eu_domestic"
    assert resolve_import_regime("GB") == "uk"
    assert resolve_import_regime("UK") == "uk"
    assert resolve_import_regime("US") == "non_eu"
    assert resolve_import_regime("CN") == "non_eu"
    assert resolve_import_regime(None) == "unknown"
    assert resolve_import_regime("") == "unknown"


def test_parse_browse_payload() -> None:
    listings = parse_browse_payload(_browse_payload(), limit=10, fetched_at=_FETCHED_AT)
    assert len(listings) == 3

    item1, item2, item3 = listings
    assert item1.source == "ebay_de"
    assert item1.source_kind == "search_api"
    assert item1.title == "AMD Ryzen 7 7800X3D CPU Box"
    assert item1.url == "https://www.ebay.de/itm/123456789"
    assert item1.price_text == "369.90"
    assert item1.currency_hint == "EUR"
    assert item1.site_display_name == "eBay.de"
    assert item1.image_url == "https://i.ebayimg.com/images/g/abc/s-l500.jpg"
    assert item1.extra["condition"] == "New"
    assert item1.extra["import_regime"] == "eu_domestic"
    assert item1.extra["country"] == "DE"

    assert item2.extra["import_regime"] == "uk"
    assert item2.image_url == "https://i.ebayimg.com/images/g/def/s-l225.jpg"

    assert item3.extra["import_regime"] == "non_eu"


def test_parse_browse_payload_respects_limit() -> None:
    listings = parse_browse_payload(_browse_payload(), limit=1, fetched_at=_FETCHED_AT)
    assert len(listings) == 1
    assert listings[0].title == "AMD Ryzen 7 7800X3D CPU Box"


@respx.mock
def test_configured_search_happy_path() -> None:
    token_route = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json=_token_payload())
    )
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_browse_payload()))

    provider = EbayBrowseProvider("mock_client_id", "mock_client_secret")
    listings = provider.search("ryzen 7800x3d", limit=5)
    assert len(listings) == 3
    assert listings[0].url == "https://www.ebay.de/itm/123456789"

    # Second search should reuse cached token (only 1 token call)
    listings2 = provider.search("ryzen 7800x3d", limit=5)
    assert len(listings2) == 3
    assert token_route.call_count == 1


@respx.mock
def test_configured_search_token_failure_returns_empty() -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(401, text="Unauthorized"))
    provider = EbayBrowseProvider("bad_id", "bad_secret")
    assert provider.search("ryzen") == []


@respx.mock
def test_configured_search_search_failure_returns_empty() -> None:
    respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=_token_payload()))
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    provider = EbayBrowseProvider("mock_id", "mock_secret")
    assert provider.search("ryzen") == []


@respx.mock
def test_configured_search_transport_error_returns_empty() -> None:
    respx.post(TOKEN_URL).mock(side_effect=httpx.ConnectError("Connection refused"))
    provider = EbayBrowseProvider("mock_id", "mock_secret")
    assert provider.search("ryzen") == []
