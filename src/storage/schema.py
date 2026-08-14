"""SQLite table definitions (SQLAlchemy Core, no ORM)."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

metadata = MetaData()

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("query_text", String, nullable=False),
    Column("canonical_name", String, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

listings = Table(
    "listings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("site_key", String, nullable=False),
    Column("site_display_name", String, nullable=False),
    Column("url", String, nullable=False),
    Column("image_url", String, nullable=True),
    Column("first_seen_at", DateTime, nullable=False),
    Column("last_seen_at", DateTime, nullable=False),
    # Product-identity match verdict (see src/matching/) for this listing's
    # title against the product it was found for. Only "confirmed"/"likely"
    # listings are surfaced by the read-side repository methods below -
    # "review"/"rejected" rows are kept for audit/debugging, never silently
    # dropped, but never shown as if they were trustworthy price data.
    Column("match_status", String, nullable=False),
    Column("match_score", Float, nullable=True),
    Column("match_reason", String, nullable=True),
    UniqueConstraint("product_id", "site_key", "url", name="uq_listing_identity"),
)

price_history = Table(
    "price_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("listing_id", Integer, ForeignKey("listings.id"), nullable=False),
    Column("price_amount", Float, nullable=False),
    Column("currency", String, nullable=False, default="EUR"),
    Column("observed_at", DateTime, nullable=False),
    Column("raw_price_text", String, nullable=True),
)
