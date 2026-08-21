"""Read confirmed, non-anomalous EUR-price observations for alert evaluation.

Persistence concern is kept here (not in the storage layer's existing
repositories) so the alerting slice stays self-contained, mirroring
``AlertDeliveryRepository``. Reads only read - it never writes.

A ``price_eur_equivalent`` of NULL is treated as "no credible value" (a pre-
v2.10 row or a missing FX rate): the observation is skipped rather than
invented, exactly as ``docs/moon/roadmaps/settings_and_config.md`` and the
2026-08-21 v2.10 landing prescribe.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, select

from storage.repository import MATCHED_STATUSES
from storage.schema import listings, price_history


@dataclass(frozen=True)
class ListingObservation:
    """One usable (EUR) observation for a matched listing."""

    listing_id: int
    site_key: str
    site_display_name: str
    url: str
    observed_at: datetime
    eur_amount: float


@dataclass(frozen=True)
class ListingHistory:
    """A matched listing's EUR price series, ordered by time."""

    listing_id: int
    site_key: str
    site_display_name: str
    url: str
    observations: list[ListingObservation]


def listing_histories_for_product(
    engine: Engine,
    product_id: int,
    *,
    include_anomalous: bool = False,
) -> list[ListingHistory]:
    """Confirmed matched listings + their EUR-equivalent observations.

    Observations with a NULL ``price_eur_equivalent`` are dropped (they are
    not credible for an EUR-keyed rule). Unknown/anomalous rows are excluded
    unless ``include_anomalous``.
    """
    anomalous_filter = (
        () if include_anomalous else (price_history.c.is_anomalous.is_(False),)
    )
    stmt = (
        select(
            listings.c.id.label("listing_id"),
            listings.c.site_key,
            listings.c.site_display_name,
            listings.c.url,
            price_history.c.observed_at,
            price_history.c.price_eur_equivalent,
        )
        .join(listings, listings.c.id == price_history.c.listing_id)
        .where(
            listings.c.product_id == product_id,
            listings.c.match_status.in_(MATCHED_STATUSES),
            price_history.c.price_eur_equivalent.is_not(None),
            *anomalous_filter,
        )
        .order_by(price_history.c.observed_at)
    )
    with engine.connect() as conn:
        rows = conn.execute(stmt).all()

    by_listing: dict[int, list[Any]] = defaultdict(list)
    order: list[int] = []
    for row in rows:
        listing_id = int(row.listing_id)
        if listing_id not in by_listing:
            order.append(listing_id)
        by_listing[listing_id].append(row)

    histories: list[ListingHistory] = []
    for listing_id in order:
        rows_for_listing = by_listing[listing_id]
        first = rows_for_listing[0]
        observations = [
            ListingObservation(
                listing_id=listing_id,
                site_key=str(first.site_key),
                site_display_name=str(first.site_display_name),
                url=str(first.url),
                observed_at=row.observed_at,
                eur_amount=float(row.price_eur_equivalent),
            )
            for row in rows_for_listing
        ]
        histories.append(
            ListingHistory(
                listing_id=listing_id,
                site_key=str(first.site_key),
                site_display_name=str(first.site_display_name),
                url=str(first.url),
                observations=observations,
            )
        )
    return histories


def product_eur_timeline(
    histories: Sequence[ListingHistory],
) -> list[tuple[datetime, float]]:
    """Best (lowest) EUR price at each distinct observation timestamp.

    Used for the product-level target-price rule, where "current price" means
    the cheapest confirmed listing's EUR sticker at the latest observation and
    "previous" the cheapest at the observation before it.
    """
    grouped: dict[datetime, list[float]] = defaultdict(list)
    for history in histories:
        for obs in history.observations:
            grouped[obs.observed_at].append(obs.eur_amount)
    timeline: list[tuple[datetime, float]] = []
    for observed_at in sorted(grouped):
        timeline.append((observed_at, min(grouped[observed_at])))
    return timeline
