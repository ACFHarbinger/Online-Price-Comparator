"""Tests for persisted v2.18 refresh-cadence forecast context."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine

from forecasting.holt import ForecastPoint, ForecastResult
from storage.forecasts import ForecastSnapshotRepository
from storage.repository import ProductRepository


def test_forecast_snapshot_round_trips_and_replaces(in_memory_engine: Engine) -> None:
    product_id = ProductRepository(in_memory_engine).get_or_create("Forecast product")
    repository = ForecastSnapshotRepository(in_memory_engine)
    trained_at = datetime(2026, 8, 22, 12, 0, 0)
    first = ForecastResult(
        currency="EUR",
        condition="new",
        trained_at=trained_at,
        last_observed_at=trained_at,
        observation_count=8,
        day_count=8,
        horizon_days=14,
        confidence_level=0.80,
        points=(
            ForecastPoint(
                forecast_for=datetime(2026, 8, 23, 0, 0),
                lower_bound=450.0,
                upper_bound=470.0,
            ),
        ),
        unavailable_reason=None,
    )
    repository.save(product_id, first, refreshed_at=trained_at)

    stored = repository.get(product_id)
    assert stored == first

    unavailable = ForecastResult(
        currency="EUR",
        condition=None,
        trained_at=None,
        last_observed_at=None,
        observation_count=0,
        day_count=0,
        horizon_days=14,
        confidence_level=0.80,
        points=(),
        unavailable_reason="need observations with a known condition",
    )
    repository.save(product_id, unavailable, refreshed_at=trained_at)

    assert repository.get(product_id) == unavailable
