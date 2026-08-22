"""Refresh-cadence training for persisted v2.18 forecast context."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Engine

from alerting.observations import ListingHistory, listing_histories_for_product
from forecasting.holt import EurPricePoint, ForecastResult, forecast_eur_prices
from storage.forecasts import ForecastSnapshotRepository


def forecast_for_histories(histories: Sequence[ListingHistory]) -> ForecastResult:
    """Train from persisted EUR observations, choosing one known condition."""
    points = [
        EurPricePoint(
            observed_at=observation.observed_at,
            eur_amount=observation.eur_amount,
            condition=observation.condition,
        )
        for history in histories
        for observation in history.observations
    ]
    known_conditions = [
        point.condition
        for point in points
        if point.condition not in (None, "", "unknown")
    ]
    condition = (
        Counter(known_conditions).most_common(1)[0][0] if known_conditions else None
    )
    return forecast_eur_prices(points, condition=condition)


def forecast_for_refresh(engine: Engine, product_id: int) -> ForecastResult:
    """Train and save the current product forecast from persisted EUR history."""
    forecast = forecast_for_histories(listing_histories_for_product(engine, product_id))
    ForecastSnapshotRepository(engine).save(
        product_id, forecast, refreshed_at=datetime.now()
    )
    return forecast


def untrained_forecast() -> ForecastResult:
    """Explain why a dashboard has no saved result before its first refresh."""
    return ForecastResult(
        currency="EUR",
        condition=None,
        trained_at=None,
        last_observed_at=None,
        observation_count=0,
        day_count=0,
        horizon_days=14,
        confidence_level=0.80,
        points=(),
        unavailable_reason="forecast has not been trained by a refresh yet",
    )
