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
from alerting.messages import build_target_message
from alerting.models import TARGET_PRICE
from alerting.repository import AlertDeliveryRepository
from alerting.service import AlertingService
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


# -- evaluate_tracked_product (ATL + meaningful-drop + target) ----------------

from datetime import datetime, timedelta  # noqa: E402

from alerting.models import ALL_TIME_LOW, MEANINGFUL_DROP  # noqa: E402
from storage.repository import (  # noqa: E402
    ListingRepository,
    PriceHistoryRepository,
)
from storage.schema import tracked_products  # noqa: E402
from storage.watchlist import TrackedProductRepository  # noqa: E402


def _seed_tracked(engine: Engine, query_text: str) -> int:
    """Create a tracked product; returns its id (used as tracked_product_id)."""
    return TrackedProductRepository(engine).get_or_create(query_text).id


def _seed_listing_history(
    engine: Engine,
    product_id: int,
    *,
    site_key: str,
    url: str,
    observations: list[tuple[datetime, float]],
) -> None:
    """One confirmed listing with EUR-equivalent observations (oldest -> newest)."""
    now = datetime(2026, 8, 21, 12, 0, 0)
    listing_repo = ListingRepository(engine)
    price_repo = PriceHistoryRepository(engine)
    listing_id = listing_repo.upsert(
        product_id=product_id,
        site_key=site_key,
        site_display_name=site_key.title(),
        url=url,
        image_url=None,
        seen_at=now,
        match_status="confirmed",
        match_score=95.0,
        match_reason="model token match",
    )
    for observed_at, eur in observations:
        price_repo.add(
            listing_id=listing_id,
            price_amount=eur,
            currency="EUR",
            observed_at=observed_at,
            raw_price_text=f"{eur:.2f}",
            price_eur_equivalent=eur,
            price_native=eur,
            currency_native="EUR",
        )


def _product_id(engine: Engine, tracked_product_id: int) -> int:
    tracked = TrackedProductRepository(engine).get(tracked_product_id)
    assert tracked is not None
    return tracked.product_id


@respx.mock
def test_evaluate_tracked_product_fires_atl(in_memory_engine: Engine) -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    respx.post(url).mock(return_value=httpx.Response(200, json={"ok": True}))
    tracked_id = _seed_tracked(in_memory_engine, "AMD Ryzen 9 9950X3D")
    pid = _product_id(in_memory_engine, tracked_id)
    base = datetime(2026, 8, 21, 12, 0, 0)
    _seed_listing_history(
        in_memory_engine,
        pid,
        site_key="amazon.es",
        url="https://amazon.es/dp/1",
        observations=[(base - timedelta(days=20), 600.0), (base, 400.0)],
    )
    service = AlertingService(in_memory_engine, _settings())

    delivered = service.evaluate_tracked_product(tracked_id, as_of=base)

    assert delivered.get(ALL_TIME_LOW) == ["telegram"]
    # Freshly-tracked product: the meaningful-drop (rolling-average) age gate is
    # not met, so it must not appear.
    assert MEANINGFUL_DROP not in delivered


@respx.mock
def test_evaluate_tracked_product_fires_meaningful_drop(
    in_memory_engine: Engine,
) -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    respx.post(url).mock(return_value=httpx.Response(200, json={"ok": True}))
    tracked_id = _seed_tracked(in_memory_engine, "AMD Ryzen 9 9950X3D")
    pid = _product_id(in_memory_engine, tracked_id)
    # Age the tracked product so the meaningful-drop (rolling-average) gate
    # minimum_tracking_age_days passes.
    with in_memory_engine.begin() as conn:
        conn.execute(
            tracked_products.update()
            .where(tracked_products.c.id == tracked_id)
            .values(created_at=datetime.now() - timedelta(days=10))
        )
    base = datetime(2026, 8, 21, 12, 0, 0)
    _seed_listing_history(
        in_memory_engine,
        pid,
        site_key="pccomponentes",
        url="https://pccomponentes.com/1",
        observations=[
            (base - timedelta(days=4), 500.0),
            (base - timedelta(days=3), 510.0),
            (base - timedelta(days=2), 490.0),
            (base, 400.0),
        ],
    )
    service = AlertingService(in_memory_engine, _settings())

    delivered = service.evaluate_tracked_product(tracked_id, as_of=base)

    assert delivered.get(MEANINGFUL_DROP) == ["telegram"]
    # prior ATL is 490, current 400 -> drop 90; that is also an all-time low.
    assert ALL_TIME_LOW in delivered


@respx.mock
def test_evaluate_tracked_product_respects_cooldown(in_memory_engine: Engine) -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    respx.post(url).mock(return_value=httpx.Response(200, json={"ok": True}))
    tracked_id = _seed_tracked(in_memory_engine, "AMD Ryzen 9 9950X3D")
    pid = _product_id(in_memory_engine, tracked_id)
    base = datetime(2026, 8, 21, 12, 0, 0)
    _seed_listing_history(
        in_memory_engine,
        pid,
        site_key="amazon.es",
        url="https://amazon.es/dp/1",
        observations=[(base - timedelta(days=20), 600.0), (base, 400.0)],
    )
    service = AlertingService(in_memory_engine, _settings())

    first = service.evaluate_tracked_product(tracked_id, as_of=base)
    assert first.get(ALL_TIME_LOW) == ["telegram"]

    # Same evaluation again immediately -> cooldown suppresses the redelivery.
    second = service.evaluate_tracked_product(tracked_id, as_of=base)
    assert ALL_TIME_LOW not in second


@respx.mock
def test_evaluate_tracked_product_target_price(in_memory_engine: Engine) -> None:
    url = TELEGRAM_SEND_URL.format(token="tok")
    respx.post(url).mock(return_value=httpx.Response(200, json={"ok": True}))
    tracked_id = _seed_tracked(in_memory_engine, "AMD Ryzen 9 9950X3D")
    pid = _product_id(in_memory_engine, tracked_id)
    with in_memory_engine.begin() as conn:
        conn.execute(
            tracked_products.update()
            .where(tracked_products.c.id == tracked_id)
            .values(target_price=600.0, target_currency="EUR")
        )
    base = datetime(2026, 8, 21, 12, 0, 0)
    _seed_listing_history(
        in_memory_engine,
        pid,
        site_key="amazon.es",
        url="https://amazon.es/dp/1",
        observations=[(base - timedelta(days=3), 650.0), (base, 550.0)],
    )
    service = AlertingService(in_memory_engine, _settings())

    delivered = service.evaluate_tracked_product(tracked_id, as_of=base)

    assert delivered.get("target_price") == ["telegram"]
