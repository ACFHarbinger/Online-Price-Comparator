"""Tests for custom listing URL tracking and processing pipeline (v2.15 Tier A)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import respx
from sqlalchemy import Engine, select

from pipeline.custom_url import (
    refresh_custom_urls_for_product,
    track_and_process_custom_url,
)
from storage.custom_urls import CustomListingUrlRepository
from storage.schema import listings, price_history
from storage.watchlist import TrackedProductRepository

HTML_RYZEN = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "AMD Ryzen 7 7800X3D Processor",
        "image": "https://ldlc.com/ryzen.jpg",
        "offers": {
            "@type": "Offer",
            "priceCurrency": "EUR",
            "price": "389.00"
        }
    }
    </script>
</head>
<body><h1>AMD Ryzen 7 7800X3D</h1></body>
</html>
"""

HTML_UNMATCHED = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": "Arctic Liquid Freezer III 360",
        "offers": {
            "@type": "Offer",
            "priceCurrency": "EUR",
            "price": "89.00"
        }
    }
    </script>
</head>
<body><h1>Arctic Liquid Freezer III 360</h1></body>
</html>
"""


@respx.mock
def test_track_and_process_custom_url_success(in_memory_engine: Engine) -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("AMD Ryzen 7 7800X3D")

    url = "https://ldlc.com/item/ryzen-7800x3d"
    respx.get(url).mock(return_value=httpx.Response(200, text=HTML_RYZEN))

    success, msg = track_and_process_custom_url(
        tracked.id,
        url,
        in_memory_engine,
        as_of=now,
    )

    assert success is True
    assert "Tracked custom listing" in msg

    # Verify custom_listing_urls table record
    custom_repo = CustomListingUrlRepository(in_memory_engine)
    record = custom_repo.get_by_url(tracked.id, url)
    assert record is not None
    assert record.status == "active"
    assert record.parser_confidence == 1.0

    # Verify listing promoted to persistent listings
    with in_memory_engine.connect() as conn:
        listing_rows = conn.execute(
            select(listings).where(listings.c.product_id == tracked.product_id)
        ).all()
        assert len(listing_rows) == 1
        assert listing_rows[0].url == url
        assert listing_rows[0].site_key == "ldlc_com"

        # Verify price_history recorded
        prices = conn.execute(select(price_history)).all()
        assert len(prices) == 1
        assert prices[0].price_amount == 389.00
        assert prices[0].price_eur_equivalent == 389.00


@respx.mock
def test_track_and_process_custom_url_unmatched(in_memory_engine: Engine) -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("AMD Ryzen 7 7800X3D")

    url = "https://ldlc.com/item/cooler"
    respx.get(url).mock(return_value=httpx.Response(200, text=HTML_UNMATCHED))

    success, msg = track_and_process_custom_url(
        tracked.id,
        url,
        in_memory_engine,
        as_of=now,
    )

    assert success is False
    assert "did not match tracked product" in msg

    # Custom url record status is unmatched
    custom_repo = CustomListingUrlRepository(in_memory_engine)
    record = custom_repo.get_by_url(tracked.id, url)
    assert record is not None
    assert record.status == "unmatched"


def test_track_and_process_custom_url_invalid_url(in_memory_engine: Engine) -> None:
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("AMD Ryzen 7 7800X3D")

    success, msg = track_and_process_custom_url(
        tracked.id,
        "not-a-valid-url",
        in_memory_engine,
    )
    assert success is False
    assert "Invalid URL" in msg


@respx.mock
def test_refresh_custom_urls_for_product(in_memory_engine: Engine) -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("AMD Ryzen 7 7800X3D")

    url = "https://ldlc.com/item/ryzen-7800x3d"
    respx.get(url).mock(return_value=httpx.Response(200, text=HTML_RYZEN))

    # Add URL
    custom_repo = CustomListingUrlRepository(in_memory_engine)
    from storage.custom_urls import CustomListingUrl

    custom_repo.add(
        CustomListingUrl(
            tracked_product_id=tracked.id,
            url=url,
            site_key="ldlc_com",
            site_display_name="LDLC",
            added_at=now,
            status="active",
        )
    )

    results = refresh_custom_urls_for_product(tracked.id, in_memory_engine, as_of=now)
    assert len(results) == 1
    assert results[0][0] == url
    assert results[0][1] is True
