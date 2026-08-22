"""Watchlist and per-site enablement repositories (v2.1).

Lives beside ``storage.repository`` so the price-history/stats path stays
untouched. These tables are the SQLite half of persistent settings:
tracked products, global ``site_settings.enabled``, and per-product site
inclusion exceptions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from storage.repository import ProductRepository
from storage.schema import (
    site_settings,
    tracked_product_site_overrides,
    tracked_products,
)

SEARCH_SCOPE_TIERS = frozenset({"local", "eu_wide", "global"})
HISTORICAL_LOW_ALERT_MODES = frozenset({"tiered", "percentile", "both"})
DEFAULT_SEARCH_SCOPE_TIER = "local"
DEFAULT_HISTORICAL_LOW_ALERT_MODE = "tiered"
#: Valid `site_settings.collection_method` values (v2.20). `server_scrape` is the
#: default; `client_extension` means the browser extension collects it (never a
#: server scrape); `search_api` / `hint_only` mirror v2.17a / v2.8.
COLLECTION_METHODS = frozenset(
    {"server_scrape", "client_extension", "search_api", "hint_only"}
)


@dataclass(frozen=True)
class TrackedProduct:
    """One persistent watchlist entry, linked to a ``products`` row."""

    id: int
    product_id: int
    query_text: str
    canonical_name: str | None
    enabled: bool
    refresh_interval_hours: int | None
    target_price: float | None
    target_currency: str | None
    search_scope_tier: str
    historical_low_alert_mode: str
    rarity_percentile: float | None
    rarity_window_days: int | None
    rarity_min_observations: int | None
    created_at: datetime
    last_checked_at: datetime | None


@dataclass(frozen=True)
class SiteSetting:
    """Persisted per-site defaults. A missing row means the site is enabled."""

    site_key: str
    enabled: bool
    result_limit: int | None
    min_request_interval_seconds: float | None
    cache_ttl_seconds: int | None
    browser_rendering_allowed: bool
    min_refresh_interval_hours: float | None
    shipping_cost_estimate_eur: float | None
    collection_method: str = "server_scrape"


@dataclass(frozen=True)
class SiteOverride:
    """Per-tracked-product exception to the global ``site_settings.enabled``."""

    tracked_product_id: int
    site_key: str
    included: bool
    reason: str | None


def resolve_site_keys(
    registered_keys: Sequence[str],
    *,
    globally_disabled: frozenset[str] | set[str] = frozenset(),
    overrides: Mapping[str, bool] | None = None,
) -> list[str]:
    """Apply global enablement plus per-product exceptions, in registry order.

    Env allowlisting (``ENABLED_SCRAPERS``) happens before this, via
    ``scrapers.registry.enabled_scrapers``. A missing override means "follow
    the global default"; ``included=False`` opts out; ``included=True`` opts
    in even when the site is globally disabled.
    """
    override_map = dict(overrides or {})
    enabled: list[str] = []
    for key in registered_keys:
        if key in override_map:
            if override_map[key]:
                enabled.append(key)
            continue
        if key not in globally_disabled:
            enabled.append(key)
    return enabled


def _row_to_tracked(row: Any) -> TrackedProduct:
    """Map a SQLAlchemy result row to ``TrackedProduct``."""
    return TrackedProduct(
        id=int(row.id),
        product_id=int(row.product_id),
        query_text=str(row.query_text),
        canonical_name=row.canonical_name,
        enabled=bool(row.enabled),
        refresh_interval_hours=row.refresh_interval_hours,
        target_price=row.target_price,
        target_currency=row.target_currency,
        search_scope_tier=str(row.search_scope_tier),
        historical_low_alert_mode=str(row.historical_low_alert_mode),
        rarity_percentile=row.rarity_percentile,
        rarity_window_days=row.rarity_window_days,
        rarity_min_observations=row.rarity_min_observations,
        created_at=row.created_at,
        last_checked_at=row.last_checked_at,
    )


class TrackedProductRepository:
    """Reads/writes the ``tracked_products`` watchlist table."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_or_create(
        self,
        query_text: str,
        *,
        search_scope_tier: str = DEFAULT_SEARCH_SCOPE_TIER,
        historical_low_alert_mode: str = DEFAULT_HISTORICAL_LOW_ALERT_MODE,
    ) -> TrackedProduct:
        """Return the watchlist row for ``query_text``, creating/re-enabling it.

        Re-enables a previously ``untrack``'d entry rather than inserting a
        duplicate. Does not scrape — callers run discovery separately.
        """
        cleaned = " ".join(query_text.split())
        if not cleaned:
            raise ValueError("query_text must not be empty")
        if search_scope_tier not in SEARCH_SCOPE_TIERS:
            raise ValueError(f"unknown search_scope_tier: {search_scope_tier!r}")
        if historical_low_alert_mode not in HISTORICAL_LOW_ALERT_MODES:
            raise ValueError(
                f"unknown historical_low_alert_mode: {historical_low_alert_mode!r}"
            )

        existing = self.get_by_query(cleaned)
        if existing is not None:
            if not existing.enabled or existing.search_scope_tier != search_scope_tier:
                with self.engine.begin() as conn:
                    conn.execute(
                        tracked_products.update()
                        .where(tracked_products.c.id == existing.id)
                        .values(
                            enabled=True,
                            search_scope_tier=search_scope_tier,
                        )
                    )
                refreshed = self.get_by_query(cleaned)
                assert refreshed is not None
                return refreshed
            return existing

        product_id = ProductRepository(self.engine).get_or_create(cleaned)
        now = datetime.now()
        with self.engine.begin() as conn:
            conn.execute(
                tracked_products.insert().values(
                    product_id=product_id,
                    query_text=cleaned,
                    canonical_name=None,
                    enabled=True,
                    refresh_interval_hours=None,
                    target_price=None,
                    target_currency=None,
                    search_scope_tier=search_scope_tier,
                    historical_low_alert_mode=historical_low_alert_mode,
                    rarity_percentile=None,
                    rarity_window_days=None,
                    rarity_min_observations=None,
                    created_at=now,
                    last_checked_at=None,
                )
            )
        created = self.get_by_query(cleaned)
        assert created is not None
        return created

    def get(self, tracked_product_id: int) -> TrackedProduct | None:
        """Return one watchlist row by id, or None."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(tracked_products).where(
                    tracked_products.c.id == tracked_product_id
                )
            ).one_or_none()
        return _row_to_tracked(row) if row is not None else None

    def get_by_query(self, query_text: str) -> TrackedProduct | None:
        """Return the watchlist row for this query text, or None."""
        cleaned = " ".join(query_text.split())
        with self.engine.connect() as conn:
            row = conn.execute(
                select(tracked_products).where(tracked_products.c.query_text == cleaned)
            ).one_or_none()
        return _row_to_tracked(row) if row is not None else None

    def list_all(self, *, enabled_only: bool = False) -> list[TrackedProduct]:
        """Return watchlist entries, most recently created first."""
        stmt = select(tracked_products)
        if enabled_only:
            stmt = stmt.where(tracked_products.c.enabled.is_(True))
        stmt = stmt.order_by(tracked_products.c.created_at.desc())
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [_row_to_tracked(row) for row in rows]

    def set_enabled(self, tracked_product_id: int, enabled: bool) -> None:
        """Enable or disable a watchlist entry without deleting history."""
        with self.engine.begin() as conn:
            conn.execute(
                tracked_products.update()
                .where(tracked_products.c.id == tracked_product_id)
                .values(enabled=enabled)
            )

    def touch_last_checked(
        self, tracked_product_id: int, *, when: datetime | None = None
    ) -> None:
        """Record that this watchlist entry was just refreshed."""
        with self.engine.begin() as conn:
            conn.execute(
                tracked_products.update()
                .where(tracked_products.c.id == tracked_product_id)
                .values(last_checked_at=when or datetime.now())
            )

    def untrack(self, tracked_product_id: int) -> None:
        """Remove a watchlist entry."""
        with self.engine.begin() as conn:
            conn.execute(
                tracked_products.delete().where(
                    tracked_products.c.id == tracked_product_id
                )
            )


class SiteSettingsRepository:
    """Reads/writes ``site_settings``. Missing keys are treated as enabled."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def disabled_keys(self) -> set[str]:
        """Site keys whose persisted global flag is explicitly off."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(site_settings.c.site_key).where(
                    site_settings.c.enabled.is_(False)
                )
            ).all()
        return {str(row.site_key) for row in rows}

    def set_enabled(self, site_key: str, enabled: bool) -> None:
        """Upsert the global enabled flag for ``site_key``."""
        cleaned = site_key.strip()
        if not cleaned:
            raise ValueError("site_key must not be empty")
        stmt = sqlite_insert(site_settings).values(
            site_key=cleaned,
            enabled=enabled,
            result_limit=None,
            min_request_interval_seconds=None,
            cache_ttl_seconds=None,
            browser_rendering_allowed=False,
            min_refresh_interval_hours=None,
            collection_method="server_scrape",
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_key"],
            set_={"enabled": enabled},
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def set_collection_method(self, site_key: str, method: str) -> None:
        """Set the v2.20 collection method for ``site_key``.

        Upserts the row (defaults ``enabled`` to True on first insert, which
        matches the v2.1 "no row = enabled" default; an existing row keeps its
        ``enabled`` flag untouched - only ``collection_method`` is updated).
        Raises ``ValueError`` for an empty site key or an unknown method.
        """
        cleaned = site_key.strip()
        if not cleaned:
            raise ValueError("site_key must not be empty")
        cleaned_method = method.strip()
        if cleaned_method not in COLLECTION_METHODS:
            allowed = ", ".join(sorted(COLLECTION_METHODS))
            raise ValueError(
                f"unknown collection_method {cleaned_method!r} "
                f"(must be one of {allowed})"
            )
        stmt = sqlite_insert(site_settings).values(
            site_key=cleaned,
            enabled=True,
            result_limit=None,
            min_request_interval_seconds=None,
            cache_ttl_seconds=None,
            browser_rendering_allowed=False,
            min_refresh_interval_hours=None,
            collection_method=cleaned_method,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_key"],
            set_={"collection_method": cleaned_method},
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def list_all(self) -> list[SiteSetting]:
        """Every persisted site_settings row (not the full scraper registry)."""
        with self.engine.connect() as conn:
            rows = conn.execute(select(site_settings)).all()
        return [
            SiteSetting(
                site_key=str(row.site_key),
                enabled=bool(row.enabled),
                result_limit=row.result_limit,
                min_request_interval_seconds=row.min_request_interval_seconds,
                cache_ttl_seconds=row.cache_ttl_seconds,
                browser_rendering_allowed=bool(row.browser_rendering_allowed),
                min_refresh_interval_hours=row.min_refresh_interval_hours,
                shipping_cost_estimate_eur=row.shipping_cost_estimate_eur,
                collection_method=str(row.collection_method or "server_scrape"),
            )
            for row in rows
        ]

    def set_shipping_cost_estimate(
        self, site_key: str, amount_eur: float | None
    ) -> None:
        """Set a local shipping estimate, or clear it when checkout is required."""
        cleaned = site_key.strip()
        if not cleaned:
            raise ValueError("site_key must not be empty")
        if amount_eur is not None and amount_eur < 0:
            raise ValueError("shipping cost estimate must not be negative")

        stmt = sqlite_insert(site_settings).values(
            site_key=cleaned,
            enabled=True,
            result_limit=None,
            min_request_interval_seconds=None,
            cache_ttl_seconds=None,
            browser_rendering_allowed=False,
            min_refresh_interval_hours=None,
            shipping_cost_estimate_eur=amount_eur,
            collection_method="server_scrape",
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_key"],
            set_={"shipping_cost_estimate_eur": amount_eur},
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def shipping_cost_estimates(self) -> dict[str, float]:
        """Configured site estimates only; absent values remain unknown."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    site_settings.c.site_key,
                    site_settings.c.shipping_cost_estimate_eur,
                ).where(site_settings.c.shipping_cost_estimate_eur.is_not(None))
            ).all()
        estimates = {
            str(row.site_key): float(row.shipping_cost_estimate_eur) for row in rows
        }
        return estimates

    def non_server_scrape_keys(self) -> set[str]:
        """Site keys whose collection method is anything but ``server_scrape``.

        ``pipeline.discover`` must never server-side scrape these - a site
        flagged ``client_extension`` is collected via the browser extension,
        and ``search_api``/``hint_only`` sites are not server-scraped either.
        A missing ``site_settings`` row means ``server_scrape`` (the default).
        """
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(site_settings.c.site_key).where(
                    site_settings.c.collection_method != "server_scrape"
                )
            ).all()
        return {str(row.site_key) for row in rows}


