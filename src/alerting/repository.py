"""Persistence for alert deliveries (cooldown + audit).

Sits in the ``alerting`` package to keep the storage layer's existing
repositories untouched; it is the only alerting code that touches the database,
and it only touches the additive ``alert_deliveries`` table.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Engine, select

from alerting.models import AlertDelivery
from storage.schema import alert_deliveries


def _row_to_delivery(row: object) -> AlertDelivery:
    return AlertDelivery(
        tracked_product_id=int(row.tracked_product_id),  # type: ignore[attr-defined]
        alert_type=str(row.alert_type),  # type: ignore[attr-defined]
        channel=str(row.channel),  # type: ignore[attr-defined]
        message=str(row.message),  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        related_price=row.related_price,  # type: ignore[attr-defined]
        target_price=row.target_price,  # type: ignore[attr-defined]
        site_key=row.site_key,  # type: ignore[attr-defined]
    )


class AlertDeliveryRepository:
    """Reads/writes ``alert_deliveries``."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def record(
        self,
        delivery: AlertDelivery,
        *,
        status: str = "delivered",
    ) -> int:
        """Insert one delivered alert; returns its id."""
        with self.engine.begin() as conn:
            result = conn.execute(
                alert_deliveries.insert().values(
                    tracked_product_id=delivery.tracked_product_id,
                    alert_type=delivery.alert_type,
                    channel=delivery.channel,
                    message=delivery.message,
                    related_price=delivery.related_price,
                    target_price=delivery.target_price,
                    site_key=delivery.site_key,
                    created_at=delivery.created_at,
                )
            )
        inserted_id = result.inserted_primary_key
        assert inserted_id is not None
        return int(inserted_id[0])

    def recent_delivery_for(
        self,
        *,
        tracked_product_id: int,
        alert_type: str,
        within_hours: float,
        as_of: datetime | None = None,
    ) -> AlertDelivery | None:
        """Most recent delivery for (product, alert_type) within the cooldown."""
        reference = as_of or datetime.now()
        cutoff = reference - timedelta(hours=within_hours)
        stmt = (
            select(alert_deliveries)
            .where(
                alert_deliveries.c.tracked_product_id == tracked_product_id,
                alert_deliveries.c.alert_type == alert_type,
                alert_deliveries.c.created_at >= cutoff,
            )
            .order_by(alert_deliveries.c.created_at.desc())
            .limit(1)
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt).one_or_none()
        return _row_to_delivery(row) if row is not None else None
