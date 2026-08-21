"""Tests for custom listing URL dashboard view (v2.15 Tier A)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from dashboard.callbacks import _custom_urls_panel
from storage.custom_urls import CustomListingUrl


def test_custom_urls_panel_empty() -> None:
    panel = _custom_urls_panel([])
    assert panel is not None
    panel_any = cast(Any, panel)
    assert "empty-message" in panel_any.className
    assert "No custom listing URLs tracked" in panel_any.children


def test_custom_urls_panel_rendered() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    custom_urls = [
        CustomListingUrl(
            id=10,
            tracked_product_id=5,
            url="https://ldlc.com/item/123",
            site_key="ldlc_com",
            site_display_name="LDLC",
            parser_confidence=1.0,
            status="active",
            last_checked_at=now - timedelta(minutes=15),
            added_at=now,
        )
    ]

    panel = _custom_urls_panel(custom_urls, as_of=now)
    assert panel is not None
    panel_any = cast(Any, panel)
    assert panel_any.className == "custom-url-table"

    # Header check
    thead = panel_any.children[0]
    headers = [th.children for th in thead.children.children]
    assert headers == [
        "Store",
        "Product Page URL",
        "Confidence",
        "Status",
        "Last Checked",
        "Actions",
    ]

    # Row check
    tbody = panel_any.children[1]
    row = tbody.children[0]
    cells = row.children
    assert cells[0].children == "LDLC"
    assert cells[1].children.children == "https://ldlc.com/item/123"
    assert cells[2].children == "100%"
    assert cells[3].children.children == "Active"
    assert "15m ago" in cells[4].children

    # Actions have remove button
    btn = cells[5].children
    assert btn.children == "Remove"
    assert btn.id == {"type": "custom-url-remove-btn", "index": 10}
