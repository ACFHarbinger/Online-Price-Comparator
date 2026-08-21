"""Alerting: rules, channel dispatch, delivery persistence (v2.3/v2.4).

This package currently ships the **target-price crossing** slice only. The
all-time-low, meaningful-drop, and v2.14 tiered/percentile rules depend on
``price_eur_equivalent`` (v2.10 FX) and are intentionally not implemented here
yet - see `docs/moon/roadmaps/alerting.md`.
"""

from __future__ import annotations

from alerting.dispatch import (
    AlertDispatcher,
    DiscordDispatcher,
    TelegramDispatcher,
    build_dispatchers,
)
from alerting.models import TARGET_PRICE, AlertDelivery
from alerting.repository import AlertDeliveryRepository
from alerting.rules import should_fire_target_alert
from alerting.service import AlertingService, build_target_message

__all__ = [
    "TARGET_PRICE",
    "AlertDelivery",
    "AlertDeliveryRepository",
    "AlertDispatcher",
    "AlertingService",
    "DiscordDispatcher",
    "TelegramDispatcher",
    "build_dispatchers",
    "build_target_message",
    "should_fire_target_alert",
]
