"""Tests for v2.11 listing-condition extraction."""

from __future__ import annotations

from matching import (
    ConditionSource,
    ListingCondition,
    extract_condition,
)


def test_structured_used_condition_beats_title() -> None:
    result = extract_condition(
        "AMD Ryzen 9 9950X3D nuevo",
        extra={"item_condition": "https://schema.org/UsedCondition"},
        site_key="amazon.es",
    )
    assert result.condition is ListingCondition.USED
    assert result.source is ConditionSource.STRUCTURED_DATA
    assert result.confidence == 0.9


def test_title_refurb_and_surplus() -> None:
    refurb = extract_condition("AMD Ryzen 9 9950X3D reacondicionado")
    assert refurb.condition is ListingCondition.REFURB
    assert refurb.source is ConditionSource.TITLE_HEURISTIC

    surplus = extract_condition("NVIDIA RTX 4090 enterprise surplus pull")
    assert surplus.condition is ListingCondition.ENTERPRISE_SURPLUS


def test_unknown_site_without_signal_is_unknown_not_new() -> None:
    result = extract_condition("AMD Ryzen 9 9950X3D", site_key="newegg")
    assert result.condition is ListingCondition.UNKNOWN
    assert result.source is ConditionSource.UNKNOWN
    assert result.confidence == 0.0


def test_new_stock_site_uses_source_policy_not_verified_new() -> None:
    result = extract_condition("AMD Ryzen 9 9950X3D", site_key="amazon.es")
    assert result.condition is ListingCondition.NEW
    assert result.source is ConditionSource.SOURCE_POLICY
    assert result.confidence == 0.4


def test_title_used_overrides_source_policy() -> None:
    result = extract_condition(
        "AMD Ryzen 9 9950X3D de segunda mano", site_key="amazon.es"
    )
    assert result.condition is ListingCondition.USED
    assert result.source is ConditionSource.TITLE_HEURISTIC
