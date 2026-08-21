"""Tests for repository price stats and anomaly filtering."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Engine

from storage.repository import (
    ListingRepository,
    PriceHistoryRepository,
    ProductRepository,
)


def test_product_price_stats_and_anomalous_filtering(
    in_memory_engine: Engine,
) -> None:
    product_repo = ProductRepository(in_memory_engine)
    listing_repo = ListingRepository(in_memory_engine)
    price_repo = PriceHistoryRepository(in_memory_engine)

    prod_id = product_repo.get_or_create("rtx 4070 super")
    now = datetime(2026, 8, 21, 12, 0, 0)

    l1 = listing_repo.upsert(
        product_id=prod_id,
        site_key="amazon.es",
        site_display_name="Amazon.es",
        url="https://amazon.es/dp/1",
        image_url="https://amazon.es/img1.jpg",
        seen_at=now,
        match_status="confirmed",
        match_score=95.0,
        match_reason="model token match",
    )
    l2 = listing_repo.upsert(
        product_id=prod_id,
        site_key="pccomponentes",
        site_display_name="PcComponentes",
        url="https://pccomponentes.com/1",
        image_url="https://pccomponentes.com/img1.jpg",
        seen_at=now,
        match_status="confirmed",
        match_score=95.0,
        match_reason="model token match",
    )

    # Historical prices:
    # 40 days ago: 600 EUR (outside 30d window)
    price_repo.add(
        listing_id=l1,
        price_amount=600.0,
        currency="EUR",
        observed_at=now - timedelta(days=40),
        raw_price_text="600,00 €",
    )
    # 20 days ago: 500 EUR (inside 30d window)
    price_repo.add(
        listing_id=l1,
        price_amount=500.0,
        currency="EUR",
        observed_at=now - timedelta(days=20),
        raw_price_text="500,00 €",
    )
    # 5 days ago: 400 EUR (inside 30d window) -> True non-anomalous ATL
    price_repo.add(
        listing_id=l2,
        price_amount=400.0,
        currency="EUR",
        observed_at=now - timedelta(days=5),
        raw_price_text="400,00 €",
    )
    # 1 day ago: 100 EUR (anomalous outlier)
    price_repo.add(
        listing_id=l2,
        price_amount=100.0,
        currency="EUR",
        observed_at=now - timedelta(days=1),
        raw_price_text="100,00 €",
        is_anomalous=True,
        anomaly_reason="low-price outlier",
    )
    # Today latest: 450 EUR
    price_repo.add(
        listing_id=l1,
        price_amount=450.0,
        currency="EUR",
        observed_at=now,
        raw_price_text="450,00 €",
    )

    # 1. Default (exclude anomalous):
    # ATL across all time non-anomalous: 400.0 (from l2, 5 days ago)
    # 30d window non-anomalous: 500.0 (20d), 400.0 (5d), 450.0 (today) -> avg = 450.0
    stats_clean = price_repo.product_price_stats(prod_id, as_of=now)
    assert stats_clean.all_time_low == 400.0
    assert stats_clean.all_time_low_currency == "EUR"
    assert stats_clean.avg_30d == 450.0
    assert stats_clean.avg_30d_currency == "EUR"

    # Latest prices (exclude anomalous):
    # l1: 450.0
    # l2: 400.0 (skips anomalous 100.0)
    latest_clean = price_repo.latest_prices_by_site(prod_id)
    assert len(latest_clean) == 2
    by_site_clean = {p.site_key: p.price_amount for p in latest_clean}
    assert by_site_clean["amazon.es"] == 450.0
    assert by_site_clean["pccomponentes"] == 400.0

    # 2. Include anomalous:
    # ATL includes 100.0
    stats_anom = price_repo.product_price_stats(
        prod_id, as_of=now, include_anomalous=True
    )
    assert stats_anom.all_time_low == 100.0
    # 30d window: 500.0, 400.0, 100.0, 450.0 -> avg = 1450 / 4 = 362.5
    assert stats_anom.avg_30d == 362.5

    latest_anom = price_repo.latest_prices_by_site(prod_id, include_anomalous=True)
    by_site_anom = {p.site_key: p.price_amount for p in latest_anom}
    assert by_site_anom["amazon.es"] == 450.0
    assert by_site_anom["pccomponentes"] == 100.0

    # Test list_with_latest_price anomalous flag
    listings_clean = listing_repo.list_with_latest_price(
        prod_id, include_anomalous=False
    )
    listing_map_clean = {item.site_key: item.price_amount for item in listings_clean}
    assert listing_map_clean["pccomponentes"] == 400.0

    listings_anom = listing_repo.list_with_latest_price(prod_id, include_anomalous=True)
    listing_map_anom = {item.site_key: item.price_amount for item in listings_anom}
    assert listing_map_anom["pccomponentes"] == 100.0
