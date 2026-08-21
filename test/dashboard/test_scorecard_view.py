"""Unit and component integration tests for site scorecard dashboard view (v2.16)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import Engine

from dashboard.callbacks import (
    _build_scorecard_table,
    _format_scorecard_cell,
    _product_view,
    _scorecard_panel_view,
)
from scoring.scorecard import Dimension, SiteScorecard
from storage.repository import (
    ListingRepository,
    PriceHistoryRepository,
    ProductRepository,
)


def test_format_scorecard_cell_ok() -> None:
    # 1. Extreme value ok
    dim_ev = Dimension(
        name="extreme_value",
        value=20.0,
        detail="latest sticker at the 20th percentile",
        confidence="ok",
    )
    cell_ev = cast(Any, _format_scorecard_cell(dim_ev))
    assert len(cell_ev.children) == 2
    assert cell_ev.children[0].children == "20th percentile"
    assert "scorecard-dim-ok" in cell_ev.children[0].className
    assert cell_ev.children[1].children == "latest sticker at the 20th percentile"

    # 2. Reliability ok
    dim_rel = Dimension(
        name="reliability",
        value=0.0,
        detail="no consecutive fetch failures",
        confidence="ok",
    )
    cell_rel = cast(Any, _format_scorecard_cell(dim_rel))
    assert cell_rel.children[0].children == "Healthy (0 failures)"


def test_format_scorecard_cell_low_confidence() -> None:
    dim = Dimension(
        name="extreme_value",
        value=None,
        detail="not enough same-condition sites yet",
        confidence="low",
    )
    cell = cast(Any, _format_scorecard_cell(dim))
    assert cell.children[0].children == "— (Low conf)"
    assert "scorecard-dim-low" in cell.children[0].className


def test_format_scorecard_cell_unavailable() -> None:
    dim = Dimension(
        name="fulfillment_sla",
        value=None,
        detail="no delivery estimates persisted yet (v2.13)",
        confidence="unavailable",
    )
    cell = cast(Any, _format_scorecard_cell(dim))
    assert cell.children[0].children == "Unavailable"
    assert "scorecard-dim-unavail" in cell.children[0].className


def test_build_scorecard_table_no_composite() -> None:
    card = SiteScorecard(
        site_key="amazon_es",
        site_display_name="Amazon.es",
        condition="new",
        extreme_value=Dimension("extreme_value", 10.0, "rank 10", "ok"),
        consistency=Dimension("consistency", 15.0, "rank 15", "ok"),
        fulfillment_sla=Dimension("fulfillment_sla", None, "v2.13", "unavailable"),
        reliability=Dimension("reliability", 0.0, "0 failures", "ok"),
    )
    table = cast(Any, _build_scorecard_table([card]))
    assert "scorecard-table" in table.className

    # Verify headers
    thead = table.children[0]
    th_texts = [th.children for th in thead.children.children]
    assert "Retailer" in th_texts
    assert "Condition" in th_texts
    assert "Extreme Value (Price Rank)" in th_texts
    assert "Consistency (Median / CV)" in th_texts
    assert "Fulfillment SLA" in th_texts
    assert "Reliability (Circuit Health)" in th_texts

    # Explicit check: no composite header or attribute exists
    assert not any("composite" in str(th).lower() for th in th_texts)

    # Verify body row
    tbody = table.children[1]
    row = tbody.children[0]
    assert len(row.children) == 6


def test_scorecard_panel_view_empty_and_populated(in_memory_engine: Engine) -> None:
    # 1. None product id
    unselected = cast(Any, _scorecard_panel_view(None, in_memory_engine))
    assert "Choose a product" in unselected.children

    # 2. Product with no prices
    prod_repo = ProductRepository(in_memory_engine)
    prod_id = prod_repo.get_or_create("RTX 4090")
    empty_prod = cast(Any, _scorecard_panel_view(prod_id, in_memory_engine))
    assert "No same-condition price histories available" in empty_prod.children

    # 3. Product with 2 sites with same-condition EUR prices
    listing_repo = ListingRepository(in_memory_engine)
    price_repo = PriceHistoryRepository(in_memory_engine)

    l1 = listing_repo.upsert(
        product_id=prod_id,
        site_key="amazon_es",
        site_display_name="Amazon.es",
        url="https://amazon.es/dp/1",
        image_url=None,
        seen_at=datetime.now(),
        match_status="confirmed",
        match_score=1.0,
        match_reason="test",
        condition="new",
    )
    l2 = listing_repo.upsert(
        product_id=prod_id,
        site_key="pccomponentes",
        site_display_name="PcComponentes",
        url="https://pccomponentes.com/dp/2",
        image_url=None,
        seen_at=datetime.now(),
        match_status="confirmed",
        match_score=1.0,
        match_reason="test",
        condition="new",
    )

    now = datetime.now()
    price_repo.add(
        listing_id=l1,
        price_amount=1800.0,
        currency="EUR",
        observed_at=now - timedelta(days=2),
        raw_price_text="1800.00",
        price_eur_equivalent=1800.0,
        condition="new",
    )
    price_repo.add(
        listing_id=l2,
        price_amount=1950.0,
        currency="EUR",
        observed_at=now - timedelta(days=2),
        raw_price_text="1950.00",
        price_eur_equivalent=1950.0,
        condition="new",
    )

    panel = cast(Any, _scorecard_panel_view(prod_id, in_memory_engine))
    assert "scorecard-table" in panel.className
    tbody = panel.children[1]
    assert len(tbody.children) == 2


def test_product_view_includes_scorecard_panel(in_memory_engine: Engine) -> None:
    prod_repo = ProductRepository(in_memory_engine)
    listing_repo = ListingRepository(in_memory_engine)
    price_repo = PriceHistoryRepository(in_memory_engine)

    prod_id = prod_repo.get_or_create("Intel Core i7-14700K")
    result = _product_view(
        prod_id,
        False,
        prod_repo,
        listing_repo,
        price_repo,
    )
    assert len(result) == 10
    scorecard_panel = cast(Any, result[9])
    assert "No same-condition price histories available" in scorecard_panel.children
