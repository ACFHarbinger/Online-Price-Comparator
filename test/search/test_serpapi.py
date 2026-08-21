"""Tests for the SerpAPI Google Shopping SearchProvider."""

from __future__ import annotations

from datetime import datetime

import httpx
import respx

from search.providers.serpapi import (
    SEARCH_URL,
    SerpApiProvider,
    listings_from_shopping_payload,
)

_FETCHED_AT = datetime(2026, 8, 21, 12, 0, 0)


def _shopping_payload() -> dict[str, object]:
    return {
        "shopping_results": [
            {
                "title": "AMD Ryzen 9 9950X3D",
                "link": "https://www.amazon.es/dp/B0DGHHMW2G",
                "product_link": "https://www.google.com/shopping/product/1",
                "source": "Amazon.es",
                "price": "609,82 €",
                "extracted_price": 609.82,
                "thumbnail": "https://img.example/a.jpg",
                "product_id": "111",
            },
            {
                "title": "AMD Ryzen 9 9950X3D tray",
                "product_link": "https://www.pccomponentes.com/amd-ryzen-9-9950x3d",
                "source": "PcComponentes",
                "price": "€589.00",
                "extracted_price": 589.0,
            },
            {
                "title": "missing url should be skipped",
                "source": "Unknown",
                "price": "10 €",
            },
        ]
    }


def test_is_configured_requires_non_empty_key() -> None:
    assert SerpApiProvider(None).is_configured() is False
    assert SerpApiProvider("").is_configured() is False
    assert SerpApiProvider("   ").is_configured() is False
    assert SerpApiProvider("secret").is_configured() is True


def test_unconfigured_search_does_not_hit_the_network() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={}))
        assert SerpApiProvider(None).search("ryzen 9950x3d") == []
        assert router.calls.call_count == 0


def test_listings_from_shopping_payload_maps_merchant_rows() -> None:
    listings = listings_from_shopping_payload(
        _shopping_payload(), limit=10, fetched_at=_FETCHED_AT
    )
    assert len(listings) == 2
    amazon, pcc = listings
    assert amazon.source == "serpapi"
    assert amazon.source_kind == "search_api"
    assert amazon.title == "AMD Ryzen 9 9950X3D"
    assert amazon.url == "https://www.amazon.es/dp/B0DGHHMW2G"
    assert amazon.price_text == "609,82 €"
    assert amazon.currency_hint == "EUR"
    assert amazon.site_display_name == "Amazon.es"
    assert amazon.image_url == "https://img.example/a.jpg"
    assert amazon.extra["merchant"] == "Amazon.es"
    assert pcc.url == "https://www.pccomponentes.com/amd-ryzen-9-9950x3d"
    assert pcc.site_display_name == "PcComponentes"


def test_listings_from_shopping_payload_respects_limit() -> None:
    listings = listings_from_shopping_payload(
        _shopping_payload(), limit=1, fetched_at=_FETCHED_AT
    )
    assert len(listings) == 1
    assert listings[0].site_display_name == "Amazon.es"


def test_listings_from_shopping_payload_empty_or_malformed() -> None:
    assert listings_from_shopping_payload({}, limit=10, fetched_at=_FETCHED_AT) == []
    assert (
        listings_from_shopping_payload(
            {"shopping_results": "nope"}, limit=10, fetched_at=_FETCHED_AT
        )
        == []
    )


@respx.mock
def test_configured_search_returns_mapped_listings() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=_shopping_payload())
    )
    listings = SerpApiProvider("test-key").search("ryzen 9950x3d", limit=5)
    assert len(listings) == 2
    assert listings[0].url == "https://www.amazon.es/dp/B0DGHHMW2G"


@respx.mock
def test_configured_search_zero_results() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"shopping_results": []})
    )
    assert SerpApiProvider("test-key").search("no such sku") == []


@respx.mock
def test_configured_search_api_error_returns_empty() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"error": "Invalid API key."})
    )
    assert SerpApiProvider("test-key").search("ryzen") == []


@respx.mock
def test_configured_search_http_error_returns_empty() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(500, text="nope"))
    assert SerpApiProvider("test-key").search("ryzen") == []


@respx.mock
def test_configured_search_transport_error_returns_empty() -> None:
    respx.get(SEARCH_URL).mock(side_effect=httpx.ConnectError("boom"))
    assert SerpApiProvider("test-key").search("ryzen") == []


@respx.mock
def test_configured_search_non_json_returns_empty() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, text="<html>nope</html>")
    )
    assert SerpApiProvider("test-key").search("ryzen") == []


def test_search_sends_google_shopping_params() -> None:
    with respx.mock(assert_all_called=True) as router:
        route = router.get(SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"shopping_results": []})
        )
        SerpApiProvider("test-key").search("9950X3D", limit=3)
        request = route.calls.last.request
        assert "engine=google_shopping" in str(request.url)
        assert "gl=es" in str(request.url)
        assert "q=9950X3D" in str(request.url)
        assert "api_key=test-key" in str(request.url)
