"""Fixture-backed JSON-LD and CSS parsing tests for Portuguese retailers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scrapers.fnac import FnacScraper
from scrapers.pcdiga import PcdigaScraper
from scrapers.worten import WortenScraper

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "html"


def _fixture(*parts: str) -> str:
    return FIXTURE_ROOT.joinpath(*parts).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("scraper", "site", "expected_title", "expected_url"),
    [
        (
            PcdigaScraper(),
            "pcdiga",
            "PCDIGA JSON-LD graphics card",
            "https://www.pcdiga.com/componentes/gpu-json-ld",
        ),
        (
            WortenScraper(),
            "worten",
            "Worten JSON-LD laptop",
            "https://www.worten.pt/produtos/laptop-json",
        ),
        (
            FnacScraper(),
            "fnac",
            "Fnac JSON-LD monitor",
            "https://www.fnac.pt/Monitor-json",
        ),
    ],
)
def test_retailer_prefers_complete_json_ld(
    scraper: PcdigaScraper | WortenScraper | FnacScraper,
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
            PcdigaScraper(),
            "pcdiga",
            "PCDIGA CSS SSD",
            "https://www.pcdiga.com/componentes/ssd-css",
            "https://www.pcdiga.com/images/ssd-css.jpg",
        ),
        (
            WortenScraper(),
            "worten",
            "Worten CSS router",
            "https://www.worten.pt/produtos/router-css",
            "https://www.worten.pt/images/router-css.jpg",
        ),
        (
            FnacScraper(),
            "fnac",
            "Fnac CSS monitor",
            "https://www.fnac.pt/Monitor-css",
            "https://www.fnac.pt/images/monitor-css.jpg",
        ),
    ],
)
def test_retailer_falls_back_to_css(
    scraper: PcdigaScraper | WortenScraper | FnacScraper,
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
