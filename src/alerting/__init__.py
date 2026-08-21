"""Alerting: rules, channel dispatch, delivery persistence (v2.3/v2.4/v2.14).

Ships the **target-price**, **all-time-low**, **meaningful-drop**, and the two
v2.14 historical-low modes (**tiered** + **percentile**). See
`docs/moon/roadmaps/alerting.md`.
"""

from __future__ import annotations

from alerting.dispatch import (
    AlertDispatcher,
    DiscordDispatcher,
    TelegramDispatcher,
    build_dispatchers,
)
from alerting.messages import (
    build_all_time_low_message,
    build_meaningful_drop_message,
    build_percentile_message,
    build_target_message,
    build_tiered_low_message,
)
from alerting.models import (
    ALL_ALERT_TYPES,
    ALL_TIME_LOW,
    DEFAULT_MINIMUM_TRACKING_AGE_DAYS,
    DEFAULT_RARITY_PERCENTILE,
    DEFAULT_RARITY_WINDOW_DAYS,
    DEFAULT_TIERED_MIN_OBSERVATIONS,
    MEANINGFUL_DROP,
    PERCENTILE_RARITY,
    TARGET_PRICE,
    TIERED_HISTORICAL_LOW,
    AlertDelivery,
)
from alerting.observations import (
    ListingHistory,
    ListingObservation,
    listing_histories_for_product,
    product_eur_timeline,
)
from alerting.repository import AlertDeliveryRepository
from alerting.rules import (
    TIERED_HISTORICAL_LOW_WINDOWS,
    percentile_low_reached,
    should_fire_all_time_low,
    should_fire_meaningful_drop,
    should_fire_target_alert,
    strongest_tiered_low,
)
from alerting.service import AlertingService

__all__ = [
    "ALL_ALERT_TYPES",
    "ALL_TIME_LOW",
    "DEFAULT_MINIMUM_TRACKING_AGE_DAYS",
    "DEFAULT_RARITY_PERCENTILE",
    "DEFAULT_RARITY_WINDOW_DAYS",
    "DEFAULT_TIERED_MIN_OBSERVATIONS",
    "MEANINGFUL_DROP",
    "PERCENTILE_RARITY",
    "TARGET_PRICE",
    "TIERED_HISTORICAL_LOW",
    "TIERED_HISTORICAL_LOW_WINDOWS",
    "AlertDelivery",
    "AlertDeliveryRepository",
    "AlertDispatcher",
    "AlertingService",
    "DiscordDispatcher",
    "ListingHistory",
    "ListingObservation",
    "TelegramDispatcher",
    "build_all_time_low_message",
    "build_dispatchers",
    "build_meaningful_drop_message",
    "build_percentile_message",
    "build_target_message",
    "build_tiered_low_message",
    "listing_histories_for_product",
    "percentile_low_reached",
    "product_eur_timeline",
    "should_fire_all_time_low",
    "should_fire_meaningful_drop",
    "should_fire_target_alert",
    "strongest_tiered_low",
]
