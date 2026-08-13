"""Normalize raw listings and persist a price snapshot."""

from __future__ import annotations

import logging

from sqlalchemy import Engine

from models.listing import RawListing
from normalize.price import parse_price
from storage.repository import (
    ListingRepository,
    PriceHistoryRepository,
    ProductRepository,
)

logger = logging.getLogger(__name__)


def persist_snapshot(
    query_text: str, raw_listings: list[RawListing], engine: Engine
) -> int:
    """Persist one price observation per raw listing, returning the product id.

    Listings whose price text can't be parsed are skipped (logged, not
    fatal) — one bad price shouldn't prevent the rest of the snapshot from
    being saved.
    """
    product_repo = ProductRepository(engine)
    listing_repo = ListingRepository(engine)
    price_repo = PriceHistoryRepository(engine)

    product_id = product_repo.get_or_create(query_text)

    for raw in raw_listings:
        try:
            amount, currency = parse_price(raw.price_text, raw.currency_hint)
        except ValueError:
            logger.warning(
                "Skipping listing with unparseable price %r from %s",
                raw.price_text,
                raw.source,
            )
            continue

        listing_id = listing_repo.upsert(
            product_id=product_id,
            site_key=raw.source,
            site_display_name=raw.site_display_name,
            url=raw.url,
            image_url=raw.image_url,
            seen_at=raw.fetched_at,
        )
        price_repo.add(
            listing_id=listing_id,
            price_amount=amount,
            currency=currency,
            observed_at=raw.fetched_at,
            raw_price_text=raw.price_text,
        )

    return product_id
