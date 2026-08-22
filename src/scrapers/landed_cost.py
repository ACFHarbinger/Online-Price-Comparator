"""Conservative, labeled landed-cost estimates for global-tier listings."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Final

_NEWEGG_SHIPPING_USD_RANGE: Final = (15, 30)
_NEWEGG_CLEARANCE_USD_RANGE: Final = (0, 15)
_PORTUGAL_ROUGH_IMPORT_VAT_RATE: Final = 0.23


@dataclass(frozen=True)
class LandedCostEstimate:
    """A transparent range, never a checkout quote or tax determination."""

    sticker_amount: float
    shipping_min: int
    shipping_max: int
    clearance_min: int
    clearance_max: int
    vat_rate: float
    total_min: int
    total_max: int

    def as_extra(self) -> dict[str, Any]:
        """Serialize the estimate as display-ready, audit-friendly metadata."""
        return {
            "landed_cost_estimate": {
                "label": "Estimated Portugal landed cost — confirm at checkout",
                "currency": "USD",
                "sticker_amount": self.sticker_amount,
                "shipping_range": [self.shipping_min, self.shipping_max],
                "customs_clearance_range": [self.clearance_min, self.clearance_max],
                "rough_import_vat_rate": self.vat_rate,
                "estimated_total_range": [self.total_min, self.total_max],
                "delivery_note": (
                    "International delivery timing is not known on the search page; "
                    "confirm at checkout."
                ),
                "assumptions": (
                    "RAM is treated as a low-duty-friction item; this range "
                    "includes no product-duty estimate.",
                    "The range includes rough shipping, clearance, and import "
                    "VAT only.",
                    "Carrier charges, seller tax collection, and checkout shipping "
                    "can change the final total.",
                ),
            }
        }


def estimate_newegg_portugal_landed_cost(
    sticker_amount: float, currency: str
) -> LandedCostEstimate | None:
    """Estimate a USD Newegg RAM purchase delivered to Portugal.

    The inputs deliberately stay narrow: this is the v2.13 first-source
    estimate, not a general customs engine. Values are rounded *up* to whole
    dollars so the displayed range does not communicate cent-level certainty.
    """
    if currency.upper() != "USD" or sticker_amount <= 0:
        return None

    shipping_min, shipping_max = _NEWEGG_SHIPPING_USD_RANGE
    clearance_min, clearance_max = _NEWEGG_CLEARANCE_USD_RANGE
    total_min = _round_up(
        sticker_amount
        + shipping_min
        + clearance_min
        + (sticker_amount + shipping_min) * _PORTUGAL_ROUGH_IMPORT_VAT_RATE
    )
    total_max = _round_up(
        sticker_amount
        + shipping_max
        + clearance_max
        + (sticker_amount + shipping_max) * _PORTUGAL_ROUGH_IMPORT_VAT_RATE
    )
    return LandedCostEstimate(
        sticker_amount=sticker_amount,
        shipping_min=shipping_min,
        shipping_max=shipping_max,
        clearance_min=clearance_min,
        clearance_max=clearance_max,
        vat_rate=_PORTUGAL_ROUGH_IMPORT_VAT_RATE,
        total_min=total_min,
        total_max=total_max,
    )


def _round_up(amount: float) -> int:
    """Round an uncertain estimate up to a whole currency unit."""
    return ceil(amount)
