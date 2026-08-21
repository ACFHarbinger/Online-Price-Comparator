"""Manual verification of KuantoKusta retailer-URL hints into candidates."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from sqlalchemy import Engine, select

from config.settings import Settings, get_settings
from fetch.circuit_breaker import CircuitBreaker
from fetch.http_client import DEFAULT_USER_AGENT, build_http_client, get_with_retry
from fetch.rate_limit import HostRateLimiter
from fetch.response_cache import get_cached, set_cached
from fetch.robots import is_allowed
from matching.matcher import MatchStatus, match_listing
from matching.profile import ProductIdentityProfile, build_profile_from_query
from normalize.price import parse_price
from scrapers.kuantokusta import RetailerUrlHint
from scrapers.registry import enabled_hint_sources
from scrapers.structured_data import StructuredProduct, extract_structured_products
from storage.candidates import CandidateListing, CandidateListingRepository
from storage.schema import listings
from storage.watchlist import TrackedProductRepository

LOGGER = logging.getLogger(__name__)

DEFAULT_CANDIDATE_TTL_DAYS = 7
DEFAULT_PER_RUN_LIMIT = 10
_MIN_INTERVAL_SECONDS = 12.0
_BLOCK_MARKERS = ("captcha", "access denied", "verify you are human", "cloudflare")
_KNOWN_RETAILERS: dict[str, tuple[str, str]] = {
    "www.amazon.es": ("amazon.es", "Amazon.es"),
    "www.pccomponentes.pt": ("pccomponentes", "PcComponentes"),
    "www.pcdiga.com": ("pcdiga", "PCDIGA"),
    "www.worten.pt": ("worten", "Worten"),
    "www.fnac.pt": ("fnac", "Fnac.pt"),
    "chip7.pt": ("chip7", "CHIP7"),
}


class RetailerHintSource(Protocol):
    """Typed URL-hint source, intentionally separate from ``ScraperAdapter``."""

    def search(self, query: str, *, limit: int = 20) -> list[RetailerUrlHint]: ...


FetchHtml = Callable[[str, Settings], str | None]


def verify_kuantokusta_hints_for_product(
    tracked_product_id: int,
    engine: Engine,
    settings: Settings | None = None,
    *,
    limit: int = DEFAULT_PER_RUN_LIMIT,
    ttl_days: int = DEFAULT_CANDIDATE_TTL_DAYS,
    as_of: datetime | None = None,
    hint_sources: Sequence[RetailerHintSource] | None = None,
    fetch_html: FetchHtml | None = None,
) -> list[CandidateListing]:
    """Verify real retailer pages from manual hints into pending candidates.

    Aggregator HTML and prices never enter this function's candidate data: only
    a real retailer page's complete schema.org Product/Offer is parsed and
    identity-matched. Candidates remain pending until the user approves them.
    """
    if limit <= 0:
        return []

    cfg = settings or get_settings()
    now = as_of or datetime.now(UTC)
    tracked = TrackedProductRepository(engine).get(tracked_product_id)
    if tracked is None:
        LOGGER.warning(
            "KuantoKusta verification for missing tracked product %d",
            tracked_product_id,
        )
        return []

    query = tracked.canonical_name or tracked.query_text
    sources = (
        list(hint_sources) if hint_sources is not None else enabled_hint_sources(cfg)
    )
    hints = [hint for source in sources for hint in source.search(query, limit=limit)][
        :limit
    ]
    if not hints:
        return []

    candidate_repo = CandidateListingRepository(engine)
    existing_urls = _existing_urls(
        engine, tracked.product_id, candidate_repo, tracked.id
    )
    profile = build_profile_from_query(query)
    expires_at = now + timedelta(days=ttl_days)
    retrieve = fetch_html or _fetch_retailer_html
    candidates: list[CandidateListing] = []

    for hint in hints:
        if hint.destination_url in existing_urls:
            continue
        html = retrieve(hint.destination_url, cfg)
        if html is None:
            continue
        product = _matching_product(html, profile)
        if product is None:
            continue
        try:
            amount, currency = parse_price(product.price_text, product.currency)
        except ValueError:
            LOGGER.info("Skipping unverifiable price at %s", hint.destination_url)
            continue
        match = match_listing(profile, product.title)
        site_key, display_name = _retailer_identity(hint.destination_url)
        candidate = CandidateListing(
            tracked_product_id=tracked.id,
            site_key=site_key,
            site_display_name=display_name,
            url=hint.destination_url,
            title=product.title,
            price_amount=amount,
            currency=currency or "EUR",
            image_url=(
                urljoin(hint.destination_url, product.image_url)
                if product.image_url
                else None
            ),
            match_status=match.status.value,
            match_score=match.score,
            discovered_at=now,
            expires_at=expires_at,
        )
        candidate_id = candidate_repo.add(candidate)
        if candidate_id is not None:
            candidates.append(_with_id(candidate, candidate_id))
            existing_urls.add(hint.destination_url)
    return candidates


def _matching_product(
    html: str, profile: ProductIdentityProfile
) -> StructuredProduct | None:
    """Return a complete JSON-LD product only when it confirms or likely-matches."""
    soup = BeautifulSoup(html, "lxml")
    for product in extract_structured_products(soup):
        match = match_listing(profile, product.title)
        if match.status in (MatchStatus.CONFIRMED, MatchStatus.LIKELY):
            return product
    return None


def _existing_urls(
    engine: Engine,
    product_id: int,
    candidate_repo: CandidateListingRepository,
    tracked_product_id: int,
) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(listings.c.url).where(listings.c.product_id == product_id)
        ).all()
    return {row.url for row in rows} | {
        candidate.url for candidate in candidate_repo.list_all(tracked_product_id)
    }


def _fetch_retailer_html(url: str, settings: Settings) -> str | None:
    """Polite, fail-closed fetch of one hinted retailer product page."""
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.scheme not in {"http", "https"} or not host:
        return None
    site_key = f"retailer-url:{host}"
    breaker = CircuitBreaker()
    if breaker.is_open(site_key):
        return None
    cached = get_cached(site_key, url)
    if cached is not None:
        return cached
    if not is_allowed(
        url, DEFAULT_USER_AGENT, cache_ttl_hours=settings.robots_cache_ttl_hours
    ):
        LOGGER.warning("robots.txt disallows hinted retailer URL %s", url)
        return None
    try:
        HostRateLimiter(_MIN_INTERVAL_SECONDS).wait(host)
        with build_http_client() as client:
            response = get_with_retry(
                client,
                url,
                headers={"Accept-Language": "pt-PT,pt;q=0.9,en;q=0.7"},
                max_attempts=settings.retry_max_attempts,
                initial_backoff_seconds=settings.retry_initial_backoff_seconds,
                max_backoff_seconds=settings.retry_max_backoff_seconds,
            )
            response.raise_for_status()
        html = response.text
        if any(marker in html.lower() for marker in _BLOCK_MARKERS):
            breaker.record_failure(site_key)
            return None
        set_cached(site_key, url, html)
        breaker.record_success(site_key)
        return html
    except Exception:
        breaker.record_failure(site_key)
        LOGGER.warning(
            "Hinted retailer verification fetch failed for %s", url, exc_info=True
        )
        return None


def _retailer_identity(url: str) -> tuple[str, str]:
    hostname = (urlparse(url).hostname or "unknown-retailer").lower()
    return _KNOWN_RETAILERS.get(hostname, (hostname, hostname))


def _with_id(candidate: CandidateListing, candidate_id: int) -> CandidateListing:
    return CandidateListing(
        id=candidate_id,
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
