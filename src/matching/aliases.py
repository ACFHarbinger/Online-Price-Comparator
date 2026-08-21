"""Per-market alias lists for v2.12 multilingual matching.

Only the token *categories* that actually vary by language: component nouns
and a few accessory/bundle words. Model/SKU tokens are language-invariant
and are not listed here. Machine translation is a later fallback, not this
module.
"""

from __future__ import annotations

from normalize.text import dedupe_key

# Surface phrase (pre-dedupe) -> canonical token used for coverage/scoring.
# Longer phrases must be listed; application is longest-match on the token
# list after ``dedupe_key``.
_ALIAS_PHRASES: tuple[tuple[str, str], ...] = (
    ("placa gráfica", "graphicscard"),
    ("placa grafica", "graphicscard"),
    ("graphics card", "graphicscard"),
    ("carte graphique", "graphicscard"),
    ("grafikkarte", "graphicscard"),
    ("videokarte", "graphicscard"),
    ("tarjeta grafica", "graphicscard"),
    ("tarjeta gráfica", "graphicscard"),
    ("fuente de alimentación", "psu"),
    ("fuente de alimentacion", "psu"),
    ("fonte de alimentação", "psu"),
    ("fonte de alimentacao", "psu"),
    ("power supply", "psu"),
    ("netzteil", "psu"),
    ("placa-mãe", "motherboard"),
    ("placa mae", "motherboard"),
    ("placa base", "motherboard"),
    ("motherboard", "motherboard"),
    ("mainboard", "motherboard"),
    ("procesador", "processor"),
    ("processador", "processor"),
    ("prozessor", "processor"),
    ("processor", "processor"),
    ("arbeitsspeicher", "memory"),
    ("memoria ram", "memory"),
    ("memória ram", "memory"),
    ("ventilador", "cooler"),
    ("kühler", "cooler"),
    ("kuehler", "cooler"),
    ("cooler", "cooler"),
    ("gehäuse", "case"),
    ("gehause", "case"),
    ("gabinete", "case"),
    ("caja", "case"),
    ("case", "case"),
    ("generalüberholt", "refurb"),
    ("generaluberholt", "refurb"),
    ("reacondicionado", "refurb"),
    ("refurbished", "refurb"),
    ("gebraucht", "used"),
    ("usado", "used"),
    ("usada", "used"),
    ("used", "used"),
)

# Longest phrase first so "placa grafica" wins over a later single token.
_NORMALIZED_ALIASES: tuple[tuple[tuple[str, ...], str], ...] = tuple(
    sorted(
        (
            (tuple(dedupe_key(phrase).split()), canonical)
            for phrase, canonical in _ALIAS_PHRASES
            if dedupe_key(phrase)
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)


def apply_aliases(normalized_text: str) -> str:
    """Replace known phrases with canonical tokens. Idempotent. No I/O."""
    tokens = normalized_text.split()
    if not tokens:
        return normalized_text
    out: list[str] = []
    index = 0
    while index < len(tokens):
        matched = False
        for needle, canonical in _NORMALIZED_ALIASES:
            width = len(needle)
            if tuple(tokens[index : index + width]) == needle:
                out.append(canonical)
                index += width
                matched = True
                break
        if not matched:
            out.append(tokens[index])
            index += 1
    return " ".join(out)


def aliases_changed(original_normalized: str, aliased: str) -> bool:
    """True when the alias table rewrote at least one token."""
    return original_normalized != aliased
