"""Honest local-tier shipping estimates for the retailer table."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShippingCostEstimate:
    """A displayed estimate and the reason it is available."""

    amount_eur: float
    label: str


_DOCUMENTED_LOCAL_DEFAULTS: dict[str, ShippingCostEstimate] = {
    "fnac": ShippingCostEstimate(
        amount_eur=2.50,
        label="from €2.50 to mainland Portugal; checkout confirms",
    ),
    "worten": ShippingCostEstimate(
        amount_eur=2.99,
        label="from €2.99 to mainland Portugal; checkout confirms",
    ),
}


def shipping_cost_for_site(
    site_key: str, configured_amount_eur: float | None
) -> ShippingCostEstimate | None:
    """Return a configured value or a narrowly documented local default.

    ``None`` means unknown rather than free shipping. Defaults are intentionally
    limited to retailers whose published mainland-Portugal starting cost is
    documented in the roadmap; every other site stays unknown until configured.
    """
    if configured_amount_eur is not None:
        return ShippingCostEstimate(
            amount_eur=configured_amount_eur,
            label="site estimate; checkout confirms",
        )
    return _DOCUMENTED_LOCAL_DEFAULTS.get(site_key)
