"""Alerting data contracts (v2.3/v2.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

#: Alert-type keys stored in ``alert_deliveries.alert_type``.
#: ``all_time_low`` and ``meaningful_drop`` are keyed on
#: ``price_eur_equivalent`` (v2.10). ``tiered_historical_low`` and
#: ``percentile_rarity`` are the two configurable v2.14 historical-low modes.
TARGET_PRICE = "target_price"
ALL_TIME_LOW = "all_time_low"
MEANINGFUL_DROP = "meaningful_drop"
TIERED_HISTORICAL_LOW = "tiered_historical_low"
PERCENTILE_RARITY = "percentile_rarity"

ALL_ALERT_TYPES = frozenset(
    {
        TARGET_PRICE,
        ALL_TIME_LOW,
        MEANINGFUL_DROP,
        TIERED_HISTORICAL_LOW,
        PERCENTILE_RARITY,
    }
)

#: Defaults used when a tracked product's own fields are unset, per
#: `alerting.md`'s "per tracked_products row" config.
DEFAULT_RARITY_PERCENTILE = 5.0
DEFAULT_RARITY_WINDOW_DAYS = 180
DEFAULT_TIERED_MIN_OBSERVATIONS = 2

#: The "rolling-average" meaningful-drop rule is gated on the product having
#: been tracked at least this long, per `alerting.md`'s global defaults, so a
#: freshly-added product with a couple of observations is not alerted on before
#: there is history to know what "normal" looks like. All-time-low and target-
#: price may fire immediately.
DEFAULT_MINIMUM_TRACKING_AGE_DAYS = 7


@dataclass(frozen=True)
class AlertDelivery:
    """One successfully dispatched alert, persisted to ``alert_deliveries``.

    Also drives the per-(product, alert_type) cooldown: the service skips a
    firing if a delivery for the same product + type exists within
    ``alert_cooldown_hours``, so a price hovering at a threshold notifies
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
