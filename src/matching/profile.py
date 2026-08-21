"""Product identity profile construction."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

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
        "mainboard",
        "netzteil",
        "gehäuse",
        "gehause",
        "kühler",
        "kuehler",
        "komplettsystem",
        "komplett pc",
        "komplettpc",
    }
)
"""Common bundle, accessory, and category-conflict terms for v1 matching."""

# RAM kits are sold as "32GB kit (2x16GB)"; "desktop memory" is the UDIMM
# product. Those DEFAULT terms would false-positive, so RAM uses this list
# of bundle/full-system/storage-device terms instead (market-scan 2026-08-21).
RAM_EXCLUDED_TERMS = frozenset(
    {
        "bundle",
        "lote",
        "combo",
        "placa base",
        "motherboard",
        "placa-mãe",
        "ordenador",
        "computador",
        "equipo de sobremesa",
        "equipos de sobremesa",
        "pc completo",
        "pc gaming",
        "pc racing",
        "torre gaming",
        "personalizado",
        "aufrüstkit",
        "aufruestkit",
        "aufrustkit",
        "aufrüstset",
        "aufruestset",
        "prebuilt",
        "pre built",
        "laptop",
        "notebook",
        "portatil",
        "portátil",
        "netbook",
        "macbook",
        "imac",
        "mini pc",
        "minipc",
        "barebone",
        "all in one",
        "komplett pc",
        "komplettpc",
        "komplettsystem",
        "ssd",
        "hdd",
        "disco duro",
        "hard disk",
        "hard drive",
        "solid state",
        "mainboard",
    }
)

_RAM_CATEGORY_TOKENS = frozenset(
    {
        "ram",
        "memoria",
        "memory",
        "ddr",
        "ddr3",
        "ddr4",
        "ddr5",
        "udimm",
        "rdimm",
        "sodimm",
        "dimm",
        "ecc",
    }
)
_RAM_CATEGORY_PHRASES = ("so dimm",)
_STORAGE_CATEGORY_TOKENS = frozenset({"ssd", "hdd", "nvme", "sata", "sas"})
_STORAGE_CATEGORY_PHRASES = (
    "hard drive",
    "hard disk",
    "disco duro",
    "solid state",
)
_MODULE_TYPE_EXTRA_KEYS = (
    "module_type",
    "moduleType",
    "memoryType",
    "memory_type",
    "formFactor",
    "form_factor",
)
_INTERFACE_EXTRA_KEYS = (
    "interface",
    "storageInterface",
    "storage_interface",
    "bus",
)

# Particles that negate an immediately following excluded term so a CPU sold
# "Sin Ventilador" / "without a cooler" is not rejected as a cooler listing.
# Articles between the particle and the term ("without a cooler") are skipped.
_EXCLUDED_TERM_NEGATIONS = frozenset({"sin", "sem", "without", "no"})
_EXCLUDED_TERM_NEGATION_SKIP = frozenset(
    {"a", "an", "the", "un", "una", "um", "uma", "el", "la"}
)


def find_excluded_term(
    title: str,
    excluded_terms: Iterable[str] = DEFAULT_EXCLUDED_TERMS,
    *,
    allowed_terms: Iterable[str] = (),
) -> str | None:
    """Return the first non-negated excluded phrase occurring in ``title``.

    A hit is ignored when it is preceded by a negation particle (``sin
    ventilador``, ``sem cooler``, ``without a cooler``, ``no cooler``).
    Positive accessory mentions (``Cooler para Ryzen…``, ``con ventilador``)
    still match. ``allowed_terms`` is the per-profile exception list.
    """
    normalized_title = dedupe_key(title)
    if not normalized_title:
        return None
    title_tokens = normalized_title.split()
    allowed = {dedupe_key(term) for term in allowed_terms if dedupe_key(term)}
    matches: list[tuple[int, str]] = []
    for term in excluded_terms:
        normalized_term = dedupe_key(term)
        if not normalized_term or normalized_term in allowed:
            continue
        term_tokens = normalized_term.split()
        width = len(term_tokens)
        if width == 0:
            continue
        for index in range(len(title_tokens) - width + 1):
            if title_tokens[index : index + width] != term_tokens:
                continue
            if _excluded_term_is_negated(title_tokens, index):
                continue
            matches.append((index, term))
            break
    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def _excluded_term_is_negated(title_tokens: list[str], match_index: int) -> bool:
    """True when ``title_tokens[match_index]`` is preceded by a negation particle."""
    index = match_index - 1
    while index >= 0 and title_tokens[index] in _EXCLUDED_TERM_NEGATION_SKIP:
        index -= 1
    return index >= 0 and title_tokens[index] in _EXCLUDED_TERM_NEGATIONS


class ProductCategory(StrEnum):
    """Coarse identity-profile category for compatibility hard-gates."""

    RAM = "ram"
    STORAGE = "storage"
    OTHER = "other"


class ModuleType(StrEnum):
    """RAM module form. ``unknown`` is never assumed to be UDIMM."""

    UDIMM = "udimm"
    RDIMM = "rdimm"
    SODIMM = "sodimm"
    UNKNOWN = "unknown"


class StorageInterface(StrEnum):
    """Storage bus. ``unknown`` is unscored, never inferred."""

    SATA = "sata"
    NVME = "nvme"
    SAS = "sas"
    USB = "usb"
    UNKNOWN = "unknown"


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

    ``module_type`` / ``storage_interface`` are category-specific hard gates
    (RAM and storage). ``unknown`` is a real value: never silently treated
    as UDIMM or as a matching interface.
    """

    canonical_name: str
    required_model_tokens: frozenset[str]
    required_brand_tokens: frozenset[str]
    excluded_terms: frozenset[str]
    allowed_variant_terms: frozenset[str]
    match_mode: MatchMode = MatchMode.EXACT_MODEL
    category: ProductCategory = ProductCategory.OTHER
    module_type: ModuleType = ModuleType.UNKNOWN
    storage_interface: StorageInterface = StorageInterface.UNKNOWN


