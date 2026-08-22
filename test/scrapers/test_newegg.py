"""Fixture-backed tests for the v2.13 Newegg global-tier source."""

from __future__ import annotations

from pathlib import Path

from config.settings import Settings
from scrapers.landed_cost import estimate_newegg_portugal_landed_cost
from scrapers.newegg import NeweggScraper
from scrapers.registry import enabled_scrapers

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "html" / "newegg"


def _fixture(name: str) -> str:
    return (FIXTURE_ROOT / name).read_text(encoding="utf-8")


def test_newegg_prefers_json_ld_and_attaches_landed_cost_estimate() -> None:
    listings = NeweggScraper()._listings_from_html(
        _fixture("structured_search.html"), limit=20
    )

    assert len(listings) == 1
    listing = listings[0]
    assert listing.title == "Newegg JSON-LD DDR5 RAM"
    assert listing.url == "https://www.newegg.com/p/N82E16800000001"
    assert listing.currency_hint == "USD"
    assert listing.extra["parser"] == "json_ld"
    assert listing.extra["import_regime"] == "row"
    estimate = listing.extra["landed_cost_estimate"]
    assert estimate["currency"] == "USD"
    assert estimate["estimated_total_range"] == [179, 212]
    assert estimate["label"] == "Estimated Portugal landed cost — confirm at checkout"


def test_newegg_css_fallback_attaches_landed_cost_estimate() -> None:
    listings = NeweggScraper()._listings_from_html(
        _fixture("css_search.html"), limit=20
    )

    assert len(listings) == 1
    listing = listings[0]
    assert listing.title == "Newegg CSS DDR5 RAM"
    assert listing.url == "https://www.newegg.com/p/N82E16800000002"
    assert listing.image_url == "https://www.newegg.com/images/ddr5-css.jpg"
    assert listing.extra["parser"] == "css"
    assert listing.extra["import_regime"] == "row"
    assert listing.extra["landed_cost_estimate"]["estimated_total_range"] == [142, 175]


def test_newegg_landed_cost_estimate_rejects_non_usd_or_non_positive_price() -> None:
    assert estimate_newegg_portugal_landed_cost(100.0, "EUR") is None
    assert estimate_newegg_portugal_landed_cost(0.0, "USD") is None


def test_newegg_is_registered() -> None:
    keys = [scraper.site_key for scraper in enabled_scrapers(Settings())]
    assert "newegg" in keys
