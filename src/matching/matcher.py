"""Deterministic listing-to-product matching."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rapidfuzz.fuzz import token_set_ratio, token_sort_ratio

from normalize.text import dedupe_key

from .profile import (
    MatchMode,
    ProductIdentityProfile,
    _extract_model_tokens,
    _looks_like_amazon_asin,
    find_excluded_term,
)

# Function words dropped before computing query-token coverage. Product
# vocabulary (brand, model, category nouns) is never listed here.
_MATCHING_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "for",
        "with",
        "to",
        "in",
        "on",
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "y",
        "o",
        "con",
        "para",
        "por",
        "en",
        "um",
        "uma",
        "uns",
        "umas",
        "do",
        "da",
        "dos",
        "das",
        "e",
        "em",
    }
)

_MIN_QUERY_TOKEN_COVERAGE = 0.80
_LIKELY_QUERY_TOKEN_COVERAGE = 0.90
_LIKELY_SORT_RATIO = 92
_REVIEW_SORT_RATIO = 80


class MatchStatus(StrEnum):
    """The confidence outcome of a listing identity decision."""

    CONFIRMED = "confirmed"
    LIKELY = "likely"
    REVIEW = "review"
    REJECTED = "rejected"


@dataclass(frozen=True)
class MatchResult:
    """The outcome and supporting evidence of a listing match decision."""

    status: MatchStatus
    score: float
    reason: str


def match_listing(profile: ProductIdentityProfile, title: str) -> MatchResult:
    """Decide whether a scraped listing title matches a product profile.

    Matching is title-versus-profile only. Amazon ASINs (in titles, URLs,
    or listing ``extra``) are stable *Amazon* listing identifiers, not
    cross-retailer identity keys — this function never reads an ASIN and
    ASIN-shaped tokens are not treated as model/SKU keys.
    """
    normalized_title = dedupe_key(title)
    if not normalized_title:
        return MatchResult(MatchStatus.REJECTED, 0.0, "empty title")

    normalized_name = dedupe_key(profile.canonical_name)
    score = float(token_sort_ratio(normalized_name, normalized_title))
    token_set_score = float(token_set_ratio(normalized_name, normalized_title))
    title_model_tokens = _extract_model_tokens(normalized_title)
    coverage = _query_token_coverage(normalized_name, normalized_title)

    if profile.required_model_tokens and not (
        profile.required_model_tokens & title_model_tokens
    ):
        return MatchResult(MatchStatus.REJECTED, score, "model token mismatch")

    excluded_term = _first_excluded_term(profile, normalized_title)
    if excluded_term is not None:
        return MatchResult(
            MatchStatus.REJECTED,
            score,
            f"excluded term: {excluded_term}",
        )

    title_tokens = frozenset(normalized_title.split())
    if profile.required_brand_tokens and not (
        profile.required_brand_tokens & title_tokens
    ):
        return MatchResult(MatchStatus.REJECTED, score, "brand mismatch")

    if coverage < _MIN_QUERY_TOKEN_COVERAGE:
        return MatchResult(
            MatchStatus.REJECTED,
            score,
            (
                "query-token coverage below threshold "
                f"({coverage:.2f} < {_MIN_QUERY_TOKEN_COVERAGE:.2f})"
            ),
        )

    has_model_match = bool(profile.required_model_tokens & title_model_tokens)

    if profile.match_mode is MatchMode.MANUAL_REVIEW:
        return MatchResult(MatchStatus.REVIEW, score, "manual review mode")

    # Confirmed is "hard model match, no conflict". token_sort_ratio >= 88
    # is *not* applied on this path: real retail titles are verbose and
    # routinely score well below 88 even for the exact SKU. Coverage and
    # the model-token gate carry the decision; token_set_ratio stays
    # supporting evidence only (it rates bundles highly because the
    # requested title is a subset of the bundle title).
    if profile.match_mode is MatchMode.EXACT_MODEL and has_model_match:
        return MatchResult(MatchStatus.CONFIRMED, score, "model token match")

    if score >= _LIKELY_SORT_RATIO and coverage >= _LIKELY_QUERY_TOKEN_COVERAGE:
        return MatchResult(
            MatchStatus.LIKELY,
            score,
            f"strong title match (token-set {token_set_score:.0f})",
        )
    if score >= _REVIEW_SORT_RATIO:
        return MatchResult(
            MatchStatus.REVIEW,
            score,
            f"ambiguous title match (token-set {token_set_score:.0f})",
        )
    return MatchResult(MatchStatus.REJECTED, score, "title score below threshold")


def _query_token_coverage(normalized_query: str, normalized_title: str) -> float:
    """Fraction of meaningful non-stopword query tokens found in the title."""
    query_tokens = _meaningful_query_tokens(normalized_query)
    if not query_tokens:
        return 1.0
    title_tokens = frozenset(normalized_title.split())
    return len(query_tokens & title_tokens) / len(query_tokens)


def _meaningful_query_tokens(normalized_query: str) -> frozenset[str]:
    """Query tokens that count toward coverage: non-stopword, length > 1.

    Single-character tokens (e.g. the ``9`` in ``Ryzen 9``) and Amazon
    ASIN-shaped tokens are dropped so they cannot become an identity key.
    """
    return frozenset(
        token
        for token in normalized_query.split()
        if token not in _MATCHING_STOPWORDS
        and len(token) > 1
        and not _looks_like_amazon_asin(token)
    )


def _first_excluded_term(
    profile: ProductIdentityProfile, normalized_title: str
) -> str | None:
    """Return the first non-negated prohibited phrase in a normalized title."""
    return find_excluded_term(
        normalized_title,
        profile.excluded_terms,
        allowed_terms=profile.allowed_variant_terms,
    )
