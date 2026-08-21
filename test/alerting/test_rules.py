"""Tests for the target-price crossing rule."""

from __future__ import annotations

from alerting.rules import should_fire_target_alert


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
    """A price already below target on previous observation is not a crossing."""
    assert (
        should_fire_target_alert(
            current_price=550.0, target_price=600.0, previous_price=560.0
        )
        is False
    )


def test_first_observation_below_target_fires() -> None:
    """Missing previous price (first observation) is treated as a crossing."""
    assert should_fire_target_alert(current_price=550.0, target_price=600.0) is True
