"""Pure alert-fire decision rules (no I/O, no channels).

Only the **target-price crossing** rule ships here. The all-time-low,
meaningful-drop, and v2.14 tiered/percentile rules all key on
``price_eur_equivalent`` (a v2.10 FX field that does not exist yet), so they
are deliberately out of scope for this slice - see `docs/moon/roadmaps/alerting.md`.
"""

from __future__ import annotations


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
