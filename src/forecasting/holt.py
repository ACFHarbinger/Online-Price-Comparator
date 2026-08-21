"""A lightweight Holt linear-trend forecast with an 80% uncertainty band.

This module is intentionally read-only decision context. It forecasts a
same-currency observed series and must never feed price ranking, anomaly
detection, historical-low badges, or the descriptive history chart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import sqrt
from statistics import median

from storage.repository import SitePricePoint

MIN_OBSERVATIONS = 8
MIN_TIME_SPAN_DAYS = 21
DEFAULT_HORIZON_DAYS = 14
CONFIDENCE_LEVEL = 0.80
_Z_SCORE_80 = 1.28155
_LEVEL_SMOOTHING = 0.5
_TREND_SMOOTHING = 0.2


@dataclass(frozen=True)
class ForecastPoint:
    """One projected day represented only by its 80% confidence interval."""

    forecast_for: datetime
    lower_bound: float
    upper_bound: float


@dataclass(frozen=True)
class ForecastResult:
    """A read-only forecast result or an explicit insufficient-history status."""

    currency: str | None
    trained_at: datetime | None
    last_observed_at: datetime | None
    observation_count: int
    day_count: int
    horizon_days: int
    confidence_level: float
    points: tuple[ForecastPoint, ...]
    unavailable_reason: str | None

    @property
    def is_available(self) -> bool:
        """Whether this result has a confidence band safe to render."""
        return self.unavailable_reason is None


def _dominant_currency_points(
    points: list[SitePricePoint],
) -> tuple[str | None, list[SitePricePoint]]:
    grouped: dict[str, list[SitePricePoint]] = {}
    for point in points:
        grouped.setdefault(point.currency, []).append(point)
    if not grouped:
        return None, []
    currency, compatible = max(grouped.items(), key=lambda item: len(item[1]))
    return currency, sorted(compatible, key=lambda point: point.observed_at)


def _daily_medians(points: list[SitePricePoint]) -> list[tuple[datetime, float]]:
    daily_prices: dict[datetime, list[float]] = {}
    for point in points:
        day = point.observed_at.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_prices.setdefault(day, []).append(point.price_amount)
    return [
        (day, float(median(prices))) for day, prices in sorted(daily_prices.items())
    ]


def _unavailable(
    *,
    currency: str | None,
    last_observed_at: datetime | None,
    observation_count: int,
    day_count: int,
    horizon_days: int,
    reason: str,
) -> ForecastResult:
    return ForecastResult(
        currency=currency,
        trained_at=None,
        last_observed_at=last_observed_at,
        observation_count=observation_count,
        day_count=day_count,
        horizon_days=horizon_days,
        confidence_level=CONFIDENCE_LEVEL,
        points=(),
        unavailable_reason=reason,
    )


def forecast_prices(
    points: list[SitePricePoint], *, horizon_days: int = DEFAULT_HORIZON_DAYS
) -> ForecastResult:
    """Forecast a same-currency product series with widening 80% intervals.

    The model aggregates same-day retailer observations to their median, then
    applies Holt's linear trend. It deliberately declines to forecast below
    eight observations spanning 21 days, rather than inventing certainty from
    a thin history.
    """
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1")

    currency, compatible = _dominant_currency_points(points)
    last_observed_at = compatible[-1].observed_at if compatible else None
    observation_count = len(compatible)
    daily = _daily_medians(compatible)
    day_count = len(daily)
    if observation_count < MIN_OBSERVATIONS:
        return _unavailable(
            currency=currency,
            last_observed_at=last_observed_at,
            observation_count=observation_count,
            day_count=day_count,
            horizon_days=horizon_days,
            reason=f"need at least {MIN_OBSERVATIONS} compatible observations",
        )
    if day_count < 2:
        return _unavailable(
            currency=currency,
            last_observed_at=last_observed_at,
            observation_count=observation_count,
            day_count=day_count,
            horizon_days=horizon_days,
            reason="need observations on more than one day",
        )

    span_days = (daily[-1][0] - daily[0][0]).days
    if span_days < MIN_TIME_SPAN_DAYS:
        return _unavailable(
            currency=currency,
            last_observed_at=last_observed_at,
            observation_count=observation_count,
            day_count=day_count,
            horizon_days=horizon_days,
            reason=f"need at least {MIN_TIME_SPAN_DAYS} days of history",
        )

    values = [value for _, value in daily]
    level = values[0]
    trend = (values[-1] - values[0]) / max(span_days, 1)
    residuals: list[float] = []
    previous_day = daily[0][0]
    for day, value in daily[1:]:
        elapsed_days = max((day - previous_day).days, 1)
        fitted = level + (trend * elapsed_days)
        residuals.append(value - fitted)
        updated_level = _LEVEL_SMOOTHING * value + (1 - _LEVEL_SMOOTHING) * fitted
        trend = (
            _TREND_SMOOTHING * ((updated_level - level) / elapsed_days)
            + (1 - _TREND_SMOOTHING) * trend
        )
        level = updated_level
        previous_day = day

    residual_scale = sqrt(sum(residual**2 for residual in residuals) / len(residuals))
    floor_scale = max(abs(sum(values) / len(values)) * 0.01, 0.01)
    uncertainty_scale = max(residual_scale, floor_scale)
    final_day = daily[-1][0]
    forecast_points = tuple(
        ForecastPoint(
            forecast_for=final_day + timedelta(days=step),
            lower_bound=max(
                0.0,
                level + (trend * step) - (_Z_SCORE_80 * uncertainty_scale * sqrt(step)),
            ),
            upper_bound=level
            + (trend * step)
            + (_Z_SCORE_80 * uncertainty_scale * sqrt(step)),
        )
        for step in range(1, horizon_days + 1)
    )
    return ForecastResult(
        currency=currency,
        trained_at=last_observed_at,
        last_observed_at=last_observed_at,
        observation_count=observation_count,
        day_count=day_count,
        horizon_days=horizon_days,
        confidence_level=CONFIDENCE_LEVEL,
        points=forecast_points,
        unavailable_reason=None,
    )
