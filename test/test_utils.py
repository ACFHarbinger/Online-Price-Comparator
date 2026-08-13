"""Unit tests for utils module."""

from __future__ import annotations

from utils import calculate_digest


def test_calculate_digest() -> None:
    """Test SHA-256 digest calculation for dictionary payloads."""
    payload = {"a": 1, "b": "test"}
    digest = calculate_digest(payload)
    assert isinstance(digest, str)
    assert len(digest) == 64
