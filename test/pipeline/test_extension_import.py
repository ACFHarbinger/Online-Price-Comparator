"""Tests for the v2.20 extension-file import pipeline."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine

from pipeline.extension_import import (
    ExtensionImportResult,
    import_extension_file,
    read_extension_records,
)
from storage.custom_urls import CustomListingUrl, CustomListingUrlRepository
from storage.repository import ListingRepository
from storage.watchlist import TrackedProductRepository


def _write_jsonl(path: Path, records: list[object]) -> Path:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    return path


def _seed_tracked_custom_url(
    engine: Engine, query_text: str, url: str
) -> tuple[int, int]:
    """Create a tracked product + a custom_listing_url for it."""
    tracked = TrackedProductRepository(engine).get_or_create(query_text)
    CustomListingUrlRepository(engine).add(
        CustomListingUrl(
            tracked_product_id=tracked.id,
            url=url,
            site_key="leboncoin",
            site_display_name="Leboncoin",
            added_at=datetime.now(UTC),
            status="active",
        )
    )
    return tracked.id, tracked.product_id


def test_read_extension_records_skips_invalid(tmp_path: Path) -> None:
    target = _write_jsonl(
        tmp_path / "opc.jsonl",
        [
            {"url": "u1", "title": "T", "price_text": "1,00 €"},
            "not json",
            {"broken": "no url"},
            {"url": "u2", "title": "T2", "price_text": "2,00 €"},
        ],
    )
    records = read_extension_records(target)
    assert len(records) == 3  # the bare "not json" line is skipped


def test_import_extension_file_persists_snapshot(
    in_memory_engine: Engine, tmp_path: Path
) -> None:
    url = "https://www.leboncoin.fr/ad/123456"
    query_text = "AMD Ryzen 9 9950X3D"
    _, product_id = _seed_tracked_custom_url(in_memory_engine, query_text, url)

    target = _write_jsonl(
        tmp_path / "opc.jsonl",
        [
            {
                "site_key": "leboncoin",
                "site_display_name": "Leboncoin",
                "url": url,
                "title": "AMD Ryzen 9 9950X3D 9950X3D 16-Core Processor",
                "price_text": "599,99 €",
                "currency_hint": "EUR",
                "observed_at": "2026-08-21T12:00:00+02:00",
            }
        ],
    )

    result = import_extension_file(target, in_memory_engine)

    assert isinstance(result, ExtensionImportResult)
    assert result.lines_read == 1
    assert result.records_imported == 1
    assert result.products_handled == [query_text]
    assert result.skipped == []

    listings = ListingRepository(in_memory_engine).list_with_latest_price(product_id)
    assert len(listings) == 1
    assert listings[0].price_amount == 599.99


def test_import_extension_file_skips_unattributed_url(
    in_memory_engine: Engine, tmp_path: Path
) -> None:
    target = _write_jsonl(
        tmp_path / "opc.jsonl",
        [
            {
                "url": "https://www.leboncoin.fr/ad/999999",
                "title": "Some Product",
                "price_text": "10,00 €",
                "currency_hint": "EUR",
            }
        ],
    )

    result = import_extension_file(target, in_memory_engine)

    assert result.records_imported == 0
    assert len(result.skipped) == 1
    assert "unattributed URL" in result.skipped[0]


def test_import_extension_file_attaches_to_existing_listing_url(
    in_memory_engine: Engine, tmp_path: Path
) -> None:
    url = "https://www.leboncoin.fr/ad/777"
    query_text = "AMD Ryzen 9 9950X3D"
    _, product_id = _seed_tracked_custom_url(in_memory_engine, query_text, url)
    # Pre-create the listing so URL resolution falls back to the listings table.
    ListingRepository(in_memory_engine).upsert(
        product_id=product_id,
        site_key="leboncoin",
        site_display_name="Leboncoin",
        url=url,
        image_url=None,
        seen_at=datetime.now(UTC),
        match_status="confirmed",
        match_score=95.0,
        match_reason="model token match",
    )

    target = _write_jsonl(
        tmp_path / "opc.jsonl",
        [
            {
                "url": url,
                "title": "AMD Ryzen 9 9950X3D 9950X3D 16-Core Processor",
                "price_text": "499,00 €",
                "currency_hint": "EUR",
            }
        ],
    )

    result = import_extension_file(target, in_memory_engine)
    assert result.records_imported == 1
    assert result.products_handled == [query_text]
