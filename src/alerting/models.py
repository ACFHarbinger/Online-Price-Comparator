"""Alerting data contracts (v2.3/v2.4, scoped to the target-price slice)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

#: Alert-type keys stored in ``alert_deliveries.alert_type``. The all-time-low,
#: meaningful-drop, and v2.14 tiered/percentile variants are intentionally NOT
#: here yet - they are keyed on ``price_eur_equivalent``, which only exists once
#: v2.10 (FX normalization) lands. This slice ships the one rule that does not
#: depend on it.
TARGET_PRICE = "target_price"

ALL_ALERT_TYPES = frozenset({TARGET_PRICE})


@dataclass(frozen=True)
class AlertDelivery:
    """One successfully dispatched alert, persisted to ``alert_deliveries``.

    Also drives the per-(product, alert_type) cooldown: the service skips a
    crossing if a delivery for the same product + type exists within
    ``alert_cooldown_hours``, so a price hovering at the threshold notifies
    once rather than on every refresh.
    """

    tracked_product_id: int
    alert_type: str
    channel: str
    message: str
    created_at: datetime
    related_price: float | None = None
    target_price: float | None = None
    site_key: str | None = None
