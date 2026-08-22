"""Deterministic product identity matching utilities."""

from __future__ import annotations

from .aliases import apply_aliases
from .anomaly import (
    AnomalyResult,
    detect_anomalies,
    review_category_for,
)
from .condition import (
    ConditionResult,
    ConditionSource,
    ListingCondition,
    extract_condition,
)
from .matcher import MatchResult, MatchStatus, match_listing
from .profile import (
    MatchMode,
    ModuleType,
    ProductCategory,
    ProductIdentityProfile,
    StorageInterface,
    build_profile_from_query,
    detect_product_category,
    extract_module_type,
    extract_storage_interface,
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
    "ModuleType",
    "ProductCategory",
    "ProductIdentityProfile",
    "StorageInterface",
    "apply_aliases",
    "build_profile_from_query",
    "detect_anomalies",
    "detect_product_category",
    "extract_condition",
    "extract_module_type",
    "extract_storage_interface",
    "find_excluded_term",
    "match_listing",
    "review_category_for",
]
