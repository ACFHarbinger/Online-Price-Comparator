"""Text normalization utilities for product titles."""

from __future__ import annotations

import unicodedata


def normalize_title(title: str) -> str:
    """Clean a scraped product title for display: strip leading/trailing
    whitespace, collapse internal runs of whitespace to a single space,
    remove stray control characters. Preserve original casing and punctuation
    otherwise — this is for DISPLAY, not matching.
    """
    cleaned_chars: list[str] = []
    for ch in title:
        if ch.isspace():
            cleaned_chars.append(" ")
        elif not unicodedata.category(ch).startswith("C"):
            cleaned_chars.append(ch)

    return " ".join("".join(cleaned_chars).split())


def dedupe_key(title: str) -> str:
    """Produce a canonicalized key from a title for identifying likely-the-same
    product across sites: lowercase, strip punctuation, collapse whitespace to
    single spaces. This is intentionally simple normalization only (no fuzzy
    matching library, no NLP) — good enough to catch near-identical titles,
    not meant to catch every paraphrase.
    """
    normalized = normalize_title(title).lower()
    cleaned_chars: list[str] = [ch if ch.isalnum() else " " for ch in normalized]
    return " ".join("".join(cleaned_chars).split())
