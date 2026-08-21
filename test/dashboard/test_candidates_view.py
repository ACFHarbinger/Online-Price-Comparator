"""Tests for candidate sources dashboard view (v2.17b)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from dashboard.callbacks import _candidate_sources_panel
from storage.candidates import CandidateListing


def test_candidate_sources_panel_empty() -> None:
    panel = _candidate_sources_panel([])
    assert panel is not None
    panel_any = cast(Any, panel)
    assert "empty-message" in panel_any.className
    assert "No pending candidate sources" in panel_any.children


def test_candidate_sources_panel_rendered() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    candidates = [
        CandidateListing(
            id=1,
            tracked_product_id=10,
            site_key="coolmod",
            site_display_name="Coolmod",
            url="https://coolmod.com/item",
            title="AMD Ryzen 7 7800X3D",
            price_amount=379.99,
            currency="EUR",
            match_status="confirmed",
            match_score=0.92,
            status="pending",
            discovered_at=now,
            expires_at=now + timedelta(days=5),
        )
    ]

    panel = _candidate_sources_panel(candidates, as_of=now)
    assert panel is not None
    panel_any = cast(Any, panel)
    assert panel_any.className == "candidate-table"

    # Header check
    thead = panel_any.children[0]
    headers = [th.children for th in thead.children.children]
    assert headers == [
        "Store",
        "Discovered Product Title",
        "Price",
        "Match Score",
        "Time Limit",
        "Link",
        "Actions",
    ]

    # Row check
    tbody = panel_any.children[1]
    row = tbody.children[0]
    cells = row.children
    assert cells[0].children == "Coolmod"
    assert cells[1].children == "AMD Ryzen 7 7800X3D"
    assert cells[2].children == "EUR 379.99"
    assert "92%" in cells[3].children.children
    assert "5d left" in cells[4].children

    # Actions have approve & reject buttons
    actions = cells[6].children
    assert len(actions) == 2
    assert actions[0].children == "Approve"
    assert actions[0].id == {"type": "candidate-approve-btn", "index": 1}
    assert actions[1].children == "Reject"
    assert actions[1].id == {"type": "candidate-reject-btn", "index": 1}
