"""Tests for CustomListingUrlRepository (v2.15 Tier A)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from storage.custom_urls import (
    CustomListingUrl,
    CustomListingUrlRepository,
    extract_site_info_from_url,
)
from storage.watchlist import TrackedProductRepository


def test_extract_site_info_from_url() -> None:
    key, name = extract_site_info_from_url("https://www.ldlc.com/fiche/PB00123.html")
    assert key == "ldlc_com"
    assert name == "Ldlc.com"

    key2, name2 = extract_site_info_from_url("https://alternate.de/item/456")
    assert key2 == "alternate_de"
    assert name2 == "Alternate.de"


def test_custom_listing_url_repository_lifecycle(in_memory_engine: Engine) -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("Nvidia RTX 5090")

    repo = CustomListingUrlRepository(in_memory_engine)

    # 1. Add custom URL
    entry = CustomListingUrl(
        tracked_product_id=tracked.id,
        url="https://ldlc.com/fiche/PB00123.html",
        site_key="ldlc_com",
        site_display_name="LDLC",
        added_at=now,
        status="active",
    )
    custom_id = repo.add(entry)
    assert custom_id is not None

    # Duplicate add returns existing ID or None
    dup_id = repo.add(entry)
    assert dup_id == custom_id

    # 2. Get by ID
    fetched = repo.get(custom_id)
    assert fetched is not None
    assert fetched.url == "https://ldlc.com/fiche/PB00123.html"
    assert fetched.site_key == "ldlc_com"
    assert fetched.status == "active"

    # 3. Get by URL
    by_url = repo.get_by_url(tracked.id, "https://ldlc.com/fiche/PB00123.html")
    assert by_url is not None
    assert by_url.id == custom_id

    # 4. List for product
    items = repo.list_for_product(tracked.id)
    assert len(items) == 1
    assert items[0].id == custom_id

    # 5. List active
    active = repo.list_all_active()
    assert len(active) == 1
    assert active[0].id == custom_id

    # 6. Update status
    check_time = now + timedelta(hours=1)
    repo.update_status(
        custom_id,
        last_checked_at=check_time,
        parser_confidence=0.95,
        status="active",
        last_error=None,
    )
    updated = repo.get(custom_id)
    assert updated is not None
    assert updated.parser_confidence == 0.95
    assert updated.last_checked_at == check_time.replace(tzinfo=None)

    # 7. Remove
    assert repo.remove(custom_id) is True
    assert repo.get(custom_id) is None
    assert len(repo.list_for_product(tracked.id)) == 0
