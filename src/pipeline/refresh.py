"""Scheduled and passive refresh runner for tracked watchlist products (v2.2).

Iterates over enabled watchlist entries, checks whether each is due for
refresh based on its configured (or default) interval, runs discovery and
snapshot persistence, and updates `last_checked_at`.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Engine, func, select

from alerting.service import AlertingService
from config.settings import Settings, get_settings
from pipeline.discover import run_discovery
from pipeline.snapshot import persist_snapshot
from storage.repository import MATCHED_STATUSES
from storage.schema import listings
from storage.watchlist import (
    SiteSettingsRepository,
    TrackedProduct,
    TrackedProductRepository,
)

logger = logging.getLogger(__name__)


def is_due_for_refresh(
    tracked: TrackedProduct,
    *,
    default_interval_hours: int = 12,
    as_of: datetime | None = None,
) -> bool:
    """Return True if `tracked` is due for a price re-check.

    A product that has never been checked is always due. Otherwise, the
    configured per-product interval override (or `default_interval_hours`)
    determines the cadence.
    """
    if tracked.last_checked_at is None:
        return True
    interval_hours = tracked.refresh_interval_hours or default_interval_hours
    ref_time = as_of or datetime.now()
    return ref_time - tracked.last_checked_at >= timedelta(hours=interval_hours)


def _site_floor_hours(engine: Engine) -> dict[str, float]:
    """site_key -> min_refresh_interval_hours for sites that set a floor."""
    return {
        site.site_key: site.min_refresh_interval_hours
        for site in SiteSettingsRepository(engine).list_all()
        if site.min_refresh_interval_hours is not None
    }


def _last_seen_per_site(engine: Engine, product_id: int) -> dict[str, datetime]:
    """Most recent ``last_seen_at`` per site for this product's matched listings."""
    stmt = (
        select(
            listings.c.site_key,
            func.max(listings.c.last_seen_at).label("last_seen"),
        )
        .where(
            listings.c.product_id == product_id,
            listings.c.match_status.in_(MATCHED_STATUSES),
        )
        .group_by(listings.c.site_key)
    )
    with engine.connect() as conn:
        rows = conn.execute(stmt).all()
    return {
        str(row.site_key): row.last_seen for row in rows if row.last_seen is not None
    }


def sites_within_min_interval(
    engine: Engine,
    product_id: int,
    *,
    as_of: datetime | None = None,
) -> frozenset[str]:
    """Site keys whose own ``min_refresh_interval_hours`` has not yet elapsed.

    Independent of the per-product cadence: a tracked product can be due for
    refresh, but a specific site whose ``min_refresh_interval_hours`` floor is
    still fresh (per ``listings.last_seen_at`` for this product) is skipped for
    this pass. Sites that never set a floor are never gated here.
    """
    reference = as_of or datetime.now()
    floors = _site_floor_hours(engine)
    if not floors:
        return frozenset()
    last_seen = _last_seen_per_site(engine, product_id)
    skipped: set[str] = set()
    for site_key, floor_hours in floors.items():
        last = last_seen.get(site_key)
        if last is not None and reference - last < timedelta(hours=floor_hours):
            skipped.add(site_key)
    return frozenset(skipped)


def refresh_tracked_product(
    tracked: TrackedProduct,
    settings: Settings,
    engine: Engine,
    *,
    limit: int = 20,
    as_of: datetime | None = None,
) -> int:
    """Run discovery, snapshot persistence, and alert evaluation for one product.

    Honors global site settings and per-product site overrides. Also applies the
    v2.14 per-site cadence floor: a site whose own ``min_refresh_interval_hours``
    has not elapsed since this product was last seen there is skipped for this
    pass (still a tick script driven by ``cli refresh``, not a daemon). Touches
    `last_checked_at` on completion. After persisting the new price snapshot it
    runs the alert service (`alerting.AlertingService`) so a target-price
    crossing / all-time-low / meaningful-drop actually dispatches. Alerts are
    disabled when `alerts_enabled` is False. Returns the count of raw listings
    found.
    """
    skip_sites = sites_within_min_interval(engine, tracked.product_id, as_of=as_of)
    raw_listings = run_discovery(
        tracked.query_text,
        settings,
        limit=limit,
        engine=engine,
        tracked_product_id=tracked.id,
        skip_site_keys=skip_sites or None,
    )
    persist_snapshot(tracked.query_text, raw_listings, engine)
    try:
        from pipeline.custom_url import refresh_custom_urls_for_product

        refresh_custom_urls_for_product(tracked.id, engine, settings)
    except Exception:  # pragma: no cover
        logger.exception(
            "Custom URL refresh failed for tracked product %d (%r); continuing",
            tracked.id,
            tracked.query_text,
        )
    TrackedProductRepository(engine).touch_last_checked(tracked.id)

    if settings.alerts_enabled:
        try:
            AlertingService(engine, settings).evaluate_tracked_product(tracked.id)
        except Exception:  # pragma: no cover - alerting must not break refresh
            logger.exception(
                "Alert evaluation failed for tracked product %d (%r); continuing",
                tracked.id,
                tracked.query_text,
            )
    return len(raw_listings)


def refresh_watchlist(
    engine: Engine,
    settings: Settings | None = None,
    *,
    force: bool = False,
    limit: int = 20,
    as_of: datetime | None = None,
) -> dict[int, int]:
    """Check and refresh due products in the watchlist.

    When `force` is True, all enabled products are refreshed regardless of
    their `last_checked_at` timestamp. Returns a mapping of
    `tracked_product_id -> raw_listings_count` for all refreshed entries.
    """
    cfg = settings or get_settings()
    tracked_repo = TrackedProductRepository(engine)
    enabled_products = tracked_repo.list_all(enabled_only=True)

    refreshed: dict[int, int] = {}
    for product in enabled_products:
        if force or is_due_for_refresh(
            product,
            default_interval_hours=cfg.refresh_interval_hours,
            as_of=as_of,
        ):
            count = refresh_tracked_product(product, cfg, engine, limit=limit)
            refreshed[product.id] = count
            logger.info(
                "Refreshed tracked product %d (%r): %d raw listings",
                product.id,
                product.query_text,
                count,
            )
    return refreshed


def run_monitoring_loop(
    engine: Engine,
    settings: Settings | None = None,
    *,
    check_interval_seconds: float = 60.0,
    max_iterations: int | None = None,
    stop_event: Any = None,
) -> int:
    """Run a periodic passive monitoring loop refreshing due products.

    Useful for running as a background task, cron job, or container entrypoint.
    Returns the total number of refresh iterations completed.
    """
    cfg = settings or get_settings()
    iterations = 0
    while True:
        if stop_event is not None and getattr(stop_event, "is_set", lambda: False)():
            break

        refresh_watchlist(engine, cfg)
        iterations += 1

        if max_iterations is not None and iterations >= max_iterations:
            break

        if stop_event is not None:
            if getattr(stop_event, "wait", lambda t: False)(check_interval_seconds):
                break
        else:
            time.sleep(check_interval_seconds)

    return iterations
