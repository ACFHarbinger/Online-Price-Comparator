"""Tests for the Google Custom Search SearchProvider."""

from __future__ import annotations

from datetime import datetime

import httpx
import respx

from search.providers.google_cse import (
    SEARCH_URL,
    GoogleCseProvider,
    listings_from_cse_payload,
)

_FETCHED_AT = datetime(2026, 8, 22, 12, 0, 0)


def _cse_payload() -> dict[str, object]:
    return {
        "items": [
            {
                "title": "AMD Ryzen 9 9950X3D",
                "link": "https://www.amazon.es/dp/B0DGHHMW2G",
                "displayLink": "www.amazon.es",
                "snippet": "Procesador AMD",
                "pagemap": {
                    "offer": [{"price": "609.82", "pricecurrency": "EUR"}],
                    "cse_image": [{"src": "https://img.example/a.jpg"}],
                },
            },
            {
                "title": "AMD Ryzen 9 9950X3D",
                "link": "https://www.pccomponentes.com/amd-ryzen-9-9950x3d",
                "displayLink": "www.pccomponentes.com",
            },
            {
                "title": "missing url should be skipped",
                "displayLink": "example.com",
            },
        ]
    }


def test_is_configured_requires_key_and_cx() -> None:
    assert GoogleCseProvider(None, None).is_configured() is False
    assert GoogleCseProvider("key", None).is_configured() is False
    assert GoogleCseProvider(None, "cx").is_configured() is False
    assert GoogleCseProvider("", "cx").is_configured() is False
    assert GoogleCseProvider("key", "  ").is_configured() is False
    assert GoogleCseProvider("key", "cx").is_configured() is True


def test_unconfigured_search_does_not_hit_the_network() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={}))
        assert GoogleCseProvider(None, "cx").search("ryzen") == []
        assert GoogleCseProvider("key", None).search("ryzen") == []
        assert router.calls.call_count == 0


def test_listings_from_cse_payload_maps_rows() -> None:
    listings = listings_from_cse_payload(
        _cse_payload(), limit=10, fetched_at=_FETCHED_AT
    )
    assert len(listings) == 2
    amazon, pcc = listings
    assert amazon.source == "google_cse"
    assert amazon.source_kind == "search_api"
    assert amazon.url == "https://www.amazon.es/dp/B0DGHHMW2G"
    assert amazon.price_text == "609.82"
    assert amazon.currency_hint == "EUR"
    assert amazon.image_url == "https://img.example/a.jpg"
    assert amazon.site_display_name == "www.amazon.es"
    assert pcc.price_text == ""
    assert pcc.currency_hint is None
    assert pcc.site_display_name == "www.pccomponentes.com"


@respx.mock
def test_search_fail_closed_on_http_error() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(403, json={"error": {}}))
    assert GoogleCseProvider("key", "cx").search("ryzen") == []


@respx.mock
def test_search_maps_live_payload() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_cse_payload()))
    listings = GoogleCseProvider("key", "cx").search("ryzen 9950x3d", limit=5)
    assert len(listings) == 2
    assert listings[0].title == "AMD Ryzen 9 9950X3D"
