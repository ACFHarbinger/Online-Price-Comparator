"""Product identity profile construction."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from normalize.text import dedupe_key

DEFAULT_EXCLUDED_TERMS = frozenset(
    {
        "bundle",
        "kit",
        "pack",
        "lote",
        "combo",
        "placa base",
        "motherboard",
        "placa-mãe",
        "cooler",
        "ventilador",
        "fuente de alimentación",
        "fonte de alimentação",
        "case",
        "gabinete",
        "caja",
        "ordenador",
        "computador",
        "equipo de sobremesa",
        "equipos de sobremesa",
        "pc completo",
        "pc gaming",
        "pc racing",
        "torre gaming",
        "desktop",
        "personalizado",
    }
)
"""Common bundle, accessory, and category-conflict terms for v1 matching."""


class MatchMode(StrEnum):
    """How aggressively ``match_listing`` may auto-accept a survivor.

    ``exact_model``
        Confirm only on a hard model-token match (the default when the
        query yields a SKU-like token such as ``9950x3d``).
    ``strict_title``
        No auto-confirm; accept as ``likely`` only when title score and
        query-token coverage both clear the strict thresholds. Used when
        no model token is available.
    ``manual_review``
        Never auto-confirm or auto-likely; survivors are ``review``.
    """

    EXACT_MODEL = "exact_model"
    STRICT_TITLE = "strict_title"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True)
class ProductIdentityProfile:
    """The identity signals required to match a listing to a product.

    ``match_mode`` selects the auto-accept path (see :class:`MatchMode`).
    Amazon ASINs are *not* an identity signal: they name an Amazon
    listing, not a product across retailers, and must not appear in
    ``required_model_tokens``.
    """

    canonical_name: str
    required_model_tokens: frozenset[str]
    required_brand_tokens: frozenset[str]
    excluded_terms: frozenset[str]
    allowed_variant_terms: frozenset[str]
    match_mode: MatchMode = MatchMode.EXACT_MODEL


def build_profile_from_query(query_text: str) -> ProductIdentityProfile:
    """Derive a product identity profile from ad-hoc search keywords."""
    canonical_name = " ".join(query_text.split())
    normalized_query = dedupe_key(canonical_name)
    model_tokens = _extract_model_tokens(normalized_query)
    return ProductIdentityProfile(
        canonical_name=canonical_name,
        required_model_tokens=model_tokens,
        required_brand_tokens=frozenset(),
        excluded_terms=frozenset(dedupe_key(term) for term in DEFAULT_EXCLUDED_TERMS),
        allowed_variant_terms=frozenset(),
        match_mode=(MatchMode.EXACT_MODEL if model_tokens else MatchMode.STRICT_TITLE),
    )


def _looks_like_amazon_asin(token: str) -> bool:
    """Return True for Amazon-ASIN-shaped tokens (typically ``B0XXXXXXXX``).

    ASINs identify an Amazon listing, not a product across retailers, so
    they must not be treated as model/SKU identity tokens.
    """
    return (
        len(token) == 10 and token[0] == "b" and token[1].isdigit() and token.isalnum()
    )


def _extract_model_tokens(normalized_text: str) -> frozenset[str]:
    """Return alphanumeric tokens that contain both a letter and a digit.

    Amazon-ASIN-shaped tokens are excluded: an ASIN is a stable *Amazon*
    listing identifier, not a cross-retailer identity key.
    """
    return frozenset(
        token
        for token in normalized_text.split()
        if any(character.isdigit() for character in token)
        and any(character.isalpha() for character in token)
        and not _looks_like_amazon_asin(token)
    )
