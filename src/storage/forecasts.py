"""Persistence for v2.18's refresh-cadence forecast snapshots."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from forecasting.holt import ForecastPoint, ForecastResult
from storage.schema import forecast_snapshots


class ForecastSnapshotRepository:
    """Store the latest read-only forecast result for each product."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(
        self,
        product_id: int,
        forecast: ForecastResult,
        *,
        refreshed_at: datetime | None = None,
    ) -> None:
        """Replace a product's snapshot after a completed refresh."""
        values = {
            "product_id": product_id,
            "currency": forecast.currency,
            "condition": forecast.condition,
            "trained_at": forecast.trained_at,
            "last_observed_at": forecast.last_observed_at,
            "observation_count": forecast.observation_count,
            "day_count": forecast.day_count,
            "horizon_days": forecast.horizon_days,
            "confidence_level": forecast.confidence_level,
            "points_json": json.dumps(
                [
                    {
                        "forecast_for": point.forecast_for.isoformat(),
                        "lower_bound": point.lower_bound,
                        "upper_bound": point.upper_bound,
                    }
                    for point in forecast.points
                ]
            ),
            "unavailable_reason": forecast.unavailable_reason,
            "refreshed_at": refreshed_at or datetime.now(),
        }
        statement = sqlite_insert(forecast_snapshots).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[forecast_snapshots.c.product_id],
            set_={key: value for key, value in values.items() if key != "product_id"},
        )
        with self._engine.begin() as conn:
            conn.execute(statement)

    def get(self, product_id: int) -> ForecastResult | None:
        """Return the most recently refresh-trained snapshot, if any."""
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    select(forecast_snapshots).where(
                        forecast_snapshots.c.product_id == product_id
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        stored_points = json.loads(str(row["points_json"]))
        points = tuple(
            ForecastPoint(
                forecast_for=datetime.fromisoformat(str(point["forecast_for"])),
                lower_bound=float(point["lower_bound"]),
                upper_bound=float(point["upper_bound"]),
            )
            for point in stored_points
        )
        return ForecastResult(
            currency=row["currency"],
            condition=row["condition"],
            trained_at=row["trained_at"],
            last_observed_at=row["last_observed_at"],
            observation_count=int(row["observation_count"]),
            day_count=int(row["day_count"]),
            horizon_days=int(row["horizon_days"]),
            confidence_level=float(row["confidence_level"]),
            points=points,
            unavailable_reason=row["unavailable_reason"],
        )
