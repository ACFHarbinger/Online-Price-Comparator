"""Deterministic product identity matching utilities."""

from __future__ import annotations

from .matcher import MatchResult, MatchStatus, match_listing
from .profile import ProductIdentityProfile, build_profile_from_query

__all__ = [
    "MatchResult",
    "MatchStatus",
    "ProductIdentityProfile",
    "build_profile_from_query",
    "match_listing",
]
