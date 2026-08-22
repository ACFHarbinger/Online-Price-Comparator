"""Tests for the v2.16 four-cell site scorecard."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Engine

from fetch.circuit_breaker import CircuitBreaker
from scoring import SiteSeries, score_sites, scorecards_for_product
from storage.repository import (
    ListingRepository,
    PriceHistoryRepository,
    ProductRepository,
)
from storage.shipping_costs import ShippingCostEstimate

_NOW = datetime(2026, 8, 21, 12, 0, 0)


def _series(
    site_key: str,
    prices: list[float],
    *,
    display: str | None = None,
) -> SiteSeries:
    times = tuple(_NOW - timedelta(days=len(prices) - i) for i in range(len(prices)))
    return SiteSeries(
        site_key=site_key,
        site_display_name=display or site_key,
        eur_prices=tuple(prices),
        observed_at=times,
    )


def test_extreme_value_ranks_cheaper_site_lower() -> None:
    cheap = _series("amazon.es", [100.0, 100.0, 100.0], display="Amazon.es")
    dear = _series("pccomponentes", [200.0, 200.0, 200.0], display="PcComponentes")
    scored = score_sites([cheap, dear], condition="new")
    cards = {card.site_key: card for card in scored}
    assert cards["amazon.es"].extreme_value.confidence == "ok"
    assert cards["pccomponentes"].extreme_value.confidence == "ok"
    amazon_rank = cards["amazon.es"].extreme_value.value
    pcc_rank = cards["pccomponentes"].extreme_value.value
    assert amazon_rank is not None and pcc_rank is not None
    assert amazon_rank < pcc_rank


def test_consistency_low_when_history_too_short_for_cv() -> None:
    short = _series("amazon.es", [100.0, 102.0])
    other = _series("pccomponentes", [110.0, 112.0])
    scored = score_sites([short, other], condition="new")
    cards = {card.site_key: card for card in scored}
    assert cards["amazon.es"].consistency.confidence == "low"
    assert cards["amazon.es"].consistency.value is not None
    assert "not enough history for CV" in cards["amazon.es"].consistency.detail


def test_consistency_reports_cv_and_median_rank() -> None:
    stable = _series("amazon.es", [100.0, 100.0, 100.0])
    jumpy = _series("pccomponentes", [80.0, 120.0, 200.0])
    scored = score_sites([stable, jumpy], condition="new")
    cards = {card.site_key: card for card in scored}
    assert cards["amazon.es"].consistency.confidence == "ok"
    assert "CV 0.0%" in cards["amazon.es"].consistency.detail
    assert cards["pccomponentes"].consistency.confidence == "ok"
    assert "CV" in cards["pccomponentes"].consistency.detail


def test_fulfillment_sla_is_unavailable_without_delivery_data() -> None:
    series = _series("amazon.es", [100.0, 110.0, 105.0])
    other = _series("worten", [90.0, 95.0, 92.0])
    card = score_sites([series, other], condition="new")[0]
    assert card.fulfillment_sla.confidence == "unavailable"
    assert card.fulfillment_sla.value is None
    assert "v2.13" in card.fulfillment_sla.detail


def test_reliability_uses_circuit_breaker_state() -> None:
    breaker = CircuitBreaker()
    breaker.reset()
    breaker.record_failure("amazon.es")
    cards = score_sites(
        [
            _series("amazon.es", [100.0, 101.0, 102.0]),
            _series("pccomponentes", [100.0, 101.0, 102.0]),
        ],
        condition="new",
        breaker=breaker,
    )
    by_site = {card.site_key: card for card in cards}
    assert "1 consecutive" in by_site["amazon.es"].reliability.detail
    assert "no consecutive" in by_site["pccomponentes"].reliability.detail
    breaker.reset()


def test_reliability_reports_open_breaker() -> None:
    breaker = CircuitBreaker()
    breaker.reset()
    breaker.record_failure("amazon.es")
    breaker.record_failure("amazon.es")
    cards = score_sites(
        [
            _series("amazon.es", [100.0, 101.0, 102.0]),
            _series("pccomponentes", [100.0, 101.0, 102.0]),
        ],
        condition="new",
        breaker=breaker,
    )
    amazon = next(card for card in cards if card.site_key == "amazon.es")
    assert amazon.reliability.confidence == "ok"
    assert amazon.reliability.value == 2.0
    assert "circuit breaker open" in amazon.reliability.detail
    breaker.reset()


def test_sparse_single_site_is_low_confidence() -> None:
    cards = score_sites([_series("amazon.es", [100.0, 101.0, 102.0])], condition="new")
    assert cards[0].extreme_value.confidence == "low"
    assert cards[0].extreme_value.value is None


def test_no_composite_score_attribute() -> None:
    cards = score_sites(
        [
            _series("amazon.es", [100.0, 100.0, 100.0]),
            _series("pccomponentes", [110.0, 110.0, 110.0]),
        ],
        condition="used",
    )
    assert not hasattr(cards[0], "composite")
    assert cards[0].condition == "used"


def test_empty_series_are_skipped() -> None:
    empty = SiteSeries(
        site_key="ghost",
        site_display_name="Ghost",
        eur_prices=(),
        observed_at=(),
    )
    other = _series("amazon.es", [100.0, 100.0, 100.0])
    scored = score_sites([empty, other], condition="new")
    assert [card.site_key for card in scored] == ["amazon.es"]


def test_unknown_condition_is_not_scored(in_memory_engine: Engine) -> None:
    assert scorecards_for_product(in_memory_engine, 1, condition="unknown") == []
    assert scorecards_for_product(in_memory_engine, 1, condition="") == []


def test_fulfillment_sla_uses_shipping_estimate_as_low_confidence_proxy() -> None:
    series = _series("worten", [90.0, 95.0, 92.0], display="Worten")
    other = _series("amazon.es", [100.0, 110.0, 105.0])

    cards = score_sites(
        [series, other],
        condition="new",
        shipping_estimates={
            "worten": ShippingCostEstimate(2.99, "from €2.99 to mainland PT"),
        },
    )
    by_site = {card.site_key: card for card in cards}
    sla = by_site["worten"].fulfillment_sla
    assert sla.confidence == "low"
    assert sla.value == 2.99
    assert "cost proxy" in sla.detail
    # A site with no estimate stays unavailable (never invented).
    assert by_site["amazon.es"].fulfillment_sla.confidence == "unavailable"


def test_scorecards_for_product_wires_documented_shipping_estimate(
    in_memory_engine: Engine,
) -> None:
    product_id = ProductRepository(in_memory_engine).get_or_create(
        "AMD Ryzen 9 9950X3D"
    )
    listing_id = ListingRepository(in_memory_engine).upsert(
        product_id=product_id,
        site_key="worten",
        site_display_name="Worten",
        url="https://www.worten.pt/amd-ryzen-9-9950x3d",
        image_url=None,
        seen_at=_NOW,
        match_status="confirmed",
        match_score=95.0,
        match_reason="model token match",
    )
    price_repo = PriceHistoryRepository(in_memory_engine)
    for i, price in enumerate([90.0, 95.0, 92.0]):
        price_repo.add(
            listing_id=listing_id,
            price_amount=price,
            currency="EUR",
            observed_at=_NOW - timedelta(days=3 - i),
            raw_price_text=str(price),
            price_eur_equivalent=price,
            condition="new",
        )

    cards = scorecards_for_product(in_memory_engine, product_id, condition="new")
    worten = next(card for card in cards if card.site_key == "worten")
    # Worten has a documented local shipping default (v2.9) -> real low-confidence SLA.
    assert worten.fulfillment_sla.confidence == "low"
    assert worten.fulfillment_sla.value is not None
