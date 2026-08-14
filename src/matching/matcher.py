"""Deterministic listing-to-product matching."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rapidfuzz.fuzz import token_set_ratio, token_sort_ratio

from normalize.text import dedupe_key

from .profile import ProductIdentityProfile, _extract_model_tokens


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
    """Decide whether a scraped listing title matches a product profile."""
    normalized_title = dedupe_key(title)
    if not normalized_title:
        return MatchResult(MatchStatus.REJECTED, 0.0, "empty title")

    normalized_name = dedupe_key(profile.canonical_name)
    score = float(token_sort_ratio(normalized_name, normalized_title))
    token_set_score = float(token_set_ratio(normalized_name, normalized_title))
    title_model_tokens = _extract_model_tokens(normalized_title)

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

    if profile.required_model_tokens & title_model_tokens:
        return MatchResult(MatchStatus.CONFIRMED, score, "model token match")

    if score >= 92:
        return MatchResult(
            MatchStatus.LIKELY,
            score,
            f"strong title match (token-set {token_set_score:.0f})",
        )
    if score >= 80:
        return MatchResult(
            MatchStatus.REVIEW,
            score,
            f"ambiguous title match (token-set {token_set_score:.0f})",
        )
    return MatchResult(MatchStatus.REJECTED, score, "title score below threshold")


def _first_excluded_term(
    profile: ProductIdentityProfile, normalized_title: str
) -> str | None:
    """Return the first prohibited phrase occurring in a normalized title."""
    title_tokens = normalized_title.split()
    allowed_terms = {dedupe_key(term) for term in profile.allowed_variant_terms}
    matches: list[tuple[int, str]] = []
    for term in profile.excluded_terms:
        normalized_term = dedupe_key(term)
        if not normalized_term or normalized_term in allowed_terms:
            continue
        term_tokens = normalized_term.split()
        width = len(term_tokens)
        for index in range(len(title_tokens) - width + 1):
            if title_tokens[index : index + width] == term_tokens:
                matches.append((index, normalized_term))
                break
    return min(matches, default=(-1, ""))[1] or None
