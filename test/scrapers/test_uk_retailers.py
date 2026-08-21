"""Fixture-backed parsing tests for UK-import retailer adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.settings import Settings
from scrapers.overclockers import OverclockersScraper
from scrapers.registry import enabled_scrapers
from scrapers.scan import ScanScraper

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "html"


def _fixture(*parts: str) -> str:
    return FIXTURE_ROOT.joinpath(*parts).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("scraper", "site", "expected_title", "expected_url"),
    [
        (
            ScanScraper(),
            "scan",
            "Scan JSON-LD graphics card",
            "https://www.scan.co.uk/products/rtx-json",
        ),
        (
            OverclockersScraper(),
            "overclockers",
            "Overclockers JSON-LD monitor",
            "https://www.overclockers.co.uk/monitors/json",
        ),
    ],
)
def test_uk_retailer_prefers_json_ld_and_marks_uk_import(
    scraper: ScanScraper | OverclockersScraper,
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
    assert listings[0].currency_hint == "GBP"
    assert listings[0].extra["parser"] == "json_ld"
    assert listings[0].extra["import_regime"] == "uk_import"


@pytest.mark.parametrize(
    ("scraper", "site", "expected_title", "expected_url", "expected_image"),
    [
        (
            ScanScraper(),
            "scan",
            "Scan CSS SSD",
            "https://www.scan.co.uk/products/ssd-css",
            "https://www.scan.co.uk/images/ssd-css.jpg",
        ),
        (
            OverclockersScraper(),
            "overclockers",
            "Overclockers CSS monitor",
            "https://www.overclockers.co.uk/monitors/css",
            "https://www.overclockers.co.uk/images/monitor-css.jpg",
        ),
    ],
)
def test_uk_retailer_falls_back_to_css_and_marks_uk_import(
    scraper: ScanScraper | OverclockersScraper,
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
    assert listings[0].extra["import_regime"] == "uk_import"


def test_uk_retailers_are_registered() -> None:
    keys = [scraper.site_key for scraper in enabled_scrapers(Settings())]
    assert "scan.co.uk" in keys
    assert "overclockers.co.uk" in keys
