"""Thin repository layer wrapping SQLAlchemy Core queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from models.product import Product
from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from storage.schema import listings, price_history, products

# Listings with any other match_status ("review"/"rejected") are kept in
# the DB for audit/debugging but never surfaced by the read methods below -
# see src/matching/ for how a listing's status is decided.
MATCHED_STATUSES = ("confirmed", "likely")


@dataclass(frozen=True)
class SitePricePoint:
    """One price observation for a site, used by both dashboard charts."""

    site_key: str
    site_display_name: str
    price_amount: float
    currency: str
    observed_at: datetime


@dataclass(frozen=True)
class ListingSummary:
    """A listing plus its most recent price, for the dashboard links panel."""

    site_key: str
    site_display_name: str
    url: str
    image_url: str | None
    price_amount: float | None
    currency: str | None
    observed_at: datetime | None


class ProductRepository:
    """Reads/writes the `products` table."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get_or_create(self, query_text: str) -> int:
        """Return the id of the product matching `query_text`, creating it if absent."""
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(products.c.id).where(products.c.query_text == query_text)
            ).scalar_one_or_none()
            if existing is not None:
                return int(existing)
            result = conn.execute(
                products.insert().values(
                    query_text=query_text,
                    canonical_name=None,
                    created_at=datetime.now(),
                )
            )
            inserted_id = result.inserted_primary_key
            assert inserted_id is not None
            return int(inserted_id[0])

    def get(self, product_id: int) -> Product | None:
        """Return the product with `product_id`, or None if it doesn't exist."""
        with self.engine.connect() as conn:
            row = conn.execute(
                select(
                    products.c.id,
                    products.c.query_text,
                    products.c.canonical_name,
                    products.c.created_at,
                ).where(products.c.id == product_id)
            ).one_or_none()
        if row is None:
            return None
        return Product(
            id=row.id,
            query_text=row.query_text,
            canonical_name=row.canonical_name,
            created_at=row.created_at,
        )

    def list_products(self) -> list[Product]:
        """Return every tracked product, most recently created first."""
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(
                    products.c.id,
                    products.c.query_text,
                    products.c.canonical_name,
                    products.c.created_at,
                ).order_by(products.c.created_at.desc())
            ).all()
        return [
            Product(
                id=row.id,
                query_text=row.query_text,
                canonical_name=row.canonical_name,
                created_at=row.created_at,
            )
            for row in rows
        ]


