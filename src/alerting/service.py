"""Alert service: evaluate a rule, dedupe via cooldown, dispatch, persist.

This is the target-price slice (v2.3/v2.4 scoped down). It evaluates a single
tracked product's current price against its ``target_price``, honors the
per-(product, alert-type) cooldown from ``alert_cooldown_hours``, dispatches
to every enabled channel, and records each successful delivery so the rule
fires once on a crossing rather than on every refresh.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import Engine

from alerting.dispatch import build_dispatchers
from alerting.models import TARGET_PRICE, AlertDelivery
from alerting.repository import AlertDeliveryRepository
from alerting.rules import should_fire_target_alert
from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_HOURS = 72.0


def build_target_message(
    product_label: str,
    *,
    current_price: float,
    target_price: float,
    currency: str | None = None,
) -> str:
    """Human-readable target-crossing message (both channels share it)."""
    curr = (currency or "EUR").upper()
    return (
        f"🎯 Target reached: {product_label}\n"
        f"Current price {curr} {current_price:,.2f} is at or below your target "
        f"{curr} {target_price:,.2f}."
    )


class AlertingService:
    """Evaluates + delivers alerts for tracked products."""

    def __init__(self, engine: Engine, settings: Settings | None = None) -> None:
        self.engine = engine
        self.settings = settings or get_settings()
        self.deliveries = AlertDeliveryRepository(engine)

    def evaluate_target_price(
        self,
        *,
        tracked_product_id: int,
        current_price: float | None,
        target_price: float | None,
        previous_price: float | None = None,
        product_label: str = "tracked product",
        site_key: str | None = None,
        target_currency: str | None = None,
        as_of: datetime | None = None,
    ) -> list[str]:
        """Return the channels an alert was delivered to (or ``[]``).

        Fires only when the price freshly crosses at/below the target AND no
        delivery for this (product, ``target_price``) exists within
        ``alert_cooldown_hours``. Never raises: an unconfigured or failing
        channel just contributes nothing (and is not recorded, so it can be
        retried on the next refresh).
        """
        if not should_fire_target_alert(
            current_price=current_price,
            target_price=target_price,
            previous_price=previous_price,
        ):
            return []

        cooldown = self.settings.alert_cooldown_hours or DEFAULT_COOLDOWN_HOURS
        recent = self.deliveries.recent_delivery_for(
            tracked_product_id=tracked_product_id,
            alert_type=TARGET_PRICE,
            within_hours=cooldown,
            as_of=as_of,
        )
        if recent is not None:
            return []

        # Not in cooldown yet - build the message and dispatch once each channel.
        message = build_target_message(
            product_label,
            current_price=float(current_price or 0.0),
            target_price=float(target_price or 0.0),
            currency=target_currency,
        )
        delivered: list[str] = []
        for dispatcher in build_dispatchers(self.settings):
            if not dispatcher.is_configured():
                logger.info("Channel %s not configured; skipping", dispatcher.name)
                continue
            if dispatcher.send(message):
                self.deliveries.record(
                    AlertDelivery(
                        tracked_product_id=tracked_product_id,
                        alert_type=TARGET_PRICE,
                        channel=dispatcher.name,
                        message=message,
                        created_at=as_of or datetime.now(),
                        related_price=float(current_price or 0.0),
                        target_price=float(target_price or 0.0),
                        site_key=site_key,
                    )
                )
                delivered.append(dispatcher.name)
            else:
                logger.warning(
                    "Channel %s failed to deliver; not recorded", dispatcher.name
                )
        return delivered
