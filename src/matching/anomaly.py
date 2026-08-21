"""Price outlier detection for a single product's cross-retailer snapshot.

v2.11: IQR runs **per exact condition bucket** on EUR-equivalent stickers.
``unknown`` and missing EUR values never enter a sample. Sparse buckets
(n<4 in that condition) never auto-hide.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class AnomalyResult:
    is_anomalous: bool
    reason: str | None  # None when not anomalous
    basis: str | None  # None when not anomalous; else a short human-readable
    # summary of the numbers behind the decision, e.g.
    # "n=6, median=520.00, IQR=45.00, high_fence=610.00"


_NOT_ANOMALOUS = AnomalyResult(is_anomalous=False, reason=None, basis=None)
_UNSAMPLED = frozenset({"", "unknown"})


def detect_anomalies(
    prices_eur: Sequence[float | None],
    titles: Sequence[str],
    *,
    conditions: Sequence[str | None],
) -> list[AnomalyResult]:
    """Flag EUR-equivalent outliers within each exact condition bucket.

    Parallel arrays, same length/order. A listing is left unflagged when
    its condition is ``unknown``/missing, its EUR equivalent is missing,
    or its condition bucket has fewer than 4 sampled prices. ``titles`` is
    kept for call-site compatibility; sparse buckets no longer auto-hide
    on excluded-term matches.
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
    return results


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
