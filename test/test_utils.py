"""Unit tests for utils module."""

from __future__ import annotations

from utils import calculate_digest, format_metadata


def test_calculate_digest() -> None:
    """Test SHA-256 digest calculation for dictionary payloads."""
    payload = {"a": 1, "b": "test"}
    digest = calculate_digest(payload)
    assert isinstance(digest, str)
    assert len(digest) == 64


def test_format_metadata() -> None:
    """Test metadata formatting string output."""
    res_base = format_metadata("mod", "1.0.0")
    assert res_base == "mod v1.0.0"

    res_extra = format_metadata("mod", "1.0.0", {"env": "prod"})
    assert res_extra == "mod v1.0.0 (env=prod)"
