"""Tests for manual source discovery pipeline (v2.17b)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine

from models.listing import RawListing
from pipeline.source_discovery import (
    DEFAULT_DAILY_CREDIT_BUDGET,
    check_and_consume_daily_budget,
    discover_sources_for_product,
    reset_discovery_budget,
)
from search.base import SearchProvider
from storage.candidates import CandidateListingRepository
from storage.watchlist import TrackedProductRepository


class DummySearchProvider(SearchProvider):
    """Test search provider returning predefined raw listings."""

    name = "dummy_provider"

    def __init__(self, listings: list[RawListing]) -> None:
        self._listings = listings

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        return self._listings[:limit]


def test_discover_sources_for_product_creates_candidates(
    in_memory_engine: Engine,
) -> None:
    reset_discovery_budget()
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("AMD Ryzen 7 7800X3D")

    sample_listings = [
        # Good match
        RawListing(
            source="coolmod",
            site_display_name="Coolmod",
            url="https://coolmod.com/ryzen-7800x3d",
            title="AMD Ryzen 7 7800X3D CPU",
            price_text="380,00 €",
            currency_hint="EUR",
            image_url="https://coolmod.com/img.jpg",
            source_kind="search_api",
            fetched_at=now,
        ),
        # Irrelevant product -> filtered out by match_listing
        RawListing(
            source="amazon_es",
            site_display_name="Amazon.es",
            url="https://amazon.es/dp/B000",
            title="Thermal Paste Arctic MX-4 4g",
            price_text="7,99 €",
            currency_hint="EUR",
            image_url=None,
            source_kind="search_api",
            fetched_at=now,
        ),
    ]

    provider = DummySearchProvider(sample_listings)
    candidates = discover_sources_for_product(
        tracked.id,
        in_memory_engine,
        as_of=now,
        provider=provider,
    )

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.site_key == "coolmod"
    assert cand.title == "AMD Ryzen 7 7800X3D CPU"
    assert cand.price_amount == 380.00
    assert cand.currency == "EUR"
    assert cand.status == "pending"

    # Verify persisted in repository
    cand_repo = CandidateListingRepository(in_memory_engine)
    pending = cand_repo.list_pending(tracked.id, as_of=now)
    assert len(pending) == 1
    assert pending[0].url == "https://coolmod.com/ryzen-7800x3d"

    # Running again ignores duplicate candidate
    second_run = discover_sources_for_product(
        tracked.id,
        in_memory_engine,
        as_of=now,
        provider=provider,
    )
    assert len(second_run) == 0


def test_discover_sources_budget_limit(in_memory_engine: Engine) -> None:
    reset_discovery_budget()
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("AMD Ryzen 7 7800X3D")

    # Consume all daily budget
    assert (
        check_and_consume_daily_budget(requested=DEFAULT_DAILY_CREDIT_BUDGET, as_of=now)
        is True
    )

    # Next attempt fails budget check
    assert check_and_consume_daily_budget(requested=1, as_of=now) is False

    provider = DummySearchProvider([])
    candidates = discover_sources_for_product(
        tracked.id,
        in_memory_engine,
        as_of=now,
        provider=provider,
    )
    assert len(candidates) == 0

    reset_discovery_budget()