class SiteOverrideRepository:
    """Per-tracked-product exceptions to global site enablement."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def set_override(
        self,
        tracked_product_id: int,
        site_key: str,
        *,
        included: bool,
        reason: str | None = None,
    ) -> None:
        """Insert or replace the exception for ``(product, site)``."""
        cleaned = site_key.strip()
        if not cleaned:
            raise ValueError("site_key must not be empty")
        note = reason.strip() if reason else None
        stmt = sqlite_insert(tracked_product_site_overrides).values(
            tracked_product_id=tracked_product_id,
            site_key=cleaned,
            included=included,
            reason=note or None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tracked_product_id", "site_key"],
            set_={"included": included, "reason": note},
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def clear_override(self, tracked_product_id: int, site_key: str) -> None:
        """Drop the exception so the product follows the global default again."""
        with self.engine.begin() as conn:
            conn.execute(
                tracked_product_site_overrides.delete().where(
                    tracked_product_site_overrides.c.tracked_product_id
                    == tracked_product_id,
                    tracked_product_site_overrides.c.site_key == site_key.strip(),
                )
            )

    def as_map(self, tracked_product_id: int) -> dict[str, bool]:
        """``site_key -> included`` for one tracked product."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    tracked_product_site_overrides.c.site_key,
                    tracked_product_site_overrides.c.included,
                ).where(
                    tracked_product_site_overrides.c.tracked_product_id
                    == tracked_product_id
                )
            ).all()
        return {str(row.site_key): bool(row.included) for row in rows}

    def list_for(self, tracked_product_id: int) -> list[SiteOverride]:
        """Every stored exception for one tracked product."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(tracked_product_site_overrides).where(
                    tracked_product_site_overrides.c.tracked_product_id
                    == tracked_product_id
                )
            ).all()
        return [
            SiteOverride(
                tracked_product_id=int(row.tracked_product_id),
                site_key=str(row.site_key),
                included=bool(row.included),
                reason=row.reason,
            )
            for row in rows
        ]
