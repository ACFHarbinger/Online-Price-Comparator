"""Tests for the read-only Holt confidence-band forecast."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from forecasting.holt import (
    DEFAULT_HORIZON_DAYS,
    MIN_OBSERVATIONS,
    MIN_TIME_SPAN_DAYS,
    forecast_prices,
)
from storage.repository import SitePricePoint


def _point(day: int, price: float, currency: str = "EUR") -> SitePricePoint:
    return SitePricePoint(
        site_key="amazon.es",
        site_display_name="Amazon.es",
        price_amount=price,
        currency=currency,
        observed_at=datetime(2026, 1, 1) + timedelta(days=day),
    )


def test_forecast_refuses_sparse_history() -> None:
    result = forecast_prices([_point(day, 500.0 - day) for day in range(7)])

    assert result.is_available is False
    assert result.points == ()
    assert result.unavailable_reason == (
        f"need at least {MIN_OBSERVATIONS} compatible observations"
    )


def test_forecast_refuses_history_with_insufficient_time_span() -> None:
    result = forecast_prices([_point(day, 500.0 - day) for day in range(8)])

    assert result.is_available is False
    assert result.unavailable_reason == (
        f"need at least {MIN_TIME_SPAN_DAYS} days of history"
    )


def test_forecast_returns_widening_confidence_band_for_dominant_currency() -> None:
    euro_points = [_point(day * 3, 500.0 - (day * 3)) for day in range(8)]
    points = [*euro_points, _point(30, 999.0, "USD")]

    result = forecast_prices(points)

    assert result.is_available is True
    assert result.currency == "EUR"
    assert result.observation_count == 8
    assert len(result.points) == DEFAULT_HORIZON_DAYS
    assert result.points[0].lower_bound < result.points[0].upper_bound
    first_width = result.points[0].upper_bound - result.points[0].lower_bound
    last_width = result.points[-1].upper_bound - result.points[-1].lower_bound
    assert last_width > first_width
    assert result.points[0].forecast_for > euro_points[-1].observed_at


def test_forecast_rejects_invalid_horizon() -> None:
    with pytest.raises(ValueError, match="horizon_days"):
        forecast_prices([], horizon_days=0)
