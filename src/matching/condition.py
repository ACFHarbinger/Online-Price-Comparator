"""Listing condition extraction (v2.11).

Order: structured-data signal → title keywords → ``unknown``. ``new`` is
never inferred from missing evidence. Known new-stock retailers may apply
an explicit ``source_policy`` *after* those two steps fail — that is a
recorded policy, not a verified ``new``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from normalize.text import dedupe_key

from .profile import ProductIdentityProfile


class ListingCondition(StrEnum):
    """Exact-condition bucket for a listing or price observation."""

    NEW = "new"
    USED = "used"
    REFURB = "refurb"
    ENTERPRISE_SURPLUS = "enterprise_surplus"
    UNKNOWN = "unknown"


class ConditionSource(StrEnum):
    """Where the current condition belief came from."""

    STRUCTURED_DATA = "structured_data"
    TITLE_HEURISTIC = "title_heuristic"
    SOURCE_POLICY = "source_policy"
    UNKNOWN = "unknown"


# Retailers in this repo that structurally list new stock only. A hit here
# is `source_policy`, never a verified structured/title `new`.
NEW_STOCK_SITE_KEYS = frozenset(
    {
        "amazon.es",
        "pccomponentes",
        "pcdiga",
        "worten",
        "fnac",
        "chip7",
    }
)

_STRUCTURED_MAP: dict[str, ListingCondition] = {
    "newcondition": ListingCondition.NEW,
    "new": ListingCondition.NEW,
    "usedcondition": ListingCondition.USED,
    "used": ListingCondition.USED,
    "damagedcondition": ListingCondition.USED,
    "refurbishedcondition": ListingCondition.REFURB,
    "refurbished": ListingCondition.REFURB,
}

_SURPLUS_PHRASES = (
    "datacenter surplus",
    "enterprise surplus",
    "data center surplus",
    "server pull",
    "datacenter pull",
    "data center",
    "datacenter",
    "surplus",
)
_REFURB_PHRASES = (
    "recertified",
    "recertificado",
    "grade a",
    "grade b",
    "hervorragend",
    "generalüberholt",
    "generaluberholt",
    "reacondicionado",
    "reacondicionada",
    "recondicionado",
    "refurbished",
    "remanufactured",
)
_USED_PHRASES = (
    "neu (sonstige)",
    "neu sonstige",
    "new (other)",
    "new other",
    "open box",
    "caja abierta",
    "segunda mano",
    "2a mano",
    "second hand",
    "oem",
    "usado",
    "usada",
    "usados",
    "gebraucht",
    "occasion",
    "used",
)
_NEW_PHRASES = (
    "brand new",
    "factory sealed",
    "nuevo de fabrica",
    "a estrenar",
    "neuf sous blister",
    "neuf",
    "nuevo",
    "nova",
    "novo",
)

_VERBATIM_CANONICAL: dict[str, str] = {
    "recertified": "Recertified",
    "recertificado": "Recertificado",
    "grade a": "Grade A",
    "grade b": "Grade B",
    "hervorragend": "Hervorragend",
    "generalüberholt": "Generalüberholt",
    "generaluberholt": "Generalüberholt",
    "reacondicionado": "Reacondicionado",
    "reacondicionada": "Reacondicionado",
    "recondicionado": "Recondicionado",
    "remanufactured": "Remanufactured",
    "datacenter surplus": "Datacenter Surplus",
    "enterprise surplus": "Enterprise Surplus",
    "server pull": "Server Pull",
    "datacenter pull": "Datacenter Pull",
    "neu (sonstige)": "Neu (Sonstige)",
    "neu sonstige": "Neu (Sonstige)",
    "new (other)": "New (Other)",
    "new other": "New (Other)",
    "open box": "Open Box",
    "caja abierta": "Open Box",
    "oem": "OEM",
    "factory sealed": "Factory Sealed",
    "brand new": "Brand New",
    "nuevo de fabrica": "Nuevo de Fábrica",
    "a estrenar": "A Estrenar",
    "neuf sous blister": "Neuf sous blister",
    "segunda mano": "Segunda Mano",
    "second hand": "Second Hand",
    "gebraucht": "Gebraucht",
    "occasion": "Occasion",
}


def extract_verbatim_label(
    text: str | None,
    extra: dict[str, Any] | None = None,
) -> str | None:
    """Extract verbatim grading or condition phrase from raw metadata or title text."""
    if extra:
        raw = (
            extra.get("condition_label")
            or extra.get("grading")
            or extra.get("seller_condition")
            or extra.get("condition_raw")
            or extra.get("item_condition")
            or extra.get("itemCondition")
        )
        if isinstance(raw, str) and raw.strip():
            raw_str = raw.strip()
            clean = raw_str.rsplit("/", 1)[-1]
            if clean.lower() in _VERBATIM_CANONICAL:
                return _VERBATIM_CANONICAL[clean.lower()]
            if clean and not clean.startswith("http"):
                return clean

    if not text:
        return None

    norm = dedupe_key(text)
    norm_tokens = norm.split()
    for phrase, canonical in sorted(
        _VERBATIM_CANONICAL.items(), key=lambda item: len(item[0]), reverse=True
    ):
        phrase_norm = dedupe_key(phrase)
        phrase_tokens = phrase_norm.split()
        width = len(phrase_tokens)
        if width == 0:
            continue
        for idx in range(len(norm_tokens) - width + 1):
            if norm_tokens[idx : idx + width] == phrase_tokens:
                return canonical
    return None


@dataclass(frozen=True)
class ConditionResult:
    """Extracted condition plus provenance. ``unknown`` is a real value."""

    condition: ListingCondition
    source: ConditionSource
    confidence: float
    raw_label: str | None = None


def extract_condition(
    title: str,
    *,
    extra: dict[str, Any] | None = None,
    site_key: str | None = None,
    profile: ProductIdentityProfile | None = None,
) -> ConditionResult:
    """Classify a listing's condition. Never guesses ``new`` from silence.

    ``profile`` is accepted so identity-profile callers can pass it through
    without a separate API; it is not consulted this slice.
    """
    del profile
    raw_label = extract_verbatim_label(title, extra)
    structured = _from_structured(extra)
    if structured is not None:
        return ConditionResult(
            structured, ConditionSource.STRUCTURED_DATA, 0.9, raw_label=raw_label
        )
    titled = _from_title(title)
    if titled is not None:
        return ConditionResult(
            titled, ConditionSource.TITLE_HEURISTIC, 0.7, raw_label=raw_label
        )
    if site_key in NEW_STOCK_SITE_KEYS:
        return ConditionResult(
            ListingCondition.NEW,
            ConditionSource.SOURCE_POLICY,
            0.4,
            raw_label=raw_label,
        )
    return ConditionResult(
        ListingCondition.UNKNOWN,
        ConditionSource.UNKNOWN,
        0.0,
        raw_label=raw_label,
    )


def _from_structured(extra: dict[str, Any] | None) -> ListingCondition | None:
    if not extra:
        return None
    raw = extra.get("item_condition") or extra.get("itemCondition")
    if not isinstance(raw, str) or not raw.strip():
        return None
    token = raw.strip().rsplit("/", 1)[-1].replace(" ", "").lower()
    return _STRUCTURED_MAP.get(token)


def _from_title(title: str) -> ListingCondition | None:
    tokens = dedupe_key(title).split()
    if not tokens:
        return None
    if _has_phrase(tokens, _SURPLUS_PHRASES):
        return ListingCondition.ENTERPRISE_SURPLUS
    if _has_phrase(tokens, _REFURB_PHRASES):
        return ListingCondition.REFURB
    if _has_phrase(tokens, _USED_PHRASES):
        return ListingCondition.USED
    if _has_phrase(tokens, _NEW_PHRASES):
        return ListingCondition.NEW
    return None


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
