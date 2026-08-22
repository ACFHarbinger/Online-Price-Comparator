"""Tests for candidate sources dashboard view (v2.17b)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from dashboard.callbacks import _candidate_sources_panel
from scoring.scorecard import Dimension, SiteScorecard
from storage.candidates import CandidateListing


def test_candidate_sources_panel_empty() -> None:
    panel = _candidate_sources_panel([])
    assert panel is not None
    panel_any = cast(Any, panel)
    assert "empty-message" in panel_any.className
    assert "No pending candidate sources" in panel_any.children


def test_candidate_sources_panel_rendered_without_scorecard() -> None:
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
        "Site Scorecard",
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
    assert "Not enough data yet" in str(cells[4].children)
    assert "5d left" in cells[5].children

    # Actions have approve & reject buttons
    actions = cells[7].children
    assert len(actions) == 2
    assert actions[0].children == "Approve"
    assert actions[0].id == {"type": "candidate-approve-btn", "index": 1}
    assert actions[1].children == "Reject"
    assert actions[1].id == {"type": "candidate-reject-btn", "index": 1}


def test_candidate_sources_panel_rendered_with_scorecard() -> None:
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

    scorecards = {
        "coolmod": SiteScorecard(
            site_key="coolmod",
            site_display_name="Coolmod",
            condition="new",
            extreme_value=Dimension("extreme_value", 10.0, "ATL", "ok"),
            consistency=Dimension("consistency", 50.0, "rank 50th", "ok"),
            fulfillment_sla=Dimension("fulfillment_sla", None, "none", "unavailable"),
            reliability=Dimension("reliability", 0.0, "0 failures", "ok"),
        )
    }

    panel = _candidate_sources_panel(candidates, scorecards=scorecards, as_of=now)
    assert panel is not None
    panel_any = cast(Any, panel)
    tbody = panel_any.children[1]
    row = tbody.children[0]
    cells = row.children

    # Four independent cells, no composite — reuse _format_scorecard_cell.
    scorecard_cell = cells[4].children
    rendered = str(scorecard_cell)
    assert "Extreme" in rendered
    assert "10th percentile" in rendered
    assert "Consistency" in rendered
    assert "50th pct median" in rendered
    assert "Fulfillment" in rendered
    assert "Unavailable" in rendered
    assert "Reliability" in rendered
    assert "Healthy (0 failures)" in rendered
    assert "composite" not in rendered.lower()
