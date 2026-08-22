"""Tests verifying dashboard ad-hoc search enforces site_settings and overrides."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import patch

from dash import Dash
from sqlalchemy import Engine

from dashboard.callbacks import register_callbacks
from models.listing import RawListing
from storage.schema import site_settings
from storage.watchlist import (
    SiteOverrideRepository,
    SiteSettingsRepository,
    TrackedProductRepository,
)


class _FakeScraper:
    """A scraper test double that records calls."""

    def __init__(self, site_key: str) -> None:
        self.site_key = site_key
        self.called = False

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        self.called = True
        return [
            RawListing(
                source=self.site_key,
                source_kind="scraper",
                title=f"{query} {self.site_key}",
                url=f"https://{self.site_key}/item/123",
                price_text="100 €",
                currency_hint="EUR",
                image_url=None,
                site_display_name=self.site_key.title(),
                fetched_at=datetime.now(),
            )
        ]


def _find_select_product(dash_app: Dash) -> Any:
    for k, v in dash_app.callback_map.items():
        if "selected-product-id" in k:
            cb = v["callback"]
            return getattr(cb, "__wrapped__", cb)
    raise RuntimeError("select_product callback not found")


def test_dashboard_search_respects_globally_disabled_site(
    in_memory_engine: Engine, monkeypatch: Any
) -> None:
    amazon = _FakeScraper("amazon.es")
    pcc = _FakeScraper("pccomponentes")
    monkeypatch.setattr(
        "pipeline.discover.enabled_scrapers",
        lambda settings: [amazon, pcc],
    )

    # Disable amazon.es globally in site_settings
    settings_repo = SiteSettingsRepository(in_memory_engine)
    settings_repo.set_enabled("amazon.es", False)

    app = Dash(__name__)
    register_callbacks(app, in_memory_engine)
    select_product = _find_select_product(app)

    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "product-search-button"
        product_id, _options, selected_id = select_product(
            1, None, None, None, "AMD Ryzen 9 9950X3D", []
        )

    assert amazon.called is False
    assert pcc.called is True
    assert product_id is not None
    assert selected_id == product_id


def test_dashboard_search_respects_client_extension_collection_method(
    in_memory_engine: Engine, monkeypatch: Any
) -> None:
    amazon = _FakeScraper("amazon.es")
    pcc = _FakeScraper("pccomponentes")
    monkeypatch.setattr(
        "pipeline.discover.enabled_scrapers",
        lambda settings: [amazon, pcc],
    )

    # Flag amazon.es as client_extension
    with in_memory_engine.begin() as conn:
        conn.execute(
            site_settings.insert().values(
                site_key="amazon.es",
                enabled=True,
                collection_method="client_extension",
            )
        )

    app = Dash(__name__)
    register_callbacks(app, in_memory_engine)
    select_product = _find_select_product(app)

    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "product-search-button"
        _pid, _opt, _sel = select_product(
            1, None, None, None, "Corsair Vengeance 64GB DDR5", []
        )

    assert amazon.called is False
    assert pcc.called is True


def test_dashboard_search_respects_tracked_product_site_override(
    in_memory_engine: Engine, monkeypatch: Any
) -> None:
    amazon = _FakeScraper("amazon.es")
    pcc = _FakeScraper("pccomponentes")
    monkeypatch.setattr(
        "pipeline.discover.enabled_scrapers",
        lambda settings: [amazon, pcc],
    )

    # Track a product and disable pccomponentes specifically for it
    tracked_repo = TrackedProductRepository(in_memory_engine)
    tracked = tracked_repo.get_or_create("Crucial P310 4TB SSD")

    override_repo = SiteOverrideRepository(in_memory_engine)
    override_repo.set_override(tracked.id, "pccomponentes", included=False)

    app = Dash(__name__)
    register_callbacks(app, in_memory_engine)
    select_product = _find_select_product(app)

    with patch("dashboard.callbacks.ctx") as mock_ctx:
        mock_ctx.triggered_id = "product-search-button"
        _pid, _opt, _sel = select_product(
            1, None, None, None, "Crucial P310 4TB SSD", []
        )

    assert amazon.called is True
    assert pcc.called is False
