"""Integration tests for the alert service: rule + cooldown + persistence.

Uses the shared ``in_memory_engine`` fixture and mocked Telegram HTTP via respx
(no network), so a delivered alert actually lands in ``alert_deliveries`` and
drives the per-(product, alert-type) cooldown on the next call.
"""

from __future__ import annotations

import httpx
import respx
from sqlalchemy import Engine

from alerting.dispatch import TELEGRAM_SEND_URL
from alerting.models import TARGET_PRICE
from alerting.repository import AlertDeliveryRepository
from alerting.service import AlertingService, build_target_message
from config.settings import Settings


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "alert_channel": "telegram",
        "telegram_bot_token": "tok",
        "telegram_chat_id": "chat",
        "alert_cooldown_hours": 72,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type,call-arg]


def test_target_alert_delivers_and_dedupes_via_cooldown(
    in_memory_engine: Engine,
) -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    with respx.mock() as router:
        router.post(url).mock(return_value=httpx.Response(200, json={"ok": True}))
        settings = _settings()
        service = AlertingService(in_memory_engine, settings)

        # Fresh crossing below target -> delivered + recorded.
        first = service.evaluate_target_price(
            tracked_product_id=7,
            current_price=550.0,
            target_price=600.0,
            previous_price=650.0,
            product_label="AMD Ryzen 9 9950X3D",
            target_currency="EUR",
        )
        assert first == ["telegram"]

        # Same crossing again immediately -> cooldown suppresses it, no second delivery.
        second = service.evaluate_target_price(
            tracked_product_id=7,
            current_price=540.0,
            target_price=600.0,
            previous_price=650.0,
            product_label="AMD Ryzen 9 9950X3D",
            target_currency="EUR",
        )
        assert second == []

        repo = AlertDeliveryRepository(in_memory_engine)
        assert (
            repo.recent_delivery_for(
                tracked_product_id=7, alert_type=TARGET_PRICE, within_hours=72
            )
            is not None
        )


def test_no_target_or_above_target_is_silent(in_memory_engine: Engine) -> None:
    service = AlertingService(in_memory_engine, _settings())

    # No target set.
    assert (
        service.evaluate_target_price(
            tracked_product_id=7, current_price=550.0, target_price=None
        )
        == []
    )
    # Still above the target.
    assert (
        service.evaluate_target_price(
            tracked_product_id=7,
            current_price=650.0,
            target_price=600.0,
            previous_price=700.0,
        )
        == []
    )


def test_unconfigured_channel_returns_no_delivery(in_memory_engine: Engine) -> None:
    # alert_channel="none" -> dispatchers empty -> evaluated but not delivered.
    service = AlertingService(in_memory_engine, _settings(alert_channel="none"))
    assert (
        service.evaluate_target_price(
            tracked_product_id=7,
            current_price=550.0,
            target_price=600.0,
            previous_price=650.0,
        )
        == []
    )


def test_failed_dispatch_is_not_recorded(in_memory_engine: Engine) -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    with respx.mock() as router:
        router.post(url).mock(return_value=httpx.Response(500))
        service = AlertingService(in_memory_engine, _settings())

        assert (
            service.evaluate_target_price(
                tracked_product_id=7,
                current_price=550.0,
                target_price=600.0,
                previous_price=650.0,
            )
            == []
        )
        # Not recorded, so a retry is allowed (no cooldown block).
        repo = AlertDeliveryRepository(in_memory_engine)
        assert (
            repo.recent_delivery_for(
                tracked_product_id=7, alert_type=TARGET_PRICE, within_hours=72
            )
            is None
        )


def test_build_target_message_content() -> None:
    text = build_target_message(
        "AMD Ryzen 9 9950X3D", current_price=550.0, target_price=600.0, currency="EUR"
    )
    assert "AMD Ryzen 9 9950X3D" in text
    assert "EUR 550.00" in text
    assert "EUR 600.00" in text
