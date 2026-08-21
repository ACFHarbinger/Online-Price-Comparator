"""Tests for the deterministic hybrid listing matcher."""

from __future__ import annotations

from dataclasses import replace

from matching import (
    MatchMode,
    MatchStatus,
    build_profile_from_query,
    match_listing,
)
from matching.profile import ProductIdentityProfile

_RYZEN_QUERY = "AMD Ryzen 9 9950X3D"
_AMAZON_ASIN = "B0DGHHMW2G"


def _ryzen_profile() -> ProductIdentityProfile:
    return build_profile_from_query(_RYZEN_QUERY)


def test_ryzen_9950x3d_confirms_exact_listing() -> None:
    """The searched SKU is confirmed even when the retail title is verbose.

    Verbose titles score well below token_sort_ratio 88; confirmation is
    the hard model-token match plus coverage, not a tight sort ratio.
    """
    result = match_listing(
        _ryzen_profile(),
        "Procesador AMD Ryzen 9 9950X3D 16 núcleos 32 hilos 4.3 GHz socket AM5",
    )
    assert result.status is MatchStatus.CONFIRMED
    assert result.reason == "model token match"
    assert result.score < 88


def test_other_ryzen_variants_are_rejected() -> None:
    """Requiring 9950x3d rejects 9800X3D / 5800X3D / 9900X as specified."""
    profile = _ryzen_profile()
    for title in (
        "AMD Ryzen 7 9800X3D 8 núcleos",
        "AMD Ryzen 7 5800X3D",
        "AMD Ryzen 9 9900X 12 núcleos",
    ):
        result = match_listing(profile, title)
        assert result.status is MatchStatus.REJECTED
        assert result.reason == "model token mismatch"


def test_bundle_and_kit_titles_are_rejected() -> None:
    """The €2531 kit is rejected on bundle/component terms, not on score."""
    profile = _ryzen_profile()
    kit = match_listing(
        profile,
        "AMD Ryzen 9 9950X3D Kit refrigeración líquida + placa base",
    )
    assert kit.status is MatchStatus.REJECTED
    assert kit.reason.startswith("excluded term:")

    bundle = match_listing(
        profile,
        "AMD Ryzen 9 9950X3D bundle torre gaming PC completo",
    )
    assert bundle.status is MatchStatus.REJECTED
    assert bundle.reason.startswith("excluded term:")


def test_query_token_coverage_rejects_model_only_title() -> None:
    """A bare model token is not enough: coverage of the query must be >= 0.80."""
    result = match_listing(_ryzen_profile(), "9950X3D")
    assert result.status is MatchStatus.REJECTED
    assert "query-token coverage below threshold" in result.reason


def test_query_token_coverage_rejects_sparse_query_overlap() -> None:
    result = match_listing(
        build_profile_from_query("Sony WH-1000XM5 wireless headphones"),
        "WH-1000XM5 replacement earpads",
    )
    assert result.status is MatchStatus.REJECTED
    assert "query-token coverage below threshold" in result.reason


def test_match_mode_exact_model_confirms_on_model_token() -> None:
    profile = replace(_ryzen_profile(), match_mode=MatchMode.EXACT_MODEL)
    result = match_listing(profile, "Procesador AMD Ryzen 9 9950X3D 16 núcleos")
    assert result.status is MatchStatus.CONFIRMED
    assert profile.match_mode is MatchMode.EXACT_MODEL


def test_match_mode_strict_title_does_not_auto_confirm() -> None:
    """strict_title never confirms, even when the model token is present.

    Verbose retail titles score well below the likely/review sort-ratio
    thresholds, so the same listing that exact_model would confirm is
    rejected on title score here.
    """
    profile = replace(_ryzen_profile(), match_mode=MatchMode.STRICT_TITLE)
    result = match_listing(
        profile,
        "Procesador AMD Ryzen 9 9950X3D 16 núcleos 32 hilos 4.3 GHz socket AM5",
    )
    assert result.status is not MatchStatus.CONFIRMED
    assert result.status is MatchStatus.REJECTED
    assert result.reason == "title score below threshold"


def test_match_mode_strict_title_likely_on_tight_title() -> None:
    profile = build_profile_from_query("Sony wireless headphones")
    assert profile.required_model_tokens == frozenset()
    assert profile.match_mode is MatchMode.STRICT_TITLE
    result = match_listing(profile, "Sony wireless headphones")
    assert result.status is MatchStatus.LIKELY
    assert result.reason.startswith("strong title match")


def test_match_mode_manual_review_never_confirms() -> None:
    profile = replace(_ryzen_profile(), match_mode=MatchMode.MANUAL_REVIEW)
    result = match_listing(profile, "AMD Ryzen 9 9950X3D")
    assert result.status is MatchStatus.REVIEW
    assert result.reason == "manual review mode"


def test_asin_is_not_a_cross_retailer_identity_key() -> None:
    """Sharing an Amazon ASIN must not confirm a different SKU.

    ASINs name an Amazon listing, not a product across retailers. Two
    titles that share ``B0DGHHMW2G`` still live or die on model tokens.
    """
    profile = _ryzen_profile()
    confirmed = match_listing(profile, f"AMD Ryzen 9 9950X3D {_AMAZON_ASIN}")
    rejected = match_listing(profile, f"AMD Ryzen 7 9800X3D {_AMAZON_ASIN}")
    assert confirmed.status is MatchStatus.CONFIRMED
    assert rejected.status is MatchStatus.REJECTED
    assert rejected.reason == "model token mismatch"
    assert _AMAZON_ASIN.lower() not in profile.required_model_tokens


def test_asin_only_query_does_not_become_a_model_token() -> None:
    profile = build_profile_from_query(_AMAZON_ASIN)
    assert profile.required_model_tokens == frozenset()
    assert _AMAZON_ASIN.lower() not in profile.required_model_tokens


def test_build_profile_picks_exact_model_when_sku_token_present() -> None:
    profile = _ryzen_profile()
    assert "9950x3d" in profile.required_model_tokens
    assert profile.match_mode is MatchMode.EXACT_MODEL


def test_allowed_variant_term_is_not_excluded() -> None:
    profile = replace(_ryzen_profile(), allowed_variant_terms=frozenset({"kit"}))
    result = match_listing(profile, "AMD Ryzen 9 9950X3D kit")
    assert result.status is MatchStatus.CONFIRMED


def test_brand_mismatch_is_rejected() -> None:
    profile = replace(_ryzen_profile(), required_brand_tokens=frozenset({"amd"}))
    result = match_listing(profile, "Intel Ryzen 9 9950X3D")
    assert result.status is MatchStatus.REJECTED
    assert result.reason == "brand mismatch"


def test_empty_title_is_rejected() -> None:
    result = match_listing(_ryzen_profile(), "   ")
    assert result.status is MatchStatus.REJECTED
    assert result.score == 0.0
    assert result.reason == "empty title"


def test_title_score_review_when_no_model_token() -> None:
    profile = build_profile_from_query("Sony wireless headphones")
    result = match_listing(profile, "Sony headphones wireless over ear")
    assert result.status is MatchStatus.REVIEW
    assert result.reason.startswith("ambiguous title match")
