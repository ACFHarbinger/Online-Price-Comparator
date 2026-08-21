"""Human-readable alert messages shared across channels."""

from __future__ import annotations

from math import fabs


def _currency(currency: str | None) -> str:
    return (currency or "EUR").upper()


def build_target_message(
    product_label: str,
    *,
    current_price: float,
    target_price: float,
    currency: str | None = None,
) -> str:
    """Target-crossing message."""
    curr = _currency(currency)
    return (
        f"🎯 Target reached: {product_label}\n"
        f"Current price {curr} {current_price:,.2f} is at or below your target "
        f"{curr} {target_price:,.2f}."
    )


def build_all_time_low_message(
    product_label: str,
    site_display_name: str,
    url: str,
    *,
    new_price: float,
    prior_atl: float,
    currency: str | None = None,
) -> str:
    """All-time-low message: prior ATL -> new price, with the buy link."""
    curr = _currency(currency)
    drop = fabs(prior_atl - new_price)
    return (
        f"🔻 New low: {product_label} @ {site_display_name}\n"
        f"Prior ATL {curr} {prior_atl:,.2f} → now {curr} {new_price:,.2f} "
        f"(-{curr} {drop:,.2f})\n"
        f"{(url or '')}"
    )


def build_meaningful_drop_message(
    product_label: str,
    site_display_name: str,
    url: str,
    *,
    new_price: float,
    baseline_median: float,
    currency: str | None = None,
) -> str:
    """Meaningful-drop message: rolling median -> new price, with the buy link."""
    curr = _currency(currency)
    drop = fabs(baseline_median - new_price)
    return (
        f"📉 Meaningful drop: {product_label} @ {site_display_name}\n"
        f"7d median {curr} {baseline_median:,.2f} → now {curr} {new_price:,.2f} "
        f"(-{curr} {drop:,.2f})\n"
        f"{(url or '')}"
    )


def build_tiered_low_message(
    product_label: str,
    site_display_name: str,
    url: str,
    *,
    new_price: float,
    tier_label: str,
    window_min: float,
    currency: str | None = None,
) -> str:
    """Tiered historical-low message (v2.14): strongest tier reached, with link."""
    curr = _currency(currency)
    return (
        f"🏷️ {tier_label} low: {product_label} @ {site_display_name}\n"
        f"Lowest confirmed sticker in window {curr} {window_min:,.2f} "
        f"(now {curr} {new_price:,.2f})\n"
        f"{(url or '')}"
    )


def build_percentile_message(
    product_label: str,
    site_display_name: str,
    url: str,
    *,
    new_price: float,
    rarity_percentile: float,
    window_days: int,
    currency: str | None = None,
) -> str:
    """Percentile rarity message (v2.14), with the buy link."""
    curr = _currency(currency)
    return (
        f"📈 Rare price: {product_label} @ {site_display_name}\n"
        f"At/below the {rarity_percentile:.0f}th percentile over the last "
        f"{window_days}d ({curr} {new_price:,.2f})\n"
        f"{(url or '')}"
    )
