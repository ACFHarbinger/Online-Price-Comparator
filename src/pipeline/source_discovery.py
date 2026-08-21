"""Manual per-product source discovery and candidate generation (v2.17b)."""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, select

from config.settings import Settings, get_settings
from matching.matcher import MatchStatus, match_listing
from matching.profile import build_profile_from_query
from normalize.price import parse_price
from search.base import SearchProvider
from search.providers.serpapi import SerpApiProvider
from storage.candidates import CandidateListing, CandidateListingRepository
from storage.schema import listings
from storage.watchlist import TrackedProductRepository

logger = logging.getLogger(__name__)

DEFAULT_CANDIDATE_TTL_DAYS = 7
DEFAULT_PER_RUN_BUDGET = 10
DEFAULT_DAILY_CREDIT_BUDGET = 50

_daily_credits_spent: int = 0
_last_reset_day: datetime | None = None
_budget_lock = threading.Lock()


def check_and_consume_daily_budget(
    requested: int = 1,
    *,
    max_daily: int = DEFAULT_DAILY_CREDIT_BUDGET,
    as_of: datetime | None = None,
) -> bool:
    """Thread-safe check and increment for daily search-API credit spending."""
    global _daily_credits_spent, _last_reset_day
    now = as_of or datetime.now(UTC)
    with _budget_lock:
        if _last_reset_day is None or _last_reset_day.date() != now.date():
            _daily_credits_spent = 0
            _last_reset_day = now
        if _daily_credits_spent + requested > max_daily:
            return False
        _daily_credits_spent += requested
        return True


def reset_discovery_budget() -> None:
    """Reset the process-wide credit budget counter (for testing)."""
    global _daily_credits_spent, _last_reset_day
    with _budget_lock:
        _daily_credits_spent = 0
        _last_reset_day = None


def discover_sources_for_product(
    tracked_product_id: int,
    engine: Engine,
    settings: Settings | None = None,
    *,
    limit: int = DEFAULT_PER_RUN_BUDGET,
    ttl_days: int = DEFAULT_CANDIDATE_TTL_DAYS,
    as_of: datetime | None = None,
    provider: SearchProvider | None = None,
) -> list[CandidateListing]:
    """Execute manual source discovery for one tracked product.

    Queries search-API provider (SerpAPI / Google Shopping), filters results
    against ProductIdentityProfile, and saves time-limited pending candidates
    to `candidate_listings`. Never auto-promotes candidates to persistent tracking.
    """
    cfg = settings or get_settings()
    now = as_of or datetime.now(UTC)
    tracked_repo = TrackedProductRepository(engine)
    candidates_repo = CandidateListingRepository(engine)

    tracked = tracked_repo.get(tracked_product_id)
    if tracked is None:
        logger.warning(
            "Source discovery called for non-existent tracked_product_id=%d",
            tracked_product_id,
        )
        return []

    # Credit budget check
    if not check_and_consume_daily_budget(requested=1, as_of=now):
        logger.warning(
            "Daily source discovery credit budget exhausted (max=%d). Skipping.",
            DEFAULT_DAILY_CREDIT_BUDGET,
        )
        return []

    search_provider: SearchProvider | None = provider
    if search_provider is None and cfg.serpapi_key:
        search_provider = SerpApiProvider(cfg.serpapi_key)

    if search_provider is None or not search_provider.is_configured():
        logger.info(
            "No configured SearchProvider for source discovery on '%s'.",
            tracked.query_text,
        )
        return []

    query = tracked.canonical_name or tracked.query_text
    raw_listings = search_provider.search(query, limit=limit)
    if not raw_listings:
        return []

    # Get existing persistent URLs for this product to avoid proposing existing ones
    with engine.connect() as conn:
        existing_rows = conn.execute(
            select(listings.c.url).where(listings.c.product_id == tracked.product_id)
        ).all()
        existing_urls = {r.url for r in existing_rows}

    # Get already recorded candidate URLs
    existing_candidates = candidates_repo.list_all(tracked_product_id)
    existing_candidate_urls = {c.url for c in existing_candidates}

    profile = build_profile_from_query(query)
    expires_at = now + timedelta(days=ttl_days)
    new_candidates: list[CandidateListing] = []

    for raw in raw_listings:
        if raw.url in existing_urls or raw.url in existing_candidate_urls:
            continue

        match = match_listing(profile, raw.title)
        if match.status not in (MatchStatus.CONFIRMED, MatchStatus.LIKELY):
            continue

        amount, currency = parse_price(raw.price_text, raw.currency_hint)

        candidate = CandidateListing(
            tracked_product_id=tracked.id,
            site_key=raw.source,
            site_display_name=raw.site_display_name,
            url=raw.url,
            title=raw.title,
            price_amount=amount,
            currency=currency or "EUR",
            image_url=raw.image_url,
            match_status=match.status.value,
            match_score=match.score,
            status="pending",
            discovered_at=now,
            expires_at=expires_at,
        )
        cand_id = candidates_repo.add(candidate)
        if cand_id is not None:
            new_candidates.append(
                CandidateListing(
                    id=cand_id,
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
                )
            )
            existing_candidate_urls.add(raw.url)

    return new_candidates
