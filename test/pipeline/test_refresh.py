"""Tests for watchlist refresh and passive monitoring runner (v2.2)."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

import pytest
from sqlalchemy import Engine

from config.settings import Settings
from models.listing import RawListing
from pipeline.refresh import (
    is_due_for_refresh,
    refresh_tracked_product,
    refresh_watchlist,
    run_monitoring_loop,
)
from storage.repository import ListingRepository
from storage.watchlist import TrackedProduct, TrackedProductRepository


def _make_tracked(
    *,
    id: int = 1,
    product_id: int = 1,
    query_text: str = "AMD Ryzen 9 9950X3D",
    enabled: bool = True,
    refresh_interval_hours: int | None = None,
    last_checked_at: datetime | None = None,
) -> TrackedProduct:
    return TrackedProduct(
        id=id,
        product_id=product_id,
        query_text=query_text,
        canonical_name=None,
        enabled=enabled,
        refresh_interval_hours=refresh_interval_hours,
        target_price=None,
        target_currency=None,
        search_scope_tier="local",
        historical_low_alert_mode="tiered",
        rarity_percentile=None,
        rarity_window_days=None,
        rarity_min_observations=None,
        created_at=datetime(2026, 8, 21, 10, 0, 0),
        last_checked_at=last_checked_at,
    )


def test_is_due_for_refresh() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)

    # 1. Never checked -> always due
    never_checked = _make_tracked(last_checked_at=None)
    assert is_due_for_refresh(never_checked, as_of=now) is True

    # 2. Checked 6 hours ago with 12h default -> not due
    recently_checked = _make_tracked(last_checked_at=now - timedelta(hours=6))
    assert (
        is_due_for_refresh(recently_checked, default_interval_hours=12, as_of=now)
        is False
    )

    # 3. Checked 13 hours ago with 12h default -> due
    past_due = _make_tracked(last_checked_at=now - timedelta(hours=13))
    assert is_due_for_refresh(past_due, default_interval_hours=12, as_of=now) is True

    # 4. Checked 6 hours ago with per-product 4h override -> due
    custom_due = _make_tracked(
        refresh_interval_hours=4,
        last_checked_at=now - timedelta(hours=6),
    )
    assert is_due_for_refresh(custom_due, default_interval_hours=12, as_of=now) is True

    # 5. Checked 6 hours ago with per-product 24h override -> not due
    custom_not_due = _make_tracked(
        refresh_interval_hours=24,
        last_checked_at=now - timedelta(hours=6),
    )
    assert (
        is_due_for_refresh(custom_not_due, default_interval_hours=12, as_of=now)
        is False
    )


def test_refresh_tracked_product(
    in_memory_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracked_repo = TrackedProductRepository(in_memory_engine)
    tracked = tracked_repo.get_or_create("AMD Ryzen 9 9950X3D")
    assert tracked.last_checked_at is None

    fake_listing = RawListing(
        source="amazon.es",
        source_kind="scraper",
        title="AMD Ryzen 9 9950X3D Processor",
        price_text="699,00 €",
        currency_hint="EUR",
        image_url=None,
        url="https://amazon.es/dp/B0EXAMPLE",
        site_display_name="Amazon.es",
        fetched_at=datetime.now(),
    )

    monkeypatch.setattr(
        "pipeline.refresh.run_discovery",
        lambda query, settings, limit=20, engine=None, tracked_product_id=None: [
            fake_listing
        ],
    )

    settings = Settings(enabled_scrapers="amazon.es")
    count = refresh_tracked_product(tracked, settings, in_memory_engine)
    assert count == 1

    # Check last_checked_at was updated
    refreshed_tracked = tracked_repo.get(tracked.id)
    assert refreshed_tracked is not None
    assert refreshed_tracked.last_checked_at is not None

    # Check listing was persisted
    listings = ListingRepository(in_memory_engine).list_with_latest_price(
        tracked.product_id
    )
    assert len(listings) == 1
    assert listings[0].price_amount == 699.0


def test_refresh_watchlist_filters_due_and_disabled(
    in_memory_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)
    tracked_repo = TrackedProductRepository(in_memory_engine)

    p1 = tracked_repo.get_or_create("Product 1 Due")
    p2 = tracked_repo.get_or_create("Product 2 Recent")
    tracked_repo.touch_last_checked(p2.id, when=now - timedelta(hours=2))
    p3 = tracked_repo.get_or_create("Product 3 Disabled")
    tracked_repo.set_enabled(p3.id, False)

    fake_listing = RawListing(
        source="amazon.es",
        source_kind="scraper",
        title="Product Listing",
        price_text="100,00 €",
        currency_hint="EUR",
        image_url=None,
        url="https://amazon.es/dp/1",
        site_display_name="Amazon.es",
        fetched_at=datetime.now(),
    )

    monkeypatch.setattr(
        "pipeline.refresh.run_discovery",
        lambda query, settings, limit=20, engine=None, tracked_product_id=None: [
            fake_listing
        ],
    )

    settings = Settings(refresh_interval_hours=12)

    # 1. Normal refresh -> only p1 is due
    res = refresh_watchlist(in_memory_engine, settings, force=False, as_of=now)
    assert p1.id in res
    assert p2.id not in res
    assert p3.id not in res

    # 2. Forced refresh -> refreshes all enabled (p1 and p2, but not disabled p3)
    res_forced = refresh_watchlist(in_memory_engine, settings, force=True, as_of=now)
    assert p1.id in res_forced
    assert p2.id in res_forced
    assert p3.id not in res_forced


def test_run_monitoring_loop(
    in_memory_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fake_refresh(
        engine: Engine, settings: Settings | None = None, **kwargs: object
    ) -> dict[int, int]:
        nonlocal calls
        calls += 1
        return {}

    monkeypatch.setattr("pipeline.refresh.refresh_watchlist", fake_refresh)

    # Test max_iterations termination
    settings = Settings()
    iterations = run_monitoring_loop(
        in_memory_engine, settings, check_interval_seconds=0.01, max_iterations=3
    )
    assert iterations == 3
    assert calls == 3

    # Test stop_event termination
    stop_event = threading.Event()
    stop_event.set()
    iterations_stopped = run_monitoring_loop(
        in_memory_engine, settings, check_interval_seconds=10.0, stop_event=stop_event
    )
    assert iterations_stopped == 0
