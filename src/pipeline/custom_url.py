"""Processing and snapshot pipeline for custom listing URLs (v2.15 Tier A)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import Engine

from config.settings import Settings, get_settings
from fx.ecb import convert_to_eur
from matching.condition import extract_condition
from matching.matcher import MatchStatus, match_listing
from matching.profile import build_profile_from_query
from normalize.price import parse_price
from scrapers.custom_url import fetch_and_parse_custom_url
from storage.custom_urls import (
    CustomListingUrl,
    CustomListingUrlRepository,
    extract_site_info_from_url,
)
from storage.repository import ListingRepository, PriceHistoryRepository
from storage.watchlist import TrackedProductRepository

LOGGER = logging.getLogger(__name__)


def is_valid_http_url(url: str) -> bool:
    """True if URL has a valid http/https scheme and non-empty network location."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ("http", "https") and parsed.netloc)
    except Exception:
        return False


def track_and_process_custom_url(
    tracked_product_id: int,
    url: str,
    engine: Engine,
    settings: Settings | None = None,
    *,
    as_of: datetime | None = None,
    client: httpx.Client | None = None,
) -> tuple[bool, str]:
    """Register and process a single custom product-page URL (Tier A).

    Validates URL format, fetches and parses structured data / meta tags,
    validates identity match against the tracked product, normalizes FX,
    upserts into `listings`, and appends to `price_history`.

    Returns (success: bool, user_message: str).
    """
    clean_url = url.strip()
    if not is_valid_http_url(clean_url):
        return False, "Invalid URL. Please enter a full http:// or https:// URL."

    now = as_of or datetime.now(UTC)
    cfg = settings or get_settings()

    tp_repo = TrackedProductRepository(engine)
    tracked = tp_repo.get(tracked_product_id)
    if tracked is None:
        return False, f"Tracked product ID {tracked_product_id} not found."

    custom_repo = CustomListingUrlRepository(engine)
    listing_repo = ListingRepository(engine)
    price_repo = PriceHistoryRepository(engine)

    site_key, site_display_name = extract_site_info_from_url(clean_url)

    # 1. Add to custom_listing_urls (idempotent)
    custom_entry = CustomListingUrl(
        tracked_product_id=tracked.id,
        url=clean_url,
        site_key=site_key,
        site_display_name=site_display_name,
        added_at=now,
        status="active",
    )
    custom_id = custom_repo.add(custom_entry)
    if custom_id is None:
        existing = custom_repo.get_by_url(tracked.id, clean_url)
        if existing is not None and existing.id is not None:
            custom_id = existing.id

    # 2. Fetch and parse custom URL
    raw = fetch_and_parse_custom_url(
        clean_url,
        client=client,
        user_agent=cfg.browser_fallback_sites or None,
        as_of=now,
    )
    if raw is None:
        if custom_id is not None:
            custom_repo.update_status(
                custom_id,
                last_checked_at=now,
                status="failed",
                last_error="Could not fetch page or extract product price.",
            )
        return (
            False,
            f"Could not extract product information from {clean_url}. "
            "Make sure the page contains schema.org Product data or OpenGraph tags.",
        )

    # 3. Match against tracked product profile
    profile_query = tracked.canonical_name or tracked.query_text
    profile = build_profile_from_query(profile_query)
    match = match_listing(profile, raw.title)

    if match.status not in (MatchStatus.CONFIRMED, MatchStatus.LIKELY):
        if custom_id is not None:
            custom_repo.update_status(
                custom_id,
                last_checked_at=now,
                parser_confidence=raw.extra.get("parser_confidence", 0.5),
                status="unmatched",
                last_error=(
                    f"Title '{raw.title}' did not match tracked product "
                    f"({match.reason})."
                ),
            )
        return (
            False,
            f"Page title '{raw.title}' did not match tracked product "
            f"'{profile_query}': {match.reason}.",
        )

    # 4. Parse Price
    amount, currency = parse_price(raw.price_text, raw.currency_hint)
    if amount is None:
        if custom_id is not None:
            custom_repo.update_status(
                custom_id,
                last_checked_at=now,
                parser_confidence=raw.extra.get("parser_confidence", 0.5),
                status="failed",
                last_error=f"Could not parse price text '{raw.price_text}'.",
            )
        return (
            False,
            f"Found title '{raw.title}', but could not parse price from "
            f"'{raw.price_text}'.",
        )

    # 5. Extract Condition
    classified = extract_condition(
        raw.title, extra=raw.extra, site_key=site_key, profile=profile
    )

    # 6. Upsert listing
    listing_id = listing_repo.upsert(
        product_id=tracked.product_id,
        site_key=site_key,
        site_display_name=site_display_name,
        url=clean_url,
        image_url=raw.image_url,
        seen_at=now,
        match_status=match.status.value,
        match_score=match.score,
        match_reason=f"Custom URL: {match.reason}",
        condition=classified.condition.value,
        condition_source=classified.source.value,
        condition_confidence=classified.confidence,
    )

    # 7. Convert FX and add price observation
    effective_currency = currency or "EUR"
    conversion = convert_to_eur(amount, effective_currency)
    price_repo.add(
        listing_id=listing_id,
        price_amount=amount,
        currency=effective_currency,
        observed_at=now,
        raw_price_text=raw.price_text,
        price_native=amount,
        currency_native=effective_currency,
        price_eur_equivalent=conversion.price_eur_equivalent if conversion else None,
        fx_rate_used=conversion.fx_rate_used if conversion else None,
        fx_rate_date=conversion.fx_rate_date if conversion else None,
        condition=classified.condition.value,
        condition_source=classified.source.value,
        condition_confidence=classified.confidence,
    )

    # 8. Update custom URL status as active
    confidence = float(raw.extra.get("parser_confidence", 1.0))
    if custom_id is not None:
        custom_repo.update_status(
            custom_id,
            last_checked_at=now,
            parser_confidence=confidence,
            status="active",
            last_error=None,
        )

    return (
        True,
        f"Tracked custom listing from {site_display_name}: '{raw.title}' "
        f"at {effective_currency} {amount:.2f}.",
    )


def refresh_custom_urls_for_product(
    tracked_product_id: int,
    engine: Engine,
    settings: Settings | None = None,
    *,
    as_of: datetime | None = None,
    client: httpx.Client | None = None,
) -> list[tuple[str, bool, str]]:
    """Re-check all active custom listing URLs for a tracked product.

    Returns a list of (url, success, message) results.
    """
    custom_repo = CustomListingUrlRepository(engine)
    custom_urls = custom_repo.list_for_product(tracked_product_id)
    results: list[tuple[str, bool, str]] = []

    for item in custom_urls:
        if item.status == "inactive":
            continue
        success, message = track_and_process_custom_url(
            tracked_product_id,
            item.url,
            engine,
            settings=settings,
            as_of=as_of,
            client=client,
        )
        results.append((item.url, success, message))

    return results
