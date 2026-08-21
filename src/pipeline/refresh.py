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

from sqlalchemy import Engine

from config.settings import Settings, get_settings
from pipeline.discover import run_discovery
from pipeline.snapshot import persist_snapshot
from storage.watchlist import TrackedProduct, TrackedProductRepository

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


def refresh_tracked_product(
    tracked: TrackedProduct,
    settings: Settings,
    engine: Engine,
    *,
    limit: int = 20,
) -> int:
    """Run discovery and snapshot persistence for a single tracked product.

    Honors global site settings and per-product site overrides. Touches
    `last_checked_at` on completion. Returns the count of raw listings found.
    """
    raw_listings = run_discovery(
        tracked.query_text,
        settings,
        limit=limit,
        engine=engine,
        tracked_product_id=tracked.id,
    )
    persist_snapshot(tracked.query_text, raw_listings, engine)
    TrackedProductRepository(engine).touch_last_checked(tracked.id)
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