def build_profile_from_query(query_text: str) -> ProductIdentityProfile:
    """Derive a product identity profile from ad-hoc search keywords."""
    canonical_name = " ".join(query_text.split())
    normalized_query = dedupe_key(canonical_name)
    model_tokens = _extract_model_tokens(normalized_query)
    category = detect_product_category(canonical_name)
    excluded_source = (
        RAM_EXCLUDED_TERMS
        if category is ProductCategory.RAM
        else DEFAULT_EXCLUDED_TERMS
    )
    return ProductIdentityProfile(
        canonical_name=canonical_name,
        required_model_tokens=model_tokens,
        required_brand_tokens=frozenset(),
        excluded_terms=frozenset(dedupe_key(term) for term in excluded_source),
        allowed_variant_terms=frozenset(),
        match_mode=(MatchMode.EXACT_MODEL if model_tokens else MatchMode.STRICT_TITLE),
        category=category,
        module_type=(
            extract_module_type(canonical_name)
            if category is ProductCategory.RAM
            else ModuleType.UNKNOWN
        ),
        storage_interface=(
            extract_storage_interface(canonical_name)
            if category is ProductCategory.STORAGE
            else StorageInterface.UNKNOWN
        ),
    )


def detect_product_category(text: str) -> ProductCategory:
    """Classify a query/title as RAM, storage, or neither."""
    tokens = dedupe_key(text).split()
    if not tokens:
        return ProductCategory.OTHER
    token_set = frozenset(tokens)
    ram = bool(token_set & _RAM_CATEGORY_TOKENS) or _has_phrase(
        tokens, _RAM_CATEGORY_PHRASES
    )
    storage = bool(token_set & _STORAGE_CATEGORY_TOKENS) or _has_phrase(
        tokens, _STORAGE_CATEGORY_PHRASES
    )
    if ram and not storage:
        return ProductCategory.RAM
    if storage and not ram:
        return ProductCategory.STORAGE
    if ram and storage:
        ram_specific = token_set & {
            "ddr3",
            "ddr4",
            "ddr5",
            "ram",
            "udimm",
            "rdimm",
            "sodimm",
            "memoria",
        }
        if ram_specific:
            return ProductCategory.RAM
        return ProductCategory.STORAGE
    return ProductCategory.OTHER


def extract_module_type(
    text: str,
    *,
    extra: dict[str, Any] | None = None,
) -> ModuleType:
    """Structured-data first, then title keywords, else ``unknown``."""
    structured = _structured_blob(extra, _MODULE_TYPE_EXTRA_KEYS)
    if structured:
        parsed = _module_type_from_text(structured)
        if parsed is not ModuleType.UNKNOWN:
            return parsed
    return _module_type_from_text(text)


def extract_storage_interface(
    text: str,
    *,
    extra: dict[str, Any] | None = None,
) -> StorageInterface:
    """Structured-data first, then title keywords, else ``unknown``."""
    structured = _structured_blob(extra, _INTERFACE_EXTRA_KEYS)
    if structured:
        parsed = _interface_from_text(structured)
        if parsed is not StorageInterface.UNKNOWN:
            return parsed
    return _interface_from_text(text)


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


def _structured_blob(extra: dict[str, Any] | None, keys: tuple[str, ...]) -> str:
    """First non-empty string among ``keys`` in listing extra, else empty."""
    if not extra:
        return ""
    for key in keys:
        raw = extra.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def _module_type_from_text(text: str) -> ModuleType:
    tokens = dedupe_key(text).split()
    if not tokens:
        return ModuleType.UNKNOWN
    token_set = frozenset(tokens)
    found: set[ModuleType] = set()
    if "sodimm" in token_set or _has_phrase(tokens, ("so dimm",)):
        found.add(ModuleType.SODIMM)
    if (
        "rdimm" in token_set
        or "lrdimm" in token_set
        or _has_phrase(
            tokens,
            ("ecc registered", "registered ecc", "registered dimm"),
        )
    ):
        found.add(ModuleType.RDIMM)
    if "udimm" in token_set or _has_phrase(
        tokens,
        ("unbuffered", "unbuffered dimm"),
    ):
        found.add(ModuleType.UDIMM)
    if len(found) == 1:
        return next(iter(found))
    return ModuleType.UNKNOWN


def _interface_from_text(text: str) -> StorageInterface:
    tokens = dedupe_key(text).split()
    if not tokens:
        return StorageInterface.UNKNOWN
    token_set = frozenset(tokens)
    found: set[StorageInterface] = set()
    if "nvme" in token_set:
        found.add(StorageInterface.NVME)
    if "sata" in token_set:
        found.add(StorageInterface.SATA)
    if "sas" in token_set:
        found.add(StorageInterface.SAS)
    if "usb" in token_set:
        found.add(StorageInterface.USB)
    if found == {StorageInterface.USB, StorageInterface.NVME}:
        return StorageInterface.USB
    if found == {StorageInterface.USB, StorageInterface.SATA}:
        return StorageInterface.USB
    if len(found) == 1:
        return next(iter(found))
    return StorageInterface.UNKNOWN


def _has_phrase(title_tokens: list[str], phrases: tuple[str, ...]) -> bool:
    for phrase in phrases:
        needle = dedupe_key(phrase).split()
        width = len(needle)
        if width == 0:
            continue
        for index in range(len(title_tokens) - width + 1):
            if title_tokens[index : index + width] == needle:
                return True
    return False
