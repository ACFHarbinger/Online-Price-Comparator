"""CHIP7 listing and KuantoKusta non-authoritative hint-source tests."""

from __future__ import annotations

from pathlib import Path

from config.settings import Settings
from scrapers.chip7 import Chip7Scraper
from scrapers.kuantokusta import KuantoKustaHintSource, RetailerUrlHint
from scrapers.registry import enabled_hint_sources, enabled_scrapers

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "html"


def _fixture(*parts: str) -> str:
    return FIXTURE_ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_chip7_prefers_complete_json_ld() -> None:
    listings = Chip7Scraper()._listings_from_html(
        _fixture("chip7", "structured_search.html"), limit=20
    )

    assert len(listings) == 1
    assert listings[0].title == "CHIP7 JSON-LD processor"
    assert listings[0].url == "https://chip7.pt/processador-json"
    assert listings[0].price_text == "334.90"
    assert listings[0].extra["parser"] == "json_ld"


def test_chip7_falls_back_to_css() -> None:
    listings = Chip7Scraper()._listings_from_html(
        _fixture("chip7", "css_search.html"), limit=20
    )

    assert len(listings) == 1
    assert listings[0].title == "CHIP7 CSS graphics card"
    assert listings[0].url == "https://chip7.pt/placa-grafica-css"
    assert listings[0].image_url == "https://chip7.pt/images/placa-grafica-css.jpg"
    assert listings[0].extra["parser"] == "css"


def test_kuantokusta_emits_only_external_retailer_url_hints() -> None:
    hints = KuantoKustaHintSource()._hints_from_html(
        _fixture("kuantokusta", "hints.html"), limit=20
    )

    assert [hint.destination_url for hint in hints] == [
        "https://www.pcdiga.com/placa-grafica/candidate",
        "https://chip7.pt/candidate",
    ]
    assert all(isinstance(hint, RetailerUrlHint) for hint in hints)
    assert all(not hasattr(hint, "price_text") for hint in hints)


def test_kuantokusta_is_not_a_price_scraper() -> None:
    settings = Settings()

    assert "kuantokusta" not in [
        scraper.site_key for scraper in enabled_scrapers(settings)
    ]
    assert [source.site_key for source in enabled_hint_sources(settings)] == [
        "kuantokusta"
    ]
