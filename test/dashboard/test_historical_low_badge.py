"""Unit tests for dashboard historical-low badges (v2.14)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import Engine

from alerting.observations import ListingHistory, ListingObservation
from dashboard.callbacks import (
    _build_hero_metrics,
    _build_percentile_badge,
    _build_tiered_low_badge,
    _product_view,
    _retailer_table,
)
from storage.repository import (
    ListingRepository,
    ListingSummary,
    PriceHistoryRepository,
    ProductPriceStats,
    ProductRepository,
)


def test_build_tiered_low_badge() -> None:
    badge_atl = cast(Any, _build_tiered_low_badge("all-time"))
    assert badge_atl.children == "All-Time Low"
    assert "badge-tiered-low" in badge_atl.className

    badge_30d = cast(Any, _build_tiered_low_badge("30d"))
    assert badge_30d.children == "30-Day Low"
    assert "badge-tiered-low" in badge_30d.className

    badge_90d = cast(Any, _build_tiered_low_badge("90d"))
    assert badge_90d.children == "90-Day Low"
    assert "badge-tiered-low" in badge_90d.className

    badge_180d = cast(Any, _build_tiered_low_badge("180d"))
    assert badge_180d.children == "180-Day Low"
    assert "badge-tiered-low" in badge_180d.className

    badge_365d = cast(Any, _build_tiered_low_badge("365d"))
    assert badge_365d.children == "365-Day Low"
    assert "badge-tiered-low" in badge_365d.className


def test_build_percentile_badge() -> None:
    badge = cast(Any, _build_percentile_badge(5.0))
    assert badge.children == "Top 5% Low"
    assert "badge-percentile-low" in badge.className


def test_build_hero_metrics_with_tiered_low() -> None:
    stats = ProductPriceStats(
        all_time_low=450.0,
        all_time_low_currency="EUR",
        avg_30d=500.0,
        avg_30d_currency="EUR",
    )

    # 1. Tiered low present
    badges = _build_hero_metrics(
        stats=stats,
        current_lowest=440.0,
        tiered_low="30d",
        percentile_low=True,
    )
    badge_texts = [b.children for b in badges if isinstance(b.children, str)]
    assert "30-Day Low" in badge_texts
    assert "Top 5% Low" in badge_texts

    # 2. No tiered low, falls back to ATL
    badges_no_tier = _build_hero_metrics(
        stats=stats,
        current_lowest=490.0,
        tiered_low=None,
        percentile_low=False,
    )
    no_tier_texts = [b.children for b in badges_no_tier if isinstance(b.children, str)]
    assert "ATL: EUR 450.00" in no_tier_texts


def test_retailer_table_historical_low_badges() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    listings = [
        ListingSummary(
            site_key="amazon_es",
            site_display_name="Amazon.es",
            url="https://amazon.es/dp/123",
            image_url=None,
            price_amount=380.0,
            currency="EUR",
            observed_at=now,
        )
    ]

    histories = [
        ListingHistory(
            listing_id=1,
            site_key="amazon_es",
            site_display_name="Amazon.es",
            url="https://amazon.es/dp/123",
            observations=[
                ListingObservation(
                    listing_id=1,
                    site_key="amazon_es",
                    site_display_name="Amazon.es",
                    url="https://amazon.es/dp/123",
                    observed_at=now - timedelta(days=10),
                    eur_amount=420.0,
                    condition="new",
                ),
                ListingObservation(
                    listing_id=1,
                    site_key="amazon_es",
                    site_display_name="Amazon.es",
                    url="https://amazon.es/dp/123",
                    observed_at=now,
                    eur_amount=380.0,
                    condition="new",
                ),
            ],
        )
    ]

    table = _retailer_table(
        listings,
        avg_30d=400.0,
        as_of=now,
        listing_histories=histories,
    )
    table_any = cast(Any, table)
    tbody = table_any.children[1]
    row = tbody.children[0]
    store_cell = row.children[0]
    store_span = store_cell.children
    # Should have store name + badge
    assert len(store_span.children) == 2
    assert store_span.children[0] == "Amazon.es"
    badge = store_span.children[1]
    assert badge.children == "ATL"
    assert "badge-tiered-row" in badge.className


def test_product_view_tiered_low_integration(in_memory_engine: Engine) -> None:
    prod_repo = ProductRepository(in_memory_engine)
    listing_repo = ListingRepository(in_memory_engine)
    price_repo = PriceHistoryRepository(in_memory_engine)

    prod_id = prod_repo.get_or_create("Ryzen 7 7800X3D")
    list_id = listing_repo.upsert(
        product_id=prod_id,
        site_key="pccomponentes",
        site_display_name="PcComponentes",
        url="https://pccomponentes.com/item",
        image_url=None,
        seen_at=datetime.now(),
        match_status="confirmed",
        match_score=1.0,
        match_reason="Test confirmed",
        condition="new",
    )

    now = datetime.now()
    price_repo.add(
        listing_id=list_id,
        price_amount=420.0,
        currency="EUR",
        observed_at=now - timedelta(days=5),
        raw_price_text="420.00",
        price_eur_equivalent=420.0,
        condition="new",
    )
    price_repo.add(
        listing_id=list_id,
        price_amount=379.0,
        currency="EUR",
        observed_at=now,
        raw_price_text="379.00",
        price_eur_equivalent=379.0,
        condition="new",
    )

    (
        title,
        _img,
        _lowest_str,
        hero_badges,
        _bar,
        _line,
        _table,
        _fcast_chart,
        _fcast_meta,
        _scorecard_panel,
    ) = _product_view(
        prod_id,
        False,
        prod_repo,
        listing_repo,
        price_repo,
    )

    assert title == "Ryzen 7 7800X3D"
    badge_texts = [b.children for b in hero_badges if isinstance(b.children, str)]
    assert "All-Time Low" in badge_texts
