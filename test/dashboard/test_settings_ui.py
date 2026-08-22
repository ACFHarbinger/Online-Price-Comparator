"""Tests for the dashboard settings UI (tracked products, site settings, overrides)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import patch

from dash import Dash
from sqlalchemy import create_engine

from dashboard.callbacks import (
    _site_overrides_panel,
    _site_settings_panel,
    _tracked_products_panel,
    register_callbacks,
)
from scrapers.base import ScraperAdapter
from storage.schema import metadata
from storage.watchlist import (
    SiteSetting,
    TrackedProduct,
    TrackedProductRepository,
)


class DummyScraper:
    site_key = "dummy_store"
    site_display_name = "Dummy Store"

    def search(self, query: str, *, limit: int = 20) -> list[Any]:
        return []


def test_tracked_products_panel_empty() -> None:
    panel = _tracked_products_panel([])
    assert panel is not None
    panel_any = cast(Any, panel)
    assert "empty-message" in panel_any.className
    assert "No tracked products" in panel_any.children


def test_tracked_products_panel_rendered() -> None:
    now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)
    tracked = [
        TrackedProduct(
            id=1,
            product_id=10,
            query_text="AMD Ryzen 7 7800X3D",
            canonical_name="AMD Ryzen 7 7800X3D",
            enabled=True,
            refresh_interval_hours=24,
            target_price=350.0,
            target_currency="EUR",
            search_scope_tier="local",
            historical_low_alert_mode="tiered",
            rarity_percentile=5.0,
            rarity_window_days=90,
            rarity_min_observations=10,
            created_at=now,
            last_checked_at=now,
        ),
        TrackedProduct(
            id=2,
            product_id=20,
            query_text="Corsair DDR5 32GB",
            canonical_name="Corsair DDR5 32GB",
            enabled=False,
            refresh_interval_hours=None,
            target_price=None,
            target_currency=None,
            search_scope_tier="eu_wide",
            historical_low_alert_mode="tiered",
            rarity_percentile=None,
            rarity_window_days=None,
            rarity_min_observations=None,
            created_at=now,
            last_checked_at=None,
        ),
    ]

    panel = _tracked_products_panel(tracked, as_of=now)
    assert panel is not None
    panel_any = cast(Any, panel)
    assert panel_any.className == "settings-table"

    tbody = panel_any.children[1]
    assert len(tbody.children) == 2

    row1_cells = tbody.children[0].children
    assert row1_cells[0].children == "AMD Ryzen 7 7800X3D"
    assert row1_cells[1].children.children == "LOCAL"
    assert row1_cells[2].children.children == "Active"
    assert row1_cells[4].children[0].children == "Pause"
    assert row1_cells[4].children[1].children == "Untrack"

    row2_cells = tbody.children[1].children
    assert row2_cells[0].children == "Corsair DDR5 32GB"
    assert row2_cells[1].children.children == "EU_WIDE"
    assert row2_cells[2].children.children == "Paused"
    assert row2_cells[3].children == "Never"
    assert row2_cells[4].children[0].children == "Resume"


def test_site_settings_panel_rendered() -> None:
    scrapers: list[ScraperAdapter] = [cast(ScraperAdapter, DummyScraper())]
    persisted = [
        SiteSetting(
            site_key="dummy_store",
            enabled=True,
            result_limit=20,
            min_request_interval_seconds=10,
            cache_ttl_seconds=3600,
            browser_rendering_allowed=False,
            min_refresh_interval_hours=24,
            shipping_cost_estimate_eur=4.99,
            collection_method="server_scrape",
        )
    ]
    disabled_keys: set[str] = set()
    shipping_estimates = {"dummy_store": 4.99}

    panel = _site_settings_panel(scrapers, persisted, disabled_keys, shipping_estimates)
    assert panel is not None
    panel_any = cast(Any, panel)
    tbody = panel_any.children[1]
    row = tbody.children[0]
    cells = row.children

    assert cells[0].children == "Dummy Store"
    assert cells[1].children.children == "dummy_store"
    assert cells[2].children.children == "server_scrape"
    assert cells[3].children == "€4.99"
    assert cells[4].children.children == "Enabled"
    assert cells[5].children.children == "Disable"


def test_site_overrides_panel_unselected() -> None:
    scrapers: list[ScraperAdapter] = [cast(ScraperAdapter, DummyScraper())]
    panel = _site_overrides_panel(scrapers, {}, None, set())
    assert panel is not None
    panel_any = cast(Any, panel)
    assert "empty-message" in panel_any.className
    assert "Select a tracked product" in panel_any.children


def test_site_overrides_panel_with_and_without_override() -> None:
    now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC)
    tracked = TrackedProduct(
        id=1,
        product_id=10,
        query_text="AMD Ryzen 7 7800X3D",
        canonical_name="AMD Ryzen 7 7800X3D",
        enabled=True,
        refresh_interval_hours=24,
        target_price=350.0,
        target_currency="EUR",
        search_scope_tier="local",
        historical_low_alert_mode="tiered",
        rarity_percentile=5.0,
        rarity_window_days=90,
        rarity_min_observations=10,
        created_at=now,
        last_checked_at=now,
    )
    scrapers: list[ScraperAdapter] = [cast(ScraperAdapter, DummyScraper())]

    # Without override
    panel = _site_overrides_panel(scrapers, {}, tracked, set())
    panel_any = cast(Any, panel)
    row = panel_any.children[1].children[0]
    cells = row.children
    assert cells[2].children.children == "Follows Default"
    action_div = cells[3].children
    assert action_div.children[0].children == "Include"
    assert action_div.children[1].children == "Exclude"

    # With override
    panel_ov = _site_overrides_panel(scrapers, {"dummy_store": False}, tracked, set())
    panel_ov_any = cast(Any, panel_ov)
    row_ov = panel_ov_any.children[1].children[0]
    cells_ov = row_ov.children
    assert cells_ov[2].children.children == "Forced Exclude"
    assert cells_ov[3].children.children == "Clear Override"


def _find_manage_settings(dash_app: Dash) -> Any:
    for k, v in dash_app.callback_map.items():
        if "tracked-products-table-container" in k:
            cb = v["callback"]
            return getattr(cb, "__wrapped__", cb)
    raise RuntimeError("manage_settings callback not found")


def test_manage_settings_ui_callback() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)

    tracked_repo = TrackedProductRepository(engine)
    tp = tracked_repo.get_or_create("RTX 4080 Super")

    app = Dash(__name__)
    register_callbacks(app, engine)
    cb_func = _find_manage_settings(app)

    # 1. Initial load
    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "tracked-products-loader"
        res = cb_func(tp.product_id, 1, [], [], [], [], [])
        assert len(res) == 5
        tracked_table, site_table, _ov_table, _status_msg, _status_style = res
        assert tracked_table is not None
        assert site_table is not None

    # 2. Toggle tracked product enable/disable
    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {"type": "toggle-tracked-btn", "index": tp.id}
        res = cb_func(tp.product_id, 1, [1], [], [], [], [])
        status_msg = res[3]
        assert "Paused tracking" in status_msg

    # 3. Toggle site enable/disable
    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {"type": "toggle-site-btn", "index": "amazon.es"}
        res = cb_func(tp.product_id, 1, [], [], [1], [], [])
        status_msg = res[3]
        assert "Disabled scraper for amazon.es" in status_msg

    # 4. Set per-product site override
    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {
            "type": "set-override-btn",
            "index": f"{tp.id}:amazon.es:include",
        }
        res = cb_func(tp.product_id, 1, [], [], [], [1], [])
        status_msg = res[3]
        assert "Set override: amazon.es is included" in status_msg

    # 5. Clear per-product site override
    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {
            "type": "clear-override-btn",
            "index": f"{tp.id}:amazon.es",
        }
        res = cb_func(tp.product_id, 1, [], [], [], [], [1])
        status_msg = res[3]
        assert "Cleared override for amazon.es" in status_msg

    # 6. Untrack product
    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = {"type": "untrack-product-btn", "index": tp.id}
        res = cb_func(tp.product_id, 1, [], [1], [], [], [])
        status_msg = res[3]
        assert "Removed product from tracked watchlist" in status_msg
