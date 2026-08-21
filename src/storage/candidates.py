"""Candidate listing data models and repository (v2.17b)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, and_, select, update
from sqlalchemy.exc import IntegrityError

from storage.schema import (
    candidate_listings,
    listings,
    price_history,
    tracked_product_site_overrides,
    tracked_products,
)


@dataclass(frozen=True)
class CandidateListing:
    """A discovered potential listing awaiting user approval."""

    tracked_product_id: int
    site_key: str
    site_display_name: str
    url: str
    title: str
    match_status: str
    discovered_at: datetime
    expires_at: datetime
    price_amount: float | None = None
    currency: str = "EUR"
    image_url: str | None = None
    match_score: float | None = None
    status: str = "pending"
    decided_at: datetime | None = None
    id: int | None = None


def _row_to_candidate(row: Any) -> CandidateListing:
    return CandidateListing(
        id=row.id,
        tracked_product_id=row.tracked_product_id,
        site_key=row.site_key,
        site_display_name=row.site_display_name,
        url=row.url,
        title=row.title,
        price_amount=row.price_amount,
        currency=row.currency,
        image_url=row.image_url,
        match_status=row.match_status,
        match_score=row.match_score,
        status=row.status,
        discovered_at=row.discovered_at,
        expires_at=row.expires_at,
        decided_at=row.decided_at,
    )


class CandidateListingRepository:
    """Repository for managing time-limited candidate listings."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add(self, candidate: CandidateListing) -> int | None:
        """Insert a candidate listing. Returns its ID or None if duplicate."""
        stmt = candidate_listings.insert().values(
            tracked_product_id=candidate.tracked_product_id,
            site_key=candidate.site_key,
            site_display_name=candidate.site_display_name,
            url=candidate.url,
            title=candidate.title,
            price_amount=candidate.price_amount,
            currency=candidate.currency,
            image_url=candidate.image_url,
            match_status=candidate.match_status,
            match_score=candidate.match_score,
            status=candidate.status,
            discovered_at=candidate.discovered_at,
            expires_at=candidate.expires_at,
            decided_at=candidate.decided_at,
        )
        try:
            with self.engine.begin() as conn:
                result = conn.execute(stmt)
                pk = result.inserted_primary_key
                if pk:
                    return int(pk[0])
                return None
        except IntegrityError:
            return None

    def get_by_id(self, candidate_id: int) -> CandidateListing | None:
        """Fetch candidate listing by ID."""
        stmt = select(candidate_listings).where(candidate_listings.c.id == candidate_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).first()
            if row is None:
                return None
            return _row_to_candidate(row)

    def list_pending(
        self,
        tracked_product_id: int | None = None,
        *,
        as_of: datetime | None = None,
    ) -> list[CandidateListing]:
        """List active pending candidate listings, marking expired ones."""
        now = as_of or datetime.now(UTC)
        self.expire_stale(as_of=now)

        conditions = [
            candidate_listings.c.status == "pending",
            candidate_listings.c.expires_at > now,
        ]
        if tracked_product_id is not None:
            conditions.append(
                candidate_listings.c.tracked_product_id == tracked_product_id
            )

        stmt = (
            select(candidate_listings)
            .where(and_(*conditions))
            .order_by(candidate_listings.c.discovered_at.desc())
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
            return [_row_to_candidate(r) for r in rows]

    def list_all(
        self,
        tracked_product_id: int | None = None,
    ) -> list[CandidateListing]:
        """List all candidate listings regardless of status."""
        stmt = select(candidate_listings)
        if tracked_product_id is not None:
            stmt = stmt.where(
                candidate_listings.c.tracked_product_id == tracked_product_id
            )
        stmt = stmt.order_by(candidate_listings.c.discovered_at.desc())
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
            return [_row_to_candidate(r) for r in rows]

    def approve(
        self,
        candidate_id: int,
        *,
        as_of: datetime | None = None,
    ) -> bool:
        """Approve a candidate listing, promoting it to a persistent listing."""
        candidate = self.get_by_id(candidate_id)
        if candidate is None or candidate.status != "pending":
            return False

        decided = as_of or datetime.now(UTC)

        with self.engine.begin() as conn:
            # 1. Update candidate status
            conn.execute(
                update(candidate_listings)
                .where(candidate_listings.c.id == candidate_id)
                .values(status="approved", decided_at=decided)
            )

            # 2. Lookup tracked product to get product_id
            tp_row = conn.execute(
                select(tracked_products).where(
                    tracked_products.c.id == candidate.tracked_product_id
                )
            ).first()
            if tp_row is None:
                return True

            product_id = tp_row.product_id

            # 3. Ensure site override is enabled (included=True)
            existing_override = conn.execute(
                select(tracked_product_site_overrides).where(
                    and_(
                        tracked_product_site_overrides.c.tracked_product_id
                        == candidate.tracked_product_id,
                        tracked_product_site_overrides.c.site_key == candidate.site_key,
                    )
                )
            ).first()
            if existing_override is None:
                conn.execute(
                    tracked_product_site_overrides.insert().values(
                        tracked_product_id=candidate.tracked_product_id,
                        site_key=candidate.site_key,
                        included=True,
                        reason="Approved from candidate discovery",
                    )
                )
            elif not existing_override.included:
                conn.execute(
                    update(tracked_product_site_overrides)
                    .where(tracked_product_site_overrides.c.id == existing_override.id)
                    .values(
                        included=True,
                        reason="Approved from candidate discovery",
                    )
                )

            # 4. Insert or update persistent listing
            existing_listing = conn.execute(
                select(listings).where(
                    and_(
                        listings.c.product_id == product_id,
                        listings.c.site_key == candidate.site_key,
                        listings.c.url == candidate.url,
                    )
                )
            ).first()

            if existing_listing is None:
                res = conn.execute(
                    listings.insert().values(
                        product_id=product_id,
                        site_key=candidate.site_key,
                        site_display_name=candidate.site_display_name,
                        url=candidate.url,
                        image_url=candidate.image_url,
                        first_seen_at=candidate.discovered_at,
                        last_seen_at=decided,
                        match_status=candidate.match_status,
                        match_score=candidate.match_score,
                        match_reason="Approved candidate source",
                    )
                )
                assert res.inserted_primary_key is not None
                listing_id = int(res.inserted_primary_key[0])
            else:
                listing_id = existing_listing.id
                conn.execute(
                    update(listings)
                    .where(listings.c.id == listing_id)
                    .values(last_seen_at=decided)
                )

            # 5. Insert initial price record if present
            if candidate.price_amount is not None:
                conn.execute(
                    price_history.insert().values(
                        listing_id=listing_id,
                        price_amount=candidate.price_amount,
                        currency=candidate.currency,
                        observed_at=decided,
                        is_anomalous=False,
                    )
                )

        return True

    def reject(
        self,
        candidate_id: int,
        *,
        as_of: datetime | None = None,
    ) -> bool:
        """Reject a candidate listing."""
        candidate = self.get_by_id(candidate_id)
        if candidate is None or candidate.status != "pending":
            return False

        decided = as_of or datetime.now(UTC)
        with self.engine.begin() as conn:
            conn.execute(
                update(candidate_listings)
                .where(candidate_listings.c.id == candidate_id)
                .values(status="rejected", decided_at=decided)
            )
        return True

    def expire_stale(self, *, as_of: datetime | None = None) -> int:
        """Mark expired pending candidate listings."""
        now = as_of or datetime.now(UTC)
        with self.engine.begin() as conn:
            result = conn.execute(
                update(candidate_listings)
                .where(
                    and_(
                        candidate_listings.c.status == "pending",
                        candidate_listings.c.expires_at <= now,
                    )
                )
                .values(status="expired", decided_at=now)
            )
            return int(result.rowcount)
