"""Descriptive statistical descriptors over a product's observed price series.

These are statistics *about observed history* (volatility and short-range
trend/gradient). They are deliberately **not** forecasts: they never claim to
predict a future price. Price forecasting lives in its own separate surface
with an explicit confidence band - see
``docs/moon/roadmaps/price_forecasting.md`` (v2.18). This module ships as part
of the descriptive visualization work (v2.19) and is the **single** home for
this statistical math - the storage layer stays a thin query layer and must not
reach into stdlib statistics.

The population used here mirrors the rest of the product: the same confirmed /
non-anomalous matched listings the anomaly detector and historical-low badges
already run over. Never mix populations across features.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median, pstdev

from storage.repository import SitePricePoint

#: Fewer observations than this yields a statistically meaningless value for
#: either indicator. Mirrors the anomaly detector's own sparse-bucket
#: discipline. Callers should render "not enough history yet" instead of a
#: number.
MIN_OBSERVATIONS = 3

#: The 30d/90d/180d/365d windows reused from v2.14's tiered ladder so the
#: volatility indicator stays on a consistent mental model with the badges.
VOLATILITY_WINDOWS: tuple[int, ...] = (30, 90, 180, 365)
#: The 7d/30d rolling regression windows for the trend/gradient indicator.
TREND_WINDOWS: tuple[int, ...] = (7, 30)

DEFAULT_VOLATILITY_WINDOW_DAYS = 90
DEFAULT_TREND_WINDOW_DAYS = 30


@dataclass(frozen=True)
class PriceSeriesStats:
    """Volatility and trend descriptors for a single price window.

    All ratio/percentage fields are expressed as fractions (0.06 == 6%).
    Absolute slopes carry the currency of the underlying observations;
    the percentage slope is unitless (relative to the window mean). Fields are
    ``None`` where there were too few points to compute a meaningful value, so
    the caller can render "not enough history yet".
    """

    window_days: int
    count: int
    coefficient_of_variation: float | None  # population stdev / mean
    iqr_pct_of_median: float | None  # (q3 - q1) / median
    trend_per_day: float | None  # absolute least-squares slope, per day
    trend_per_week: float | None  # absolute least-squares slope, per week
    trend_pct_per_week: float | None  # trend_per_week / mean
    currency: str | None


def _percentile(sorted_values: Sequence[float], fraction: float) -> float:
    """Linear-interpolation percentile (matches numpy's default method)."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    position = fraction * (n - 1)
    lower = int(position)
    upper = min(lower + 1, n - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def coefficient_of_variation(values: Sequence[float]) -> float | None:
    """Population coefficient of variation (``stdev / mean``).

    Returns ``None`` when there are too few points or a zero mean (so the
    ratio is undefined), rather than a meaningless number.
    """
    if len(values) < MIN_OBSERVATIONS:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    return pstdev(values) / mean


def iqr_percent_of_median(values: Sequence[float]) -> float | None:
    """Interquartile range as a fraction of the median.

    Returns ``None`` when there are too few points or a zero median.
    """
    if len(values) < MIN_OBSERVATIONS:
        return None
    ordered = sorted(values)
    q1 = _percentile(ordered, 0.25)
    q3 = _percentile(ordered, 0.75)
    center = median(ordered)
    if center == 0:
        return None
    return (q3 - q1) / center


def linear_regression_slope(
    points: Sequence[tuple[datetime, float]],
) -> float | None:
    """Least-squares slope of price vs. time, expressed per day.

    ``points`` must be ``(observed_at, price_amount)`` pairs. Returns ``None``
    when there are too few points or all timestamps are identical (undefined
    regression).
    """
    if len(points) < MIN_OBSERVATIONS:
        return None
    reference = points[0][0]
    x_seconds = [(observed_at - reference).total_seconds() for observed_at, _ in points]
    y_values = [price for _, price in points]
    n = len(x_seconds)
    sum_x = sum(x_seconds)
    sum_y = sum(y_values)
    sum_x2 = sum(x * x for x in x_seconds)
    sum_xy = sum(x * y for x, y in zip(x_seconds, y_values, strict=True))
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return None
    slope_per_second = (n * sum_xy - sum_x * sum_y) / denominator
    return slope_per_second * 86_400


def _dominant_currency_points(
    points: Sequence[SitePricePoint],
) -> tuple[str | None, list[SitePricePoint]]:
    """Pick the most-observed currency's points.

    Native-currency values are not comparable until v2.10's FX-normalized
    storage lands, so the descriptors are computed over a single currency's
    population rather than silently pooling EUR/data across regimes.
    """
    if not points:
        return None, []
    grouped: dict[str, list[SitePricePoint]] = {}
    for point in points:
        grouped.setdefault(point.currency, []).append(point)
    currency, compatible = max(grouped.items(), key=lambda item: len(item[1]))
    compatible = sorted(compatible, key=lambda point: point.observed_at)
    return currency, compatible


def compute_price_stats(
    points: Sequence[SitePricePoint],
    *,
    window_days: int,
    reference: datetime | None = None,
    min_observations: int = MIN_OBSERVATIONS,
) -> PriceSeriesStats:
    """Compute volatility + trend descriptors over a rolling price window.

    Points are pooled across confirmed listings for a product, then restricted
    to the single most-observed currency (never pooled across currencies). The
    window is ``[reference - window_days, reference]``. When fewer than
    ``min_observations`` points fall in the window, every indicator is
    ``None`` so the caller can render "not enough history yet".
    """
    ref = reference or datetime.now()
    cutoff = ref - timedelta(days=window_days)
    window = [point for point in points if cutoff <= point.observed_at <= ref]
    currency, compatible = _dominant_currency_points(window)
    prices = [point.price_amount for point in compatible]
    count = len(prices)
    if count < min_observations:
        return PriceSeriesStats(
            window_days=window_days,
            count=count,
            coefficient_of_variation=None,
            iqr_pct_of_median=None,
            trend_per_day=None,
            trend_per_week=None,
            trend_pct_per_week=None,
            currency=currency,
        )

    mean = sum(prices) / count
    cv = coefficient_of_variation(prices)
    iqr = iqr_percent_of_median(prices)
    slope_per_day = linear_regression_slope(
        [(point.observed_at, point.price_amount) for point in compatible]
    )
    trend_per_week: float | None = None
    trend_pct_per_week: float | None = None
    if slope_per_day is not None:
        trend_per_week = slope_per_day * 7
        if mean != 0:
            trend_pct_per_week = trend_per_week / mean

    return PriceSeriesStats(
        window_days=window_days,
        count=count,
        coefficient_of_variation=cv,
        iqr_pct_of_median=iqr,
        trend_per_day=slope_per_day,
        trend_per_week=trend_per_week,
        trend_pct_per_week=trend_pct_per_week,
        currency=currency,
    )
