"""Alerting: rules, channel dispatch, delivery persistence (v2.3/v2.4).

Ships the **target-price**, **all-time-low**, and **meaningful-drop** rules.
The v2.14 tiered/percentile historical-low modes are a separate follow-up - see
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
    build_target_message,
)
from alerting.models import (
    ALL_ALERT_TYPES,
    ALL_TIME_LOW,
    DEFAULT_MINIMUM_TRACKING_AGE_DAYS,
    MEANINGFUL_DROP,
    TARGET_PRICE,
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
    should_fire_all_time_low,
    should_fire_meaningful_drop,
    should_fire_target_alert,
)
from alerting.service import AlertingService

__all__ = [
    "ALL_ALERT_TYPES",
    "ALL_TIME_LOW",
    "DEFAULT_MINIMUM_TRACKING_AGE_DAYS",
    "MEANINGFUL_DROP",
    "TARGET_PRICE",
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
    "build_target_message",
    "listing_histories_for_product",
    "product_eur_timeline",
    "should_fire_all_time_low",
    "should_fire_meaningful_drop",
    "should_fire_target_alert",
]
