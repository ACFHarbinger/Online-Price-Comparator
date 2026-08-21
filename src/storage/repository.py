"""Thin repository layer wrapping SQLAlchemy Core queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import sqrt

from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from models.product import Product
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
class PriceVolatilityStats:
    """Price volatility (variance / coefficient of variation) over a rolling window."""

    window_days: int
    sample_size: int
    mean_price: float | None
    stdev_price: float | None
    cv_percent: float | None
    currency: str | None
    description: str
    is_sparse: bool


@dataclass(frozen=True)
class PriceTrendStats:
    """Descriptive linear trend/gradient over a rolling window.

    This is an empirical descriptive statistic about observed price history only,
    never a prediction or forecast.
    """

    window_days: int
    sample_size: int
    slope_per_day: float | None
    slope_per_week: float | None
    pct_per_week: float | None
    currency: str | None
    direction: str  # "down", "up", "flat", "sparse"
    description: str
    is_sparse: bool


def compute_price_volatility(
    observations: list[tuple[datetime, float, str]],
    *,
    window_days: int = 90,
    min_observations: int = 4,
) -> PriceVolatilityStats:
    """Compute coefficient of variation (stdev / mean) for price observations."""
    if len(observations) < min_observations:
        curr = observations[0][2] if observations else None
        return PriceVolatilityStats(
            window_days=window_days,
            sample_size=len(observations),
            mean_price=None,
            stdev_price=None,
            cv_percent=None,
            currency=curr,
            description="not enough history yet",
            is_sparse=True,
        )

    prices = [p for _, p, _ in observations]
    currencies = [c for _, _, c in observations]
    curr = currencies[0] if currencies else "EUR"
    n = len(prices)
    mean_val = sum(prices) / n

    if mean_val <= 0:
        return PriceVolatilityStats(
            window_days=window_days,
            sample_size=n,
            mean_price=mean_val,
            stdev_price=0.0,
            cv_percent=0.0,
            currency=curr,
            description=f"±0.0% ({window_days}d vol)",
            is_sparse=False,
        )

    variance = sum((p - mean_val) ** 2 for p in prices) / (n - 1)
    stdev_val = sqrt(variance)
    cv_pct = (stdev_val / mean_val) * 100.0

    return PriceVolatilityStats(
        window_days=window_days,
        sample_size=n,
        mean_price=mean_val,
        stdev_price=stdev_val,
        cv_percent=cv_pct,
        currency=curr,
        description=f"±{cv_pct:.1f}% ({window_days}d vol)",
        is_sparse=False,
    )


def compute_price_trend(
    observations: list[tuple[datetime, float, str]],
    *,
    window_days: int = 30,
    min_observations: int = 4,
    min_time_span_days: float = 2.0,
) -> PriceTrendStats:
    """Compute empirical linear regression slope over time.

    Descriptive statistic of past observations only - never a prediction.
    """
    if len(observations) < min_observations:
        curr = observations[0][2] if observations else None
        return PriceTrendStats(
            window_days=window_days,
            sample_size=len(observations),
            slope_per_day=None,
            slope_per_week=None,
            pct_per_week=None,
            currency=curr,
            direction="sparse",
            description="not enough history yet",
            is_sparse=True,
        )

    sorted_obs = sorted(observations, key=lambda x: x[0])
    t0 = sorted_obs[0][0]
    tn = sorted_obs[-1][0]
    time_span_days = (tn - t0).total_seconds() / 86400.0

    if time_span_days < min_time_span_days:
        curr = sorted_obs[0][2]
        return PriceTrendStats(
            window_days=window_days,
            sample_size=len(sorted_obs),
            slope_per_day=None,
            slope_per_week=None,
            pct_per_week=None,
            currency=curr,
            direction="sparse",
            description="not enough history yet",
            is_sparse=True,
        )

    t_vals = [(obs[0] - t0).total_seconds() / 86400.0 for obs in sorted_obs]
    p_vals = [obs[1] for obs in sorted_obs]
    curr = sorted_obs[0][2]

    n = len(t_vals)
    t_mean = sum(t_vals) / n
    p_mean = sum(p_vals) / n

    ss_tt = sum((t - t_mean) ** 2 for t in t_vals)
    if ss_tt == 0:
        return PriceTrendStats(
            window_days=window_days,
            sample_size=n,
            slope_per_day=0.0,
            slope_per_week=0.0,
            pct_per_week=0.0,
            currency=curr,
            direction="flat",
            description=f"→ {curr} 0.00/wk (0.0%/wk)",
            is_sparse=False,
        )

    ss_tp = sum((t_vals[i] - t_mean) * (p_vals[i] - p_mean) for i in range(n))
    slope_day = ss_tp / ss_tt
    slope_week = slope_day * 7.0
    pct_week = (slope_week / p_mean * 100.0) if p_mean > 0 else 0.0

    if pct_week < -0.05:
        direction = "down"
        arrow = "↘"
        sign = "-"
        rate_str = f"{abs(slope_week):,.2f}"
        pct_str = f"{sign}{abs(pct_week):.1f}%"
        desc = f"{arrow} -{curr} {rate_str}/wk ({pct_str}/wk)"
    elif pct_week > 0.05:
        direction = "up"
        arrow = "↗"
        sign = "+"
        rate_str = f"{abs(slope_week):,.2f}"
        pct_str = f"{sign}{abs(pct_week):.1f}%"
        desc = f"{arrow} +{curr} {rate_str}/wk ({pct_str}/wk)"
    else:
        direction = "flat"
        arrow = "→"
        desc = f"{arrow} {curr} 0.00/wk (0.0%/wk)"

    return PriceTrendStats(
        window_days=window_days,
        sample_size=n,
        slope_per_day=slope_day,
        slope_per_week=slope_week,
        pct_per_week=pct_week,
        currency=curr,
        direction=direction,
        description=desc,
        is_sparse=False,
    )


@dataclass(frozen=True)
class ProductPriceStats:
    """Summary price metrics across all confirmed listings for a product."""

    all_time_low: float | None
    all_time_low_currency: str | None
    avg_30d: float | None
    avg_30d_currency: str | None
    volatility_90d: PriceVolatilityStats | None = None
    trend_30d: PriceTrendStats | None = None


@dataclass(frozen=True)
class PriceSeriesStatistics:
    """Descriptive statistics for a product's compatible recent price series."""

    window_days: int
    observation_count: int
    currency: str | None
    volatility_pct: float | None
    trend_per_week: float | None


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

        # Compute 90-day volatility and 30-day descriptive trend
        history_points = self.price_history_by_site(
            product_id, include_anomalous=include_anomalous
        )
        ninety_days_ago = reference_time - timedelta(days=90)

        obs_90d = [
            (p.observed_at, p.price_amount, p.currency)
            for p in history_points
            if ninety_days_ago <= p.observed_at <= reference_time
        ]
        obs_30d = [
            (p.observed_at, p.price_amount, p.currency)
            for p in history_points
            if thirty_days_ago <= p.observed_at <= reference_time
        ]

        volatility_90d = compute_price_volatility(obs_90d, window_days=90)
        trend_30d = compute_price_trend(obs_30d, window_days=30)

        return ProductPriceStats(
            all_time_low=atl_price,
            all_time_low_currency=atl_currency,
            avg_30d=avg_price,
            avg_30d_currency=avg_currency,
            volatility_90d=volatility_90d,
            trend_30d=trend_30d,
        )

    def product_price_series_statistics(
        self,
        product_id: int,
        *,
        window_days: int = 30,
        as_of: datetime | None = None,
        include_anomalous: bool = False,
    ) -> PriceSeriesStatistics:
        """Return aggregate volatility and observed linear trend for recent prices.

        Values are calculated only from the most-observed currency in the selected
        window. This avoids implying that native-currency values are comparable
        before v2.10's FX-normalized storage lands. Fewer than four compatible
        observations deliberately produces no statistical values.
        """
        reference_time = as_of or datetime.now()
        start_time = reference_time - timedelta(days=window_days)
        points = [
            point
            for point in self.price_history_by_site(
                product_id, include_anomalous=include_anomalous
            )
            if start_time <= point.observed_at <= reference_time
        ]
        by_currency: dict[str, list[SitePricePoint]] = {}
        for point in points:
            by_currency.setdefault(point.currency, []).append(point)

        if not by_currency:
            return PriceSeriesStatistics(window_days, 0, None, None, None)

        currency, compatible_points = max(
            by_currency.items(), key=lambda item: len(item[1])
        )
        observation_count = len(compatible_points)
        if observation_count < 4:
            return PriceSeriesStatistics(
                window_days, observation_count, currency, None, None
            )

        prices = [point.price_amount for point in compatible_points]
        mean_price = sum(prices) / observation_count
        variance = (
            sum((price - mean_price) ** 2 for price in prices) / observation_count
        )
        volatility_pct = (sqrt(variance) / mean_price) * 100 if mean_price > 0 else None

        first_observed_at = min(point.observed_at for point in compatible_points)
        days = [
            (point.observed_at - first_observed_at).total_seconds() / 86_400
            for point in compatible_points
        ]
        mean_day = sum(days) / observation_count
        denominator = sum((day - mean_day) ** 2 for day in days)
        trend_per_week = None
        if denominator > 0:
            numerator = sum(
                (day - mean_day) * (price - mean_price)
                for day, price in zip(days, prices, strict=True)
            )
            trend_per_week = (numerator / denominator) * 7

        return PriceSeriesStatistics(
            window_days,
            observation_count,
            currency,
            volatility_pct,
            trend_per_week,
        )
