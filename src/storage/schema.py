"""SQLite table definitions (SQLAlchemy Core, no ORM)."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
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
    # v2.11: current-belief condition. Observation-time copies live on
    # price_history so later corrections do not retcon ATL/IQR history.
    # NULL on pre-v2.11 rows; never silently backfilled as verified `new`.
    Column("condition", String, nullable=True),
    Column("condition_source", String, nullable=True),
    Column("condition_confidence", Float, nullable=True),
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
    # Cross-retailer price-outlier flag for this observation (see
    # src/matching/anomaly.py) - flagged, never deleted. Read-side queries
    # exclude is_anomalous=True by default so a bad price never surfaces as
    # "the price" without an explicit reveal.
    Column("is_anomalous", Boolean, nullable=False, default=False),
    Column("anomaly_reason", String, nullable=True),
    Column("anomaly_basis", String, nullable=True),
    # v2.10: native sticker stored alongside a scrape-time EUR equivalent.
    # `price_amount`/`currency` remain the native values (backward compatible).
    # `fx_rate_used` is ECB units of native currency per 1 EUR (1.0 for EUR).
    # Nullable so pre-v2.10 rows stay valid; application code fills them on insert.
    Column("price_native", Float, nullable=True),
    Column("currency_native", String, nullable=True),
    Column("price_eur_equivalent", Float, nullable=True),
    Column("fx_rate_used", Float, nullable=True),
    Column("fx_rate_date", Date, nullable=True),
    # v2.11 observation-time condition snapshot (not current listing belief).
    Column("condition", String, nullable=True),
    Column("condition_source", String, nullable=True),
    Column("condition_confidence", Float, nullable=True),
)

# v2.1 watchlist + per-site enablement. Ad-hoc `products` rows from `search`
# stay as they are; `tracked_products` is the persistent watchlist. Absence
# of a `site_settings` row means the site is enabled. Absence of an override
# row means "follow that global default" — this table stores exceptions only.
tracked_products = Table(
    "tracked_products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("query_text", String, nullable=False),
    Column("canonical_name", String, nullable=True),
    Column("enabled", Boolean, nullable=False, default=True),
    Column("refresh_interval_hours", Integer, nullable=True),
    Column("target_price", Float, nullable=True),
    Column("target_currency", String, nullable=True),
    Column(
        "search_scope_tier",
        String,
        nullable=False,
        default="local",
    ),
    Column(
        "historical_low_alert_mode",
        String,
        nullable=False,
        default="tiered",
    ),
    Column("rarity_percentile", Float, nullable=True),
    Column("rarity_window_days", Integer, nullable=True),
    Column("rarity_min_observations", Integer, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("last_checked_at", DateTime, nullable=True),
    UniqueConstraint("product_id", name="uq_tracked_product_product_id"),
    UniqueConstraint("query_text", name="uq_tracked_product_query_text"),
)

site_settings = Table(
    "site_settings",
    metadata,
    Column("site_key", String, primary_key=True),
    Column("enabled", Boolean, nullable=False, default=True),
    Column("result_limit", Integer, nullable=True),
    Column("min_request_interval_seconds", Float, nullable=True),
    Column("cache_ttl_seconds", Integer, nullable=True),
    Column("browser_rendering_allowed", Boolean, nullable=False, default=False),
    Column("min_refresh_interval_hours", Float, nullable=True),
    # v2.9: optional local-delivery estimate. NULL means unknown, never free.
    # It is a site-level starting point, not a checkout quote or a historical
    # price component, and can be set manually through SiteSettingsRepository.
    Column("shipping_cost_estimate_eur", Float, nullable=True),
    # v2.20: which pipeline path is allowed to touch this site. "server_scrape"
    # (default) is the scrapers/ registry adapter; "client_extension" is the
    # browser extension (no server-side scraping allowed); "search_api" and
    # "hint_only" mirror v2.17a / v2.8. `pipeline.discover` must never fall
    # back to server-side scraping for anything other than "server_scrape".
    Column(
        "collection_method",
        String,
        nullable=False,
        default="server_scrape",
    ),
)

tracked_product_site_overrides = Table(
    "tracked_product_site_overrides",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "tracked_product_id",
        Integer,
        ForeignKey("tracked_products.id"),
        nullable=False,
    ),
    Column("site_key", String, nullable=False),
    Column("included", Boolean, nullable=False),
    Column("reason", String, nullable=True),
    UniqueConstraint(
        "tracked_product_id",
        "site_key",
        name="uq_tracked_product_site_override",
    ),
)

# v2.18 persisted, read-only forecast context. A refresh replaces the one
# product-level snapshot atomically; historical observations remain the source
# of truth in price_history.
forecast_snapshots = Table(
    "forecast_snapshots",
    metadata,
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    Column("currency", String, nullable=True),
    Column("condition", String, nullable=True),
    Column("trained_at", DateTime, nullable=True),
    Column("last_observed_at", DateTime, nullable=True),
    Column("observation_count", Integer, nullable=False),
    Column("day_count", Integer, nullable=False),
    Column("horizon_days", Integer, nullable=False),
    Column("confidence_level", Float, nullable=False),
    Column("points_json", String, nullable=False),
    Column("unavailable_reason", String, nullable=True),
    Column("refreshed_at", DateTime, nullable=False),
)

# v2.3/v2.4 alerting delivery log (see src/alerting/). One row per successful
# channel dispatch. Used both for audit and for the per-product + alert-type
# cooldown, so a crossing below a target notifies once rather than on every
# refresh. This table is additive only (alerting slice) - it does not touch
# `price_history` or the v2.1 watchlist tables.
alert_deliveries = Table(
    "alert_deliveries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "tracked_product_id",
        Integer,
        ForeignKey("tracked_products.id"),
        nullable=False,
    ),
    Column("alert_type", String, nullable=False),
    Column("channel", String, nullable=False),
    Column("message", String, nullable=False),
    Column("related_price", Float, nullable=True),
    Column("target_price", Float, nullable=True),
    Column("site_key", String, nullable=True),
    Column("created_at", DateTime, nullable=False),
)

# v2.17b per-product candidate listings from manual source discovery.
# Survives initial identity matching and is surfaced for user approval
# before being promoted to persistent tracked sources.
candidate_listings = Table(
    "candidate_listings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "tracked_product_id",
        Integer,
        ForeignKey("tracked_products.id"),
        nullable=False,
    ),
    Column("site_key", String, nullable=False),
    Column("site_display_name", String, nullable=False),
    Column("url", String, nullable=False),
    Column("title", String, nullable=False),
    Column("price_amount", Float, nullable=True),
    Column("currency", String, nullable=False, default="EUR"),
    Column("image_url", String, nullable=True),
    Column("match_status", String, nullable=False),
    Column("match_score", Float, nullable=True),
    Column(
        "status", String, nullable=False, default="pending"
    ),  # pending, approved, rejected, expired
    Column("discovered_at", DateTime, nullable=False),
    Column("expires_at", DateTime, nullable=False),
    Column("decided_at", DateTime, nullable=True),
    UniqueConstraint(
        "tracked_product_id",
        "url",
        name="uq_candidate_listing",
    ),
)

# v2.15 custom listing URLs (Tier A). Exact product-page URLs added
# directly by the user against a tracked product.
custom_listing_urls = Table(
    "custom_listing_urls",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "tracked_product_id",
        Integer,
        ForeignKey("tracked_products.id"),
        nullable=False,
    ),
    Column("url", String, nullable=False),
    Column("site_key", String, nullable=False),
    Column("site_display_name", String, nullable=False),
    Column("parser_confidence", Float, nullable=True),
    Column("status", String, nullable=False, default="active"),
    Column("last_checked_at", DateTime, nullable=True),
    Column("last_error", String, nullable=True),
    Column("added_at", DateTime, nullable=False),
    UniqueConstraint(
        "tracked_product_id",
        "url",
        name="uq_custom_listing_url",
    ),
)
