"""Tests for richer condition-label display and verbatim grading in dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from dashboard.callbacks import _format_condition_badge, _retailer_table
from matching.condition import (
    ConditionSource,
    ListingCondition,
    extract_condition,
    extract_verbatim_label,
)
from storage.repository import ListingSummary


def test_extract_verbatim_label_from_title() -> None:
    # Storage and enterprise HDD / SSD scan terms
    assert extract_verbatim_label("Western Digital 22 TB SATA OEM drive") == "OEM"
    assert (
        extract_verbatim_label("Seagate 22TB Recertified (ST22000NM000C)")
        == "Recertified"
    )
    assert (
        extract_verbatim_label("Seagate Exos X22 Refurbished — Hervorragend")
        == "Hervorragend"
    )
    assert (
        extract_verbatim_label("Western Digital 22TB Neu (Sonstige) private seller")
        == "Neu (Sonstige)"
    )
    assert (
        extract_verbatim_label("Crucial P310 4TB NVMe SSD Factory Sealed")
        == "Factory Sealed"
    )
    assert (
        extract_verbatim_label("Dell 20TB Datacenter Surplus Hard Drive")
        == "Datacenter Surplus"
    )
    assert extract_verbatim_label("Apple Mac Pro Grade A Refurbished") == "Grade A"


def test_extract_verbatim_label_from_extra() -> None:
    assert (
        extract_verbatim_label("Some Drive", extra={"grading": "Grade A"}) == "Grade A"
    )
    assert (
        extract_verbatim_label("Some Drive", extra={"item_condition": "Recertified"})
        == "Recertified"
    )
    assert (
        extract_verbatim_label(
            "Some Drive",
            extra={"itemCondition": "https://schema.org/RefurbishedCondition"},
        )
        == "RefurbishedCondition"
    )


def test_extract_condition_populates_raw_label() -> None:
    res = extract_condition("Seagate 22TB Recertified SATA drive")
    assert res.condition == ListingCondition.REFURB
    assert res.source == ConditionSource.TITLE_HEURISTIC
    assert res.raw_label == "Recertified"

    res_oem = extract_condition("Western Digital 22TB SATA *oem*")
    assert res_oem.condition == ListingCondition.USED
    assert res_oem.raw_label == "OEM"


def test_format_condition_badge() -> None:
    # Pure coarse badge
    badge_new = cast(Any, _format_condition_badge("new"))
    assert badge_new.children == "NEW"
    assert "badge-condition-new" in badge_new.className

    # Coarse with verbatim label
    badge_refurb = cast(Any, _format_condition_badge("refurb", "Recertified"))
    assert badge_refurb.children == "REFURB · Recertified"
    assert "badge-condition-refurb" in badge_refurb.className

    badge_used_oem = cast(Any, _format_condition_badge("used", "OEM"))
    assert badge_used_oem.children == "USED · OEM"
    assert "badge-condition-used" in badge_used_oem.className

    # Source policy annotation
    badge_policy = cast(
        Any, _format_condition_badge("new", condition_source="source_policy")
    )
    assert badge_policy.children == "NEW"
    assert "source: source_policy" in (badge_policy.title or "")

    # Unknown
    badge_unavail = cast(Any, _format_condition_badge("unknown"))
    assert badge_unavail.children == "UNKNOWN"
    assert "badge-condition-unknown" in badge_unavail.className


def test_retailer_table_renders_condition_badges_with_verbatim() -> None:
    now = datetime(2026, 8, 22, 1, 0, 0)
    listings = [
        ListingSummary(
            site_key="ebay_de",
            site_display_name="eBay.de",
            url="https://ebay.de/itm/wd-22tb-oem-sata",
            image_url=None,
            price_amount=500.0,
            currency="EUR",
            observed_at=now,
            condition="used",
            condition_source="title_heuristic",
        ),
        ListingSummary(
            site_key="amazon_es",
            site_display_name="Amazon.es",
            url="https://amazon.es/dp/B0123",
            image_url=None,
            price_amount=750.0,
            currency="EUR",
            observed_at=now,
            condition="new",
            condition_source="source_policy",
        ),
    ]

    rendered = _retailer_table(listings, avg_30d=600.0, as_of=now)
    assert rendered is not None
    table_any = cast(Any, rendered)
    rows = table_any.children[1].children

    # Row 0: eBay listing with OEM verbatim label in URL
    store_cell_0 = rows[0].children[0]
    badges_0 = [
        c.children for c in store_cell_0.children.children if hasattr(c, "children")
    ]
    assert any("USED · OEM" in str(b) for b in badges_0)

    # Row 1: Amazon listing with NEW condition
    store_cell_1 = rows[1].children[0]
    badges_1 = [
        c.children for c in store_cell_1.children.children if hasattr(c, "children")
    ]
    assert any("NEW" in str(b) for b in badges_1)
