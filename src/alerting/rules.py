"""Pure alert-fire decision rules (no I/O, no channels).

Rules shipped here:

- **target-price crossing** (does not depend on FX).
- **all-time-low** and **meaningful-drop**, both keyed on
  ``price_eur_equivalent`` (v2.10): a caller passes already-normalised EUR
  amounts, so these rules stay pure and currency-agnostic.
- **tiered historical-low** and **percentile rarity** (v2.14), both keyed on
  ``price_eur_equivalent`` within a single ``condition`` bucket.

See `docs/moon/roadmaps/alerting.md` for the full rules.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from statistics import median


def should_fire_target_alert(
    *,
    current_price: float | None,
    target_price: float | None,
    previous_price: float | None = None,
) -> bool:
    """True when the current price freshly crosses at/below the target.

    Semantics: only ever fire when the price is at or below the target AND we
    are not already below it. A missing ``previous_price`` (first observation)
    is treated as a fresh crossing. This means a price that stays under the
    target across refreshes fires once, and a price already below the target
    at the time a target is set fires on the next refresh (its previous is
    None) - both acceptable for the "notify once on crossing, not every
    refresh" intent. Never fires when ``previous_price <= target`` and
    ``current_price <= target`` (would be a repeat), and never fires on a
    price increase.
    """
    if target_price is None or current_price is None:
        return False
    target = float(target_price)
    current = float(current_price)
    if current > target:
        return False
    if previous_price is None:
        return True
    # Already at/below the target on the previous observation -> not a new
    # crossing; stays silent unless the cooldown has lapsed and we crossed
    # again from above.
    return float(previous_price) > target


def should_fire_all_time_low(
    *,
    current_eur: float | None,
    prior_atl_eur: float | None,
    min_percent: float = 0.02,
    min_amount: float = 5.0,
) -> bool:
    """True when ``current_eur`` is materially below that listing's prior ATL.

    Per `alerting.md`: the current sticker is at least ``max(min_percent,
    min_amount)`` below that listing's prior same-condition sticker ATL. The
    drop must clear the *larger* of the two floors, so a drop is material in
    at least one sense. Never fires when there is no prior ATL (single
    observation) or on an increase.
    """
    if current_eur is None or prior_atl_eur is None:
        return False
    current = float(current_eur)
    prior_atl = float(prior_atl_eur)
    drop = prior_atl - current
    if drop <= 0:
        return False
    threshold = max(min_percent * prior_atl, min_amount)
    return drop >= threshold


def should_fire_meaningful_drop(
    *,
    current_eur: float | None,
    window_eur: Sequence[float],
    min_percent: float = 0.10,
    min_amount: float = 10.0,
    min_observations: int = 3,
) -> bool:
    """True when ``current_eur`` is a meaningful drop vs the listing's median.

    Per `alerting.md`: the current price is at least ``min_percent`` **and**
    ``min_amount`` below that listing's rolling median (over ``window_eur``),
    requiring at least ``min_observations`` in that window. Requires BOTH
    floors, unlike the ATL rule's ``max``. Never fires with too little history
    or on an increase.
    """
    if current_eur is None:
        return False
    recent = [float(value) for value in window_eur]
    if len(recent) < min_observations:
        return False
    baseline = median(recent)
    if baseline <= 0:
        return False
    drop = baseline - float(current_eur)
    if drop <= 0:
        return False
    return drop >= min_percent * baseline and drop >= min_amount


#: The v2.14 tiered ladder, ordered strongest-claim first. ``None`` means
#: all-time (no lookback bound). "at the highest tier reached" means we walk
#: strongest-first and fire once on the first tier the current price clears.
TIERED_HISTORICAL_LOW_WINDOWS: tuple[tuple[str, int | None], ...] = (
    ("all-time", None),
    ("365d", 365),
    ("180d", 180),
    ("90d", 90),
    ("30d", 30),
)

#: ``unknown``/missing condition never forms a comparison bucket - consistent
#: with Grok's v2.11 anomaly discipline.
UNRESOLVED_CONDITIONS = frozenset({None, "", "unknown", "Unknown", "UNKNOWN"})


def strongest_tiered_low(
    *,
    current_eur: float,
    observations: Sequence[tuple[datetime, float]],
    reference: datetime,
    windows: Sequence[tuple[str, int | None]] = TIERED_HISTORICAL_LOW_WINDOWS,
    min_observations: int = 2,
) -> str | None:
    """Return the label of the strongest tier the current price clears, or None.

    ``observations`` is the listing's own same-condition bucket of
    ``(observed_at, eur)`` pairs (including the current one). For each window
    (all-time first) the current price must be at/below that window's minimum
    to claim that tier; longer windows need at least ``min_observations`` in
    them (so a single observation never auto-claims a low). Purely descriptive.
    """
    for label, days in windows:
        if days is None:
            in_window = list(observations)
        else:
            cutoff = reference - timedelta(days=days)
            in_window = [
                (when, value) for when, value in observations if when >= cutoff
            ]
        if len(in_window) < min_observations:
            continue
        window_min = min(value for _, value in in_window)
        if current_eur <= window_min:
            return label
    return None


def _percentile(sorted_values: Sequence[float], fraction: float) -> float:
    """Linear-interpolation percentile (numpy default method)."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    position = fraction * (n - 1)
    lower = int(position)
    upper = min(lower + 1, n - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def percentile_low_reached(
    *,
    current_eur: float,
    observations: Sequence[tuple[datetime, float]],
    reference: datetime,
    window_days: int = 180,
    percentile: float = 5.0,
    min_observations: int = 20,
) -> bool:
    """True when the current price is at/below the configured rarity percentile.

    Computes the percentile over the listing's same-condition EUR observations
    within the trailing ``window_days``, and requires at least
    ``min_observations`` in that window (scaled to the window, ~1 obs per 9
    days as a floor). Purely descriptive.
    """
    cutoff = reference - timedelta(days=window_days)
    values = sorted(value for when, value in observations if when >= cutoff)
    if len(values) < min_observations:
        return False
    threshold = _percentile(values, percentile / 100.0)
    return current_eur <= threshold
