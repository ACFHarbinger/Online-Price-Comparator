"""Deterministic product identity matching utilities."""

from __future__ import annotations

from .anomaly import AnomalyResult, detect_anomalies
from .condition import (
    ConditionResult,
    ConditionSource,
    ListingCondition,
    extract_condition,
)
from .matcher import MatchResult, MatchStatus, match_listing
from .profile import (
    MatchMode,
    ProductIdentityProfile,
    build_profile_from_query,
    find_excluded_term,
)

__all__ = [
    "AnomalyResult",
    "ConditionResult",
    "ConditionSource",
    "ListingCondition",
    "MatchMode",
    "MatchResult",
    "MatchStatus",
    "ProductIdentityProfile",
    "build_profile_from_query",
    "detect_anomalies",
    "extract_condition",
    "find_excluded_term",
    "match_listing",
]