class ListingRepository:
    """Reads/writes the `listings` table."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def upsert(
        self,
        *,
        product_id: int,
        site_key: str,
        site_display_name: str,
        url: str,
        image_url: str | None,
        seen_at: datetime,
        match_status: str,
        match_score: float | None,
        match_reason: str | None,
    ) -> int:
        """Insert a listing, or refresh it (incl. its match verdict) if it exists.

        The match verdict is re-evaluated and overwritten on every upsert
        (not just set once) since a re-run's matching logic/title may
        change the correct verdict for the same URL over time.
        """
        with self.engine.begin() as conn:
            stmt = sqlite_insert(listings).values(
                product_id=product_id,
                site_key=site_key,
                site_display_name=site_display_name,
                url=url,
                image_url=image_url,
                first_seen_at=seen_at,
                last_seen_at=seen_at,
                match_status=match_status,
                match_score=match_score,
                match_reason=match_reason,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["product_id", "site_key", "url"],
                set_={
                    "last_seen_at": seen_at,
                    "image_url": image_url,
                    "match_status": match_status,
                    "match_score": match_score,
                    "match_reason": match_reason,
                },
            )
            conn.execute(stmt)
            listing_id = conn.execute(
                select(listings.c.id).where(
                    listings.c.product_id == product_id,
                    listings.c.site_key == site_key,
                    listings.c.url == url,
                )
            ).scalar_one()
            return int(listing_id)

    def list_with_latest_price(
        self, product_id: int, *, include_anomalous: bool = False
    ) -> list[ListingSummary]:
        """Every listing for a product plus its most recent price, for the links panel.

        Left-joined so a listing with no parseable price observation yet still
        appears (with `price_amount`/`currency`/`observed_at` as None) rather
        than being silently dropped.
        """
        anomalous_filter = (
            () if include_anomalous else (price_history.c.is_anomalous.is_(False),)
        )
        latest_per_listing = (
            select(
                price_history.c.listing_id,
                func.max(price_history.c.observed_at).label("max_observed_at"),
            )
            .where(*anomalous_filter)
            .group_by(price_history.c.listing_id)
            .subquery()
        )
        latest_price = (
            select(
                price_history.c.listing_id,
                price_history.c.price_amount,
                price_history.c.currency,
                price_history.c.observed_at,
            )
            .where(*anomalous_filter)
            .join(
                latest_per_listing,
                (price_history.c.listing_id == latest_per_listing.c.listing_id)
                & (price_history.c.observed_at == latest_per_listing.c.max_observed_at),
            )
            .subquery()
        )
        stmt = (
            select(
                listings.c.site_key,
                listings.c.site_display_name,
                listings.c.url,
                listings.c.image_url,
                latest_price.c.price_amount,
                latest_price.c.currency,
                latest_price.c.observed_at,
            )
            .select_from(listings)
            .outerjoin(latest_price, latest_price.c.listing_id == listings.c.id)
            .where(
                listings.c.product_id == product_id,
                listings.c.match_status.in_(MATCHED_STATUSES),
            )
            .order_by(
                latest_price.c.price_amount.is_(None), latest_price.c.price_amount
            )
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [
            ListingSummary(
                site_key=row.site_key,
                site_display_name=row.site_display_name,
                url=row.url,
                image_url=row.image_url,
                price_amount=row.price_amount,
                currency=row.currency,
                observed_at=row.observed_at,
            )
            for row in rows
        ]


@dataclass(frozen=True)
class ProductPriceStats:
    """Summary price metrics across all confirmed listings for a product."""

    all_time_low: float | None
    all_time_low_currency: str | None
    avg_30d: float | None
    avg_30d_currency: str | None


class PriceHistoryRepository:
    """Reads/writes the `price_history` table."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def add(
        self,
        *,
        listing_id: int,
        price_amount: float,
        currency: str,
        observed_at: datetime,
        raw_price_text: str | None,
        is_anomalous: bool = False,
        anomaly_reason: str | None = None,
        anomaly_basis: str | None = None,
    ) -> None:
        """Append a new price observation for a listing."""
        with self.engine.begin() as conn:
            conn.execute(
                price_history.insert().values(
                    listing_id=listing_id,
                    price_amount=price_amount,
                    currency=currency,
                    observed_at=observed_at,
                    raw_price_text=raw_price_text,
                    is_anomalous=is_anomalous,
                    anomaly_reason=anomaly_reason,
                    anomaly_basis=anomaly_basis,
                )
            )

    def latest_prices_by_site(
        self, product_id: int, *, include_anomalous: bool = False
    ) -> list[SitePricePoint]:
        """One row per site: its most recent observed price.

        Drives the snapshot chart. When `include_anomalous` is False (default),
        anomalous observations are excluded entirely. When True, anomalous
        observations are included.
        """
        anomalous_filter = (
            () if include_anomalous else (price_history.c.is_anomalous.is_(False),)
        )
        latest_per_listing = (
            select(
                price_history.c.listing_id,
                func.max(price_history.c.observed_at).label("max_observed_at"),
            )
            .where(*anomalous_filter)
            .group_by(price_history.c.listing_id)
            .subquery()
        )
        stmt = (
            select(
                listings.c.site_key,
                listings.c.site_display_name,
                price_history.c.price_amount,
                price_history.c.currency,
                price_history.c.observed_at,
            )
            .join(listings, listings.c.id == price_history.c.listing_id)
            .join(
                latest_per_listing,
                (price_history.c.listing_id == latest_per_listing.c.listing_id)
                & (price_history.c.observed_at == latest_per_listing.c.max_observed_at),
            )
            .where(
                listings.c.product_id == product_id,
                listings.c.match_status.in_(MATCHED_STATUSES),
                *anomalous_filter,
            )
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [
            SitePricePoint(
                site_key=row.site_key,
                site_display_name=row.site_display_name,
                price_amount=row.price_amount,
                currency=row.currency,
                observed_at=row.observed_at,
            )
            for row in rows
        ]

    def price_history_by_site(
        self, product_id: int, *, include_anomalous: bool = False
    ) -> list[SitePricePoint]:
        """Full price history for a product, ordered by time.

        Drives the trend chart. When `include_anomalous` is False (default),
        anomalous points are dropped from the series. When True, they are included.
        """
        anomalous_filter = (
            () if include_anomalous else (price_history.c.is_anomalous.is_(False),)
        )
        stmt = (
            select(
                listings.c.site_key,
                listings.c.site_display_name,
                price_history.c.price_amount,
                price_history.c.currency,
                price_history.c.observed_at,
            )
            .join(listings, listings.c.id == price_history.c.listing_id)
            .where(
                listings.c.product_id == product_id,
                listings.c.match_status.in_(MATCHED_STATUSES),
                *anomalous_filter,
            )
            .order_by(price_history.c.observed_at)
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [
            SitePricePoint(
                site_key=row.site_key,
                site_display_name=row.site_display_name,
                price_amount=row.price_amount,
                currency=row.currency,
                observed_at=row.observed_at,
            )
            for row in rows
        ]

    def product_price_stats(
        self,
        product_id: int,
        *,
        as_of: datetime | None = None,
        include_anomalous: bool = False,
    ) -> ProductPriceStats:
        """Return all-time low price and 30-day average price for a product.

        Calculated across matched listings. When `include_anomalous` is False
        (default), anomalous price observations are excluded.
        """
        reference_time = as_of or datetime.now()
        thirty_days_ago = reference_time - timedelta(days=30)

        anomalous_filter = (
            () if include_anomalous else (price_history.c.is_anomalous.is_(False),)
        )

        atl_stmt = (
            select(
                price_history.c.price_amount,
                price_history.c.currency,
            )
            .join(listings, listings.c.id == price_history.c.listing_id)
            .where(
                listings.c.product_id == product_id,
                listings.c.match_status.in_(MATCHED_STATUSES),
                *anomalous_filter,
            )
            .order_by(price_history.c.price_amount.asc())
            .limit(1)
        )

        avg_stmt = (
            select(
                func.avg(price_history.c.price_amount).label("avg_price"),
                price_history.c.currency,
            )
            .join(listings, listings.c.id == price_history.c.listing_id)
            .where(
                listings.c.product_id == product_id,
                listings.c.match_status.in_(MATCHED_STATUSES),
                price_history.c.observed_at >= thirty_days_ago,
                price_history.c.observed_at <= reference_time,
                *anomalous_filter,
            )
            .group_by(price_history.c.currency)
            .order_by(func.count(price_history.c.id).desc())
            .limit(1)
        )

        with self.engine.connect() as conn:
            atl_row = conn.execute(atl_stmt).one_or_none()
            avg_row = conn.execute(avg_stmt).one_or_none()

        atl_price = float(atl_row.price_amount) if atl_row is not None else None
        atl_currency = str(atl_row.currency) if atl_row is not None else None

        avg_price = (
            float(avg_row.avg_price)
            if avg_row is not None and avg_row.avg_price is not None
            else None
        )
        avg_currency = str(avg_row.currency) if avg_row is not None else None

        return ProductPriceStats(
            all_time_low=atl_price,
            all_time_low_currency=atl_currency,
            avg_30d=avg_price,
            avg_30d_currency=avg_currency,
        )
