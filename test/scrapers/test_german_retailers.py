"""Fixture-backed parsing tests for the first EU-wide retail adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings
from scrapers.alternate import AlternateScraper
from scrapers.mindfactory import MindfactoryScraper
from scrapers.registry import enabled_scrapers

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "html"


def _fixture(*parts: str) -> str:
    return FIXTURE_ROOT.joinpath(*parts).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("scraper", "site", "expected_title", "expected_url"),
    [
        (
            MindfactoryScraper(),
            "mindfactory",
            "Mindfactory JSON-LD graphics card",
            "https://www.mindfactory.de/product/rtx-json",
        ),
        (
            AlternateScraper(),
            "alternate",
            "Alternate JSON-LD monitor",
            "https://www.alternate.de/Monitor-json",
        ),
    ],
)
def test_german_retailer_prefers_complete_json_ld(
    scraper: MindfactoryScraper | AlternateScraper,
    site: str,
    expected_title: str,
    expected_url: str,
) -> None:
    listings = scraper._listings_from_html(
        _fixture(site, "structured_search.html"), limit=20
    )

    assert len(listings) == 1
    assert listings[0].title == expected_title
    assert listings[0].url == expected_url
    assert listings[0].currency_hint == "EUR"
    assert listings[0].extra["parser"] == "json_ld"


@pytest.mark.parametrize(
    ("scraper", "site", "expected_title", "expected_url", "expected_image"),
    [
        (
            MindfactoryScraper(),
            "mindfactory",
            "Mindfactory CSS SSD",
            "https://www.mindfactory.de/product/ssd-css",
            "https://www.mindfactory.de/images/ssd-css.jpg",
        ),
        (
            AlternateScraper(),
            "alternate",
            "Alternate CSS monitor",
            "https://www.alternate.de/Monitor-css",
            "https://www.alternate.de/images/monitor-css.jpg",
        ),
    ],
)
def test_german_retailer_falls_back_to_css(
    scraper: MindfactoryScraper | AlternateScraper,
    site: str,
    expected_title: str,
    expected_url: str,
    expected_image: str,
) -> None:
    listings = scraper._listings_from_html(_fixture(site, "css_search.html"), limit=20)

    assert len(listings) == 1
    assert listings[0].title == expected_title
    assert listings[0].url == expected_url
    assert listings[0].image_url == expected_image
    assert listings[0].extra["parser"] == "css"


def test_german_retailers_are_registered() -> None:
    keys = [scraper.site_key for scraper in enabled_scrapers(Settings())]
    assert "mindfactory" in keys
    assert "alternate" in keys
