"""v2.11: persist_snapshot stores listing and observation-time condition."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, select

from models.listing import RawListing
from pipeline.snapshot import persist_snapshot
from storage.schema import listings, price_history


def test_persist_snapshot_writes_condition_on_listing_and_history(
    in_memory_engine: Engine,
) -> None:
    raw = RawListing(
        source="kleinanzeigen",
        source_kind="search_api",
        title="AMD Ryzen 9 9950X3D usado",
        url="https://example.com/used",
        price_text="400,00 €",
        currency_hint="EUR",
        image_url=None,
        site_display_name="Kleinanzeigen",
        fetched_at=datetime(2026, 8, 21, 12, 0, 0),
        extra={"item_condition": "https://schema.org/UsedCondition"},
    )
    persist_snapshot("AMD Ryzen 9 9950X3D", [raw], in_memory_engine)

    with in_memory_engine.connect() as conn:
        listing = conn.execute(select(listings)).one()
        observation = conn.execute(select(price_history)).one()

    assert listing.condition == "used"
    assert listing.condition_source == "structured_data"
    assert listing.condition_confidence == 0.9
    assert observation.condition == "used"
    assert observation.condition_source == "structured_data"
