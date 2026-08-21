"""Tests for CandidateListingRepository (v2.17b)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, select

from storage.candidates import CandidateListing, CandidateListingRepository
from storage.schema import listings, price_history, tracked_product_site_overrides
from storage.watchlist import TrackedProductRepository


def test_candidate_repository_lifecycle(in_memory_engine: Engine) -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("AMD Ryzen 7 7800X3D")

    cand_repo = CandidateListingRepository(in_memory_engine)

    # 1. Add candidate listing
    cand = CandidateListing(
        tracked_product_id=tracked.id,
        site_key="coolmod",
        site_display_name="Coolmod",
        url="https://coolmod.com/item-123",
        title="AMD Ryzen 7 7800X3D Processor",
        match_status="confirmed",
        match_score=0.95,
        price_amount=389.90,
        currency="EUR",
        discovered_at=now,
        expires_at=now + timedelta(days=7),
    )
    cand_id = cand_repo.add(cand)
    assert cand_id is not None

    # Duplicate add returns None
    assert cand_repo.add(cand) is None

    # 2. Get by ID
    fetched = cand_repo.get_by_id(cand_id)
    assert fetched is not None
    assert fetched.title == "AMD Ryzen 7 7800X3D Processor"
    assert fetched.status == "pending"

    # 3. List pending
    pending = cand_repo.list_pending(tracked.id, as_of=now)
    assert len(pending) == 1
    assert pending[0].id == cand_id

    # 4. Approve candidate
    decision_time = now + timedelta(hours=2)
    approved = cand_repo.approve(cand_id, as_of=decision_time)
    assert approved is True

    # After approval, pending is empty
    assert len(cand_repo.list_pending(tracked.id, as_of=decision_time)) == 0

    # Candidate status is approved
    approved_cand = cand_repo.get_by_id(cand_id)
    assert approved_cand is not None
    assert approved_cand.status == "approved"
    assert approved_cand.decided_at == decision_time.replace(tzinfo=None)

    # Persistent listing exists
    with in_memory_engine.connect() as conn:
        listing_rows = conn.execute(
            select(listings).where(listings.c.product_id == tracked.product_id)
        ).all()
        assert len(listing_rows) == 1
        assert listing_rows[0].site_key == "coolmod"

        # Price history recorded
        price_rows = conn.execute(select(price_history)).all()
        assert len(price_rows) == 1
        assert price_rows[0].price_amount == 389.90

        # Override recorded
        override_rows = conn.execute(select(tracked_product_site_overrides)).all()
        assert len(override_rows) == 1
        assert override_rows[0].site_key == "coolmod"
        assert override_rows[0].included is True


def test_candidate_reject_and_expire(in_memory_engine: Engine) -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    tp_repo = TrackedProductRepository(in_memory_engine)
    tracked = tp_repo.get_or_create("Nvidia RTX 4080")

    cand_repo = CandidateListingRepository(in_memory_engine)

    # Add 2 candidates
    c1_id = cand_repo.add(
        CandidateListing(
            tracked_product_id=tracked.id,
            site_key="shop1",
            site_display_name="Shop 1",
            url="https://shop1.com/gpu",
            title="RTX 4080 16GB",
            match_status="confirmed",
            discovered_at=now,
            expires_at=now + timedelta(days=7),
        )
    )
    c2_id = cand_repo.add(
        CandidateListing(
            tracked_product_id=tracked.id,
            site_key="shop2",
            site_display_name="Shop 2",
            url="https://shop2.com/gpu",
            title="RTX 4080 OC",
            match_status="confirmed",
            discovered_at=now,
            expires_at=now + timedelta(days=2),
        )
    )
    assert c1_id is not None and c2_id is not None

    # Reject c1
    assert cand_repo.reject(c1_id, as_of=now) is True
    assert cand_repo.get_by_id(c1_id).status == "rejected"  # type: ignore[union-attr]

    # Only c2 is pending
    pending = cand_repo.list_pending(tracked.id, as_of=now)
    assert len(pending) == 1
    assert pending[0].id == c2_id

    # Fast forward 3 days -> c2 expires
    after_3d = now + timedelta(days=3)
    pending_later = cand_repo.list_pending(tracked.id, as_of=after_3d)
    assert len(pending_later) == 0

    assert cand_repo.get_by_id(c2_id).status == "expired"  # type: ignore[union-attr]
