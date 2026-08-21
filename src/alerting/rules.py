"""Pure alert-fire decision rules (no I/O, no channels).

Three rules ship here:

- **target-price crossing** (does not depend on FX).
- **all-time-low** and **meaningful-drop**, both keyed on
  ``price_eur_equivalent`` (v2.10): a caller passes already-normalised EUR
  amounts, so these rules stay pure and currency-agnostic.

The v2.14 tiered/percentile rules are a separate follow-up - see
`docs/moon/roadmaps/alerting.md`.
"""

from __future__ import annotations

from collections.abc import Sequence
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
