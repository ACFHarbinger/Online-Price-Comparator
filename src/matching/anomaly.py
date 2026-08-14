"""Price outlier detection for a single product's cross-retailer snapshot."""

from __future__ import annotations

import statistics
from collections.abc import Iterable
from dataclasses import dataclass

from matching.profile import DEFAULT_EXCLUDED_TERMS
from normalize.text import dedupe_key


@dataclass(frozen=True)
class AnomalyResult:
    is_anomalous: bool
    reason: str | None  # None when not anomalous
    basis: str | None  # None when not anomalous; else a short human-readable
    # summary of the numbers behind the decision, e.g.
    # "n=6, median=520.00, IQR=45.00, high_fence=610.00"


def _find_excluded_term(
    title: str, excluded_terms: Iterable[str] = DEFAULT_EXCLUDED_TERMS
) -> str | None:
    """Return the first excluded term from `excluded_terms` matching `title`."""
    normalized_title = dedupe_key(title)
    if not normalized_title:
        return None
    title_tokens = normalized_title.split()

    matches: list[tuple[int, str]] = []
    for term in excluded_terms:
        normalized_term = dedupe_key(term)
        if not normalized_term:
            continue
        term_tokens = normalized_term.split()
        width = len(term_tokens)
        if width == 0:
            continue
        for index in range(len(title_tokens) - width + 1):
            if title_tokens[index : index + width] == term_tokens:
                matches.append((index, term))
                break

    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def detect_anomalies(prices: list[float], titles: list[str]) -> list[AnomalyResult]:
    """Flag price outliers within one product's cross-retailer snapshot.

    `prices` and `titles` are parallel arrays (same length, same order —
    `titles[i]` is the listing title for `prices[i]`). Returns a list of
    the same length and order.
    """
    n = min(len(prices), len(titles))
    if n < 2:
        return [
            AnomalyResult(is_anomalous=False, reason=None, basis=None)
            for _ in range(n)
        ]

    if n >= 4:
        sorted_prices = sorted(prices[:n])
        quantiles = statistics.quantiles(sorted_prices, n=4, method="inclusive")
        q1, _q2, q3 = quantiles[0], quantiles[1], quantiles[2]
        median = statistics.median(prices[:n])
        iqr = q3 - q1
        high_fence = q3 + 2.0 * iqr
        low_fence = q1 - 2.0 * iqr
        basis = (
            f"n={n}, median={median:.2f}, IQR={iqr:.2f}, "
            f"high_fence={high_fence:.2f}, low_fence={low_fence:.2f}"
        )

        results: list[AnomalyResult] = []
        for i in range(n):
            p = prices[i]
            if p > high_fence and p >= 1.75 * median:
                results.append(
                    AnomalyResult(
                        is_anomalous=True,
                        reason="price is a high-price outlier (> Q3 + 2xIQR fence)",
                        basis=basis,
                    )
                )
            elif p < low_fence and p <= 0.60 * median:
                results.append(
                    AnomalyResult(
                        is_anomalous=True,
                        reason="price is a low-price outlier (< Q1 - 2xIQR fence)",
                        basis=basis,
                    )
                )
            else:
                results.append(
                    AnomalyResult(
                        is_anomalous=False,
                        reason=None,
                        basis=None,
                    )
                )
        return results

    # n is 2 or 3
    results = []
    for i in range(n):
        p = prices[i]
        others = prices[:i] + prices[i + 1 : n]
        median_of_others = statistics.median(others)
        excluded_term = _find_excluded_term(titles[i])

        if p >= 2.5 * median_of_others and excluded_term is not None:
            results.append(
                AnomalyResult(
                    is_anomalous=True,
                    reason=(
                        "price is >=2.5x the median of other listings and title "
                        f"contains excluded term: {excluded_term}"
                    ),
                    basis=f"n={n}, median_of_others={median_of_others:.2f}",
                )
            )
        else:
            results.append(
                AnomalyResult(
                    is_anomalous=False,
                    reason=None,
                    basis=None,
                )
            )
    return results
