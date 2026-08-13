"""Thin repository layer wrapping SQLAlchemy Core queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from models.product import Product
from storage.schema import listings, price_history, products


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
    ) -> int:
        """Insert a listing, or update its `last_seen_at`/image if it already exists."""
        with self.engine.begin() as conn:
            stmt = sqlite_insert(listings).values(
                product_id=product_id,
                site_key=site_key,
                site_display_name=site_display_name,
                url=url,
                image_url=image_url,
                first_seen_at=seen_at,
                last_seen_at=seen_at,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["product_id", "site_key", "url"],
                set_={"last_seen_at": seen_at, "image_url": image_url},
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

    def list_with_latest_price(self, product_id: int) -> list[ListingSummary]:
        """Every listing for a product plus its most recent price, for the links panel.

        Left-joined so a listing with no parseable price observation yet still
        appears (with `price_amount`/`currency`/`observed_at` as None) rather
        than being silently dropped.
        """
        latest_per_listing = (
            select(
                price_history.c.listing_id,
                func.max(price_history.c.observed_at).label("max_observed_at"),
            )
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
            .where(listings.c.product_id == product_id)
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
                )
            )

    def latest_prices_by_site(self, product_id: int) -> list[SitePricePoint]:
        """One row per site: its most recent observed price, for the snapshot chart."""
        latest_per_listing = (
            select(
                price_history.c.listing_id,
                func.max(price_history.c.observed_at).label("max_observed_at"),
            )
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
            .where(listings.c.product_id == product_id)
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

    def price_history_by_site(self, product_id: int) -> list[SitePricePoint]:
        """Full price history for a product, ordered by time. Drives the trend chart."""
        stmt = (
            select(
                listings.c.site_key,
                listings.c.site_display_name,
                price_history.c.price_amount,
                price_history.c.currency,
                price_history.c.observed_at,
            )
            .join(listings, listings.c.id == price_history.c.listing_id)
            .where(listings.c.product_id == product_id)
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
