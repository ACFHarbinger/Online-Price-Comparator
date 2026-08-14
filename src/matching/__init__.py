"""Deterministic product identity matching utilities."""

from __future__ import annotations

from .anomaly import AnomalyResult, detect_anomalies
from .matcher import MatchResult, MatchStatus, match_listing
from .profile import ProductIdentityProfile, build_profile_from_query

__all__ = [
    "AnomalyResult",
    "MatchResult",
    "MatchStatus",
    "ProductIdentityProfile",
    "build_profile_from_query",
    "detect_anomalies",
    "match_listing",
]
