"""Product identity profile construction."""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class ProductIdentityProfile:
    """The identity signals required to match a listing to a product."""

    canonical_name: str
    required_model_tokens: frozenset[str]
    required_brand_tokens: frozenset[str]
    excluded_terms: frozenset[str]
    allowed_variant_terms: frozenset[str]


def build_profile_from_query(query_text: str) -> ProductIdentityProfile:
    """Derive a product identity profile from ad-hoc search keywords."""
    canonical_name = " ".join(query_text.split())
    normalized_query = dedupe_key(canonical_name)
    return ProductIdentityProfile(
        canonical_name=canonical_name,
        required_model_tokens=_extract_model_tokens(normalized_query),
        required_brand_tokens=frozenset(),
        excluded_terms=frozenset(dedupe_key(term) for term in DEFAULT_EXCLUDED_TERMS),
        allowed_variant_terms=frozenset(),
    )


def _extract_model_tokens(normalized_text: str) -> frozenset[str]:
    """Return alphanumeric tokens that contain both a letter and a digit."""
    return frozenset(
        token
        for token in normalized_text.split()
        if any(character.isdigit() for character in token)
        and any(character.isalpha() for character in token)
    )
