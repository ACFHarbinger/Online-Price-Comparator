"""Price outlier detection for a single product's cross-retailer snapshot.

v2.11: IQR runs **per exact condition bucket** on EUR-equivalent stickers.
``unknown`` and missing EUR values never enter a sample. Sparse buckets
(n<4 in that condition) never auto-hide. They may raise an inspect-
seller/condition **review** flag when the sticker is below a per-category
fraction of the ``new`` median.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from normalize.text import dedupe_key

from .aliases import apply_aliases
from .profile import ProductCategory, detect_product_category

# Starting values from product_matching.md — not a universal fence.
# Keyed (category, exact-condition). Callers may override.
DEFAULT_SPARSE_REVIEW_FRACTIONS: dict[tuple[str, str], float] = {
    ("gpu", "enterprise_surplus"): 0.40,
    ("ram", "used"): 0.50,
}

_GPU_CATEGORY_TOKENS = frozenset(
    {
        "gpu",
        "rtx",
        "gtx",
        "geforce",
        "radeon",
        "grafikkarte",
        "graphicscard",
    }
)


@dataclass(frozen=True)
class AnomalyResult:
    is_anomalous: bool
    reason: str | None  # None when not anomalous and not review
    basis: str | None  # None when not anomalous and not review
    needs_review: bool = False  # inspect seller/condition; never hides


_NOT_ANOMALOUS = AnomalyResult(is_anomalous=False, reason=None, basis=None)
_UNSAMPLED = frozenset({"", "unknown"})


def review_category_for(text: str) -> str:
    """Category key for sparse-review fractions. GPU is not a hard-gate."""
    detected = detect_product_category(text)
    if detected is not ProductCategory.OTHER:
        return detected.value
    tokens = frozenset(apply_aliases(dedupe_key(text)).split())
    if tokens & _GPU_CATEGORY_TOKENS:
        return "gpu"
    return ProductCategory.OTHER.value


def detect_anomalies(
    prices_eur: Sequence[float | None],
    titles: Sequence[str],
    *,
    conditions: Sequence[str | None],
    category: str | None = None,
    fractions: Mapping[tuple[str, str], float] | None = None,
    prior_eur: Sequence[float | None] | None = None,
) -> list[AnomalyResult]:
    """Flag EUR-equivalent outliers within each exact condition bucket.

    Parallel arrays, same length/order. A listing is left unflagged when
    its condition is ``unknown``/missing, its EUR equivalent is missing,
    or its condition bucket has fewer than 4 sampled prices. Sparse
    buckets never auto-hide; they may ``needs_review`` when the sticker
    is below the configured fraction of the ``new`` median (or of
    ``prior_eur`` when no new reference exists).
    """
    n = min(len(prices_eur), len(titles), len(conditions))
    results = [_NOT_ANOMALOUS] * n
    buckets: dict[str, list[int]] = defaultdict(list)
    for index in range(n):
        condition = _normalize_condition(conditions[index])
        price = prices_eur[index]
        if condition in _UNSAMPLED or price is None:
            continue
        buckets[condition].append(index)

    for condition, indexes in buckets.items():
        sample = [prices_eur[i] for i in indexes]
        flagged = _iqr_fence(sample, condition=condition)
        for index, result in zip(indexes, flagged, strict=True):
            results[index] = result

    resolved_category = category or (
        review_category_for(titles[0]) if titles else ProductCategory.OTHER.value
    )
    table = dict(DEFAULT_SPARSE_REVIEW_FRACTIONS)
    if fractions is not None:
        table.update(fractions)
    new_median = _median_of([prices_eur[i] for i in buckets.get("new", ())])
    for condition, indexes in buckets.items():
        if len(indexes) >= 4:
            continue
        fraction = table.get((resolved_category, condition))
        if fraction is None:
            continue
        for index in indexes:
            if results[index].is_anomalous:
                continue
            price = prices_eur[index]
            if price is None:
                continue
            prior = None
            if prior_eur is not None and index < len(prior_eur):
                prior = prior_eur[index]
            reference, reference_kind = _review_reference(new_median, prior)
            if reference is None or reference <= 0:
                continue
            threshold = fraction * reference
            if float(price) < threshold:
                results[index] = AnomalyResult(
                    is_anomalous=False,
                    needs_review=True,
                    reason="inspect seller/condition",
                    basis=(
                        f"n={len(indexes)}, condition={condition}, "
                        f"category={resolved_category}, fraction={fraction:.2f}, "
                        f"reference={reference_kind}:{reference:.2f}, "
                        f"threshold={threshold:.2f}, price={float(price):.2f}"
                    ),
                )
    return results


def _median_of(values: Sequence[float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return float(statistics.median(clean))


def _review_reference(
    new_median: float | None,
    prior: float | None,
) -> tuple[float | None, str]:
    """Prefer the snapshot's new median; fall back to a prior sticker."""
    if new_median is not None:
        return new_median, "new_median"
    if prior is not None:
        return float(prior), "prior_sticker"
    return None, "none"


def _normalize_condition(value: str | None) -> str:
    if value is None:
        return "unknown"
    stripped = value.strip().lower()
    return stripped or "unknown"


def _iqr_fence(
    prices: Sequence[float | None], *, condition: str
) -> list[AnomalyResult]:
    """IQR fence for one condition bucket. n<4 never auto-hides."""
    clean = [float(price) for price in prices if price is not None]
    n = len(clean)
    if n < 4:
        return [_NOT_ANOMALOUS] * len(prices)
    if n != len(prices):
        return [_NOT_ANOMALOUS] * len(prices)

    sorted_prices = sorted(clean)
    quantiles = statistics.quantiles(sorted_prices, n=4, method="inclusive")
    q1, _q2, q3 = quantiles[0], quantiles[1], quantiles[2]
    median = statistics.median(clean)
    iqr = q3 - q1
    high_fence = q3 + 2.0 * iqr
    low_fence = q1 - 2.0 * iqr
    basis = (
        f"n={n}, condition={condition}, median={median:.2f}, IQR={iqr:.2f}, "
        f"high_fence={high_fence:.2f}, low_fence={low_fence:.2f}"
    )

    results: list[AnomalyResult] = []
    for price in clean:
        if price > high_fence and price >= 1.75 * median:
            results.append(
                AnomalyResult(
                    is_anomalous=True,
                    reason="price is a high-price outlier (> Q3 + 2xIQR fence)",
                    basis=basis,
                )
            )
        elif price < low_fence and price <= 0.60 * median:
            results.append(
                AnomalyResult(
                    is_anomalous=True,
                    reason="price is a low-price outlier (< Q1 - 2xIQR fence)",
                    basis=basis,
                )
            )
        else:
            results.append(_NOT_ANOMALOUS)
    return results
