"""v2.12 per-market alias lists — category nouns, no machine translation."""

from __future__ import annotations

from matching import (
    MatchStatus,
    apply_aliases,
    build_profile_from_query,
    match_listing,
)
from normalize.text import dedupe_key


def test_grafikkarte_matches_graphics_card_query() -> None:
    profile = build_profile_from_query("NVIDIA RTX 4070 graphics card")
    german = match_listing(profile, "NVIDIA RTX 4070 Grafikkarte")
    english = match_listing(profile, "NVIDIA RTX 4070 graphics card")
    assert german.status is MatchStatus.LIKELY
    assert german.resolution == "alias_table"
    assert english.status is MatchStatus.LIKELY


def test_prozessor_matches_processor_query() -> None:
    profile = build_profile_from_query("AMD Ryzen 9 9950X3D processor")
    result = match_listing(
        profile,
        "AMD Ryzen 9 9950X3D Prozessor 16 Kerne 32 Threads",
    )
    assert result.status is MatchStatus.CONFIRMED
    assert result.resolution == "alias_table"
    assert result.reason == "model token match"


def test_mainboard_is_excluded_on_cpu_search() -> None:
    profile = build_profile_from_query("AMD Ryzen 9 9950X3D")
    result = match_listing(
        profile,
        "AMD Ryzen 9 9950X3D Mainboard Bundle AM5",
    )
    assert result.status is MatchStatus.REJECTED
    assert result.reason.startswith("excluded term:")


def test_netzteil_is_excluded_on_cpu_search() -> None:
    profile = build_profile_from_query("AMD Ryzen 9 9950X3D")
    result = match_listing(profile, "Netzteil für AMD Ryzen 9 9950X3D 850W")
    assert result.status is MatchStatus.REJECTED
    assert result.reason.startswith("excluded term:")


def test_apply_aliases_is_idempotent() -> None:
    once = apply_aliases(dedupe_key("NVIDIA RTX 4070 Grafikkarte"))
    twice = apply_aliases(once)
    assert once == twice
    assert "graphicscard" in once.split()


def test_sku_token_is_not_translated() -> None:
    """Model tokens stay verbatim — the alias table does not invent SKUs."""
    profile = build_profile_from_query("AMD Ryzen 9 9950X3D")
    assert "9950x3d" in profile.required_model_tokens
    result = match_listing(profile, "AMD Ryzen 9 9800X3D Prozessor")
    assert result.status is MatchStatus.REJECTED
    assert result.reason == "model token mismatch"
