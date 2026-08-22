"""Tests for collection_method enforcement in discovery (v2.20)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine

from config.settings import Settings
from pipeline.discover import run_discovery
from storage.schema import site_settings


class _FakeScraper:
    """A scraper-shaped test double that records whether it was queried."""

    def __init__(self, site_key: str) -> None:
        self.site_key = site_key
        self.called = False

    def search(self, query: str, *, limit: int = 20) -> list[Any]:
        self.called = True
        return []


def _set_collection_method(engine: Engine, site_key: str, method: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            site_settings.insert().values(
                site_key=site_key,
                enabled=True,
                collection_method=method,
            )
        )


def test_discovery_excludes_client_extension_site(
    in_memory_engine: Engine, monkeypatch: Any
) -> None:
    amazon = _FakeScraper("amazon.es")
    pcc = _FakeScraper("pccomponentes")
    monkeypatch.setattr(
        "pipeline.discover.enabled_scrapers",
        lambda settings: [amazon, pcc],
    )
    # amazon.es is collected via the browser extension - never server-scraped.
    _set_collection_method(in_memory_engine, "amazon.es", "client_extension")

    settings = Settings(_env_file=None, enabled_scrapers="amazon.es,pccomponentes")  # type: ignore[call-arg]
    run_discovery("AMD Ryzen 9 9950X3D", settings, engine=in_memory_engine)

    assert amazon.called is False
    assert pcc.called is True


def test_discovery_still_scrapes_default_site(
    in_memory_engine: Engine, monkeypatch: Any
) -> None:
    amazon = _FakeScraper("amazon.es")
    pcc = _FakeScraper("pccomponentes")
    monkeypatch.setattr(
        "pipeline.discover.enabled_scrapers",
        lambda settings: [amazon, pcc],
    )
    # A site with no site_settings row (default server_scrape) is still scraped.
    settings = Settings(_env_file=None, enabled_scrapers="amazon.es,pccomponentes")  # type: ignore[call-arg]
    run_discovery("AMD Ryzen 9 9950X3D", settings, engine=in_memory_engine)

    assert amazon.called is True
    assert pcc.called is True
