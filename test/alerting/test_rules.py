"""Tests for the alert-fire decision rules."""

from __future__ import annotations

from alerting.rules import (
    should_fire_all_time_low,
    should_fire_meaningful_drop,
    should_fire_target_alert,
)

# -- target-price ------------------------------------------------------------


def test_no_target_never_fires() -> None:
    assert should_fire_target_alert(current_price=500.0, target_price=None) is False


def test_no_current_price_never_fires() -> None:
    assert should_fire_target_alert(current_price=None, target_price=600.0) is False


def test_crossing_below_target_fires() -> None:
    assert (
        should_fire_target_alert(
            current_price=580.0, target_price=600.0, previous_price=650.0
        )
        is True
    )


def test_price_above_target_does_not_fire() -> None:
    assert (
        should_fire_target_alert(
            current_price=620.0, target_price=600.0, previous_price=650.0
        )
        is False
    )


def test_equals_target_fires_on_crossing() -> None:
    assert (
        should_fire_target_alert(
            current_price=600.0, target_price=600.0, previous_price=650.0
        )
        is True
    )


def test_already_below_target_does_not_refire() -> None:
    assert (
        should_fire_target_alert(
            current_price=550.0, target_price=600.0, previous_price=560.0
        )
        is False
    )


def test_first_observation_below_target_fires() -> None:
    assert should_fire_target_alert(current_price=550.0, target_price=600.0) is True


# -- all-time-low ------------------------------------------------------------


def test_atl_fires_when_drop_clears_percent_floor() -> None:
    # prior ATL 1000, current 970 -> drop 30 (3%) >= max(2%*1000=20, 5)=20 -> fire
    assert should_fire_all_time_low(current_eur=970.0, prior_atl_eur=1000.0) is True


def test_atl_fires_when_drop_clears_absolute_floor() -> None:
    # prior ATL 1000, current 994 -> drop 6 (0.6%) < 2% (20) but >= EUR 5
    # -> max=20 -> no.
    # Choose a drop that clears the EUR 5 floor at a small price where 2% is tiny.
    # prior 300, current 294 -> drop 6 (2%) = max(6, 5)=6 -> fires (equal).
    assert (
        should_fire_all_time_low(
            current_eur=294.0, prior_atl_eur=300.0, min_percent=0.02, min_amount=5.0
        )
        is True
    )


def test_atl_does_not_fire_when_drop_too_small_both_floors() -> None:
    # prior 300, current 296 -> drop 4 (1.33%) < 2%(6) and < EUR 5 -> no.
    assert (
        should_fire_all_time_low(
            current_eur=296.0, prior_atl_eur=300.0, min_percent=0.02, min_amount=5.0
        )
        is False
    )


def test_atl_no_prior_no_fire() -> None:
    assert should_fire_all_time_low(current_eur=970.0, prior_atl_eur=None) is False


def test_atl_increase_no_fire() -> None:
    assert should_fire_all_time_low(current_eur=1100.0, prior_atl_eur=1000.0) is False


# -- meaningful-drop ---------------------------------------------------------


def test_meaningful_drop_fires_when_both_floors_cleared() -> None:
    # median 500, current 440 -> drop 60 (12%) >= 10% (50) and >= EUR 10 -> fire
    assert (
        should_fire_meaningful_drop(current_eur=440.0, window_eur=[500.0, 510.0, 490.0])
        is True
    )


def test_meaningful_drop_requires_both_floors() -> None:
    # median 500, current 460 -> drop 40 (8%) < 10% (50), but >= EUR 10
    # -> BOTH needed -> no.
    assert (
        should_fire_meaningful_drop(current_eur=460.0, window_eur=[500.0, 510.0, 490.0])
        is False
    )


def test_meaningful_drop_too_few_observations() -> None:
    assert should_fire_meaningful_drop(current_eur=300.0, window_eur=[350.0]) is False
    assert should_fire_meaningful_drop(current_eur=300.0, window_eur=[]) is False


def test_meaningful_drop_increase_no_fire() -> None:
    assert (
        should_fire_meaningful_drop(current_eur=600.0, window_eur=[500.0, 510.0, 490.0])
        is False
    )
