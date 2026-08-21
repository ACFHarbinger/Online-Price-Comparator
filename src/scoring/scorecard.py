"""Per-site value-proposition scorecard (v2.16).

Four independent cells, never averaged into a composite. Price-based cells
run inside one exact condition bucket on EUR-equivalent stickers.
``unknown`` / missing EUR is skipped, not invented.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from statistics import median

from sqlalchemy import Engine

from alerting.observations import listing_histories_for_product
from alerting.rules import UNRESOLVED_CONDITIONS, percentile_low_reached
from dashboard.stats import coefficient_of_variation
from fetch.circuit_breaker import CircuitBreaker

#: Need this many sites in the bucket before a cross-site rank is meaningful.
_MIN_SITES = 2
_RARITY_PERCENTILE = 5.0


@dataclass(frozen=True)
class Dimension:
    """One scorecard cell. ``value`` is None when the cell cannot be scored."""

    name: str
    value: float | None
    detail: str
    confidence: str  # "ok" | "low" | "unavailable"


@dataclass(frozen=True)
class SiteScorecard:
    """Four independent dimensions for one site x condition."""

    site_key: str
    site_display_name: str
    condition: str
    extreme_value: Dimension
    consistency: Dimension
    fulfillment_sla: Dimension
    reliability: Dimension


@dataclass(frozen=True)
class SiteSeries:
    """One site's same-condition EUR sticker series."""

    site_key: str
    site_display_name: str
    eur_prices: tuple[float, ...]
    observed_at: tuple[datetime, ...]


def score_sites(
    series: Sequence[SiteSeries],
    *,
    condition: str,
    breaker: CircuitBreaker | None = None,
    reference: datetime | None = None,
) -> list[SiteScorecard]:
    """Compute scorecards for every site in ``series``. No composite score."""
    breaker = breaker if breaker is not None else CircuitBreaker()
    open_until = breaker.open_sites()
    usable = [item for item in series if item.eur_prices]
    all_prices = [price for item in usable for price in item.eur_prices]
    site_medians = {item.site_key: float(median(item.eur_prices)) for item in usable}
    cards: list[SiteScorecard] = []
    for item in usable:
        latest = item.eur_prices[-1]
        latest_at = item.observed_at[-1] if item.observed_at else reference
        cards.append(
            SiteScorecard(
                site_key=item.site_key,
                site_display_name=item.site_display_name,
                condition=condition,
                extreme_value=_extreme_value(
                    latest,
                    item,
                    all_prices,
                    n_sites=len(usable),
                    reference=latest_at or datetime.now(),
                ),
                consistency=_consistency(item, site_medians),
                fulfillment_sla=_fulfillment_sla(),
                reliability=_reliability(
                    item.site_key,
                    breaker,
                    open_until=open_until,
                ),
            )
        )
    return cards


def scorecards_for_product(
    engine: Engine,
    product_id: int,
    *,
    condition: str,
) -> list[SiteScorecard]:
    """Load EUR histories and score each site in ``condition``."""
    bucket = condition.strip().lower()
    if bucket in UNRESOLVED_CONDITIONS:
        return []
    grouped: dict[str, list[tuple[datetime, float, str]]] = defaultdict(list)
    for history in listing_histories_for_product(engine, product_id):
        for observation in history.observations:
            obs_condition = (observation.condition or "").strip().lower()
            if obs_condition != bucket:
                continue
            grouped[history.site_key].append(
                (
                    observation.observed_at,
                    observation.eur_amount,
                    history.site_display_name,
                )
            )
    series: list[SiteSeries] = []
    for site_key, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: row[0])
        series.append(
            SiteSeries(
                site_key=site_key,
                site_display_name=ordered[0][2],
                eur_prices=tuple(price for _, price, _ in ordered),
                observed_at=tuple(when for when, _, _ in ordered),
            )
        )
    return score_sites(series, condition=bucket)


def _extreme_value(
    latest: float,
    item: SiteSeries,
    all_prices: Sequence[float],
    *,
    n_sites: int,
    reference: datetime,
) -> Dimension:
    """Percentile rank of the latest sticker in the same-condition pool."""
    if n_sites < _MIN_SITES:
        return Dimension(
            "extreme_value",
            None,
            "not enough same-condition sites yet",
            "low",
        )
    cheaper = sum(1 for price in all_prices if price < latest)
    rank = 100.0 * cheaper / len(all_prices)
    observations = list(zip(item.observed_at, item.eur_prices, strict=True))
    at_rarity = False
    if observations:
        at_rarity = percentile_low_reached(
            current_eur=latest,
            observations=observations,
            reference=reference,
            percentile=_RARITY_PERCENTILE,
        )
    rarity_note = " at configured rarity percentile" if at_rarity else ""
    count = len(all_prices)
    return Dimension(
        "extreme_value",
        rank,
        (
            f"latest sticker at the {rank:.0f}th percentile of {count} "
            f"same-condition EUR prices{rarity_note}"
        ),
        "ok",
    )


def _consistency(item: SiteSeries, site_medians: dict[str, float]) -> Dimension:
    volatility = coefficient_of_variation(item.eur_prices)
    medians = list(site_medians.values())
    this_median = site_medians[item.site_key]
    if len(medians) < _MIN_SITES:
        return Dimension(
            "consistency",
            None,
            "not enough same-condition sites for a median rank",
            "low",
        )
    cheaper = sum(1 for value in medians if value < this_median)
    rank = 100.0 * cheaper / len(medians)
    if volatility is None:
        return Dimension(
            "consistency",
            rank,
            f"median rank {rank:.0f}th percentile; not enough history for CV",
            "low",
        )
    return Dimension(
        "consistency",
        rank,
        (
            f"median rank {rank:.0f}th percentile of site medians; "
            f"own-series CV {volatility * 100:.1f}%"
        ),
        "ok",
    )


def _fulfillment_sla() -> Dimension:
    return Dimension(
        "fulfillment_sla",
        None,
        "no delivery estimates persisted yet (v2.13)",
        "unavailable",
    )


def _reliability(
    site_key: str,
    breaker: CircuitBreaker,
    *,
    open_until: dict[str, datetime],
) -> Dimension:
    failures = breaker.failure_count(site_key)
    until = open_until.get(site_key)
    if until is not None:
        return Dimension(
            "reliability",
            float(failures),
            f"circuit breaker open until {until.isoformat()}",
            "ok",
        )
    if failures:
        return Dimension(
            "reliability",
            float(failures),
            f"{failures} consecutive fetch failure(s); breaker still closed",
            "ok",
        )
    return Dimension(
        "reliability",
        0.0,
        "no consecutive fetch failures",
        "ok",
    )
