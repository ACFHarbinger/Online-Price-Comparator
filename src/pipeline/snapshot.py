"""Normalize raw listings and persist a price snapshot."""

from __future__ import annotations

import logging

from sqlalchemy import Engine

from matching import MatchStatus, build_profile_from_query, match_listing
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
    """Persist one price observation per matched raw listing, returning the product id.

    Every listing is matched against a product-identity profile derived
    from `query_text` (see `matching.build_profile_from_query`) and always
    upserted with its match verdict, for audit visibility - but only
    `confirmed` listings get a `price_history` point. `likely`/`review`/
    `rejected` listings are kept in `listings` (never silently dropped)
    but excluded from all read-side queries until a later, config-driven
    match mode lets a user promote them. Listings whose price text can't
    be parsed are skipped entirely (logged, not fatal).
    """
    product_repo = ProductRepository(engine)
    listing_repo = ListingRepository(engine)
    price_repo = PriceHistoryRepository(engine)

    product_id = product_repo.get_or_create(query_text)
    profile = build_profile_from_query(query_text)

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

        match = match_listing(profile, raw.title)
        listing_id = listing_repo.upsert(
            product_id=product_id,
            site_key=raw.source,
            site_display_name=raw.site_display_name,
            url=raw.url,
            image_url=raw.image_url,
            seen_at=raw.fetched_at,
            match_status=match.status.value,
            match_score=match.score,
            match_reason=match.reason,
        )

        if match.status is not MatchStatus.CONFIRMED:
            logger.info(
                "Listing not confirmed (%s: %s), skipping price_history: %r from %s",
                match.status.value,
                match.reason,
                raw.title,
                raw.source,
            )
            continue

        price_repo.add(
            listing_id=listing_id,
            price_amount=amount,
            currency=currency,
            observed_at=raw.fetched_at,
            raw_price_text=raw.price_text,
        )

    return product_id
