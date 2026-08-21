"""Normalize raw listings and persist a price snapshot."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import Engine

from fx.ecb import Conversion, convert_to_eur
from matching import (
    MatchStatus,
    build_profile_from_query,
    detect_anomalies,
    extract_condition,
    match_listing,
)
from models.listing import RawListing
from normalize.price import parse_price
from storage.repository import (
    ListingRepository,
    PriceHistoryRepository,
    ProductRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ConfirmedObservation:
    """A parsed, identity-confirmed price, pending an anomaly check."""

    raw: RawListing
    listing_id: int
    conversion: Conversion
    condition: str
    condition_source: str
    condition_confidence: float


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

    Confirmed listings are then checked for cross-retailer price outliers
    (`matching.detect_anomalies`, per exact condition bucket on scrape-time
    EUR-equivalent stickers). An anomalous point is still recorded (never
    dropped), just flagged so read-side queries skip past it. ``unknown``
    condition and missing EUR equivalents never enter an IQR sample;
    sparse buckets (n<4) never auto-hide.
    """
    product_repo = ProductRepository(engine)
    listing_repo = ListingRepository(engine)
    price_repo = PriceHistoryRepository(engine)

    product_id = product_repo.get_or_create(query_text)
    profile = build_profile_from_query(query_text)

    confirmed: list[_ConfirmedObservation] = []
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
        classified = extract_condition(
            raw.title, extra=raw.extra, site_key=raw.source, profile=profile
        )
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
            condition=classified.condition.value,
            condition_source=classified.source.value,
            condition_confidence=classified.confidence,
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

        confirmed.append(
            _ConfirmedObservation(
                raw,
                listing_id,
                convert_to_eur(amount, currency),
                classified.condition.value,
                classified.source.value,
                classified.confidence,
            )
        )

    anomalies = detect_anomalies(
        [observation.conversion.price_eur_equivalent for observation in confirmed],
        [observation.raw.title for observation in confirmed],
        conditions=[observation.condition for observation in confirmed],
    )
    for observation, anomaly in zip(confirmed, anomalies, strict=True):
        if anomaly.is_anomalous:
            logger.warning(
                "Anomalous price flagged (%s) for %r from %s: %s",
                anomaly.reason,
                observation.raw.title,
                observation.raw.source,
                anomaly.basis,
            )
        conversion = observation.conversion
        price_repo.add(
            listing_id=observation.listing_id,
            price_amount=conversion.price_native,
            currency=conversion.currency_native,
            observed_at=observation.raw.fetched_at,
            raw_price_text=observation.raw.price_text,
            is_anomalous=anomaly.is_anomalous,
            anomaly_reason=anomaly.reason,
            anomaly_basis=anomaly.basis,
            price_native=conversion.price_native,
            currency_native=conversion.currency_native,
            price_eur_equivalent=conversion.price_eur_equivalent,
            fx_rate_used=conversion.fx_rate_used,
            fx_rate_date=conversion.fx_rate_date,
            condition=observation.condition,
            condition_source=observation.condition_source,
            condition_confidence=observation.condition_confidence,
        )

    return product_id
