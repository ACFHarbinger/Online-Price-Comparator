"""Structured-data-first and CSS fallback tests for retailer scrapers."""

from __future__ import annotations

from pathlib import Path

from scrapers.amazon import AmazonScraper
from scrapers.pccomponentes import PcComponentesScraper

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "html"


def _fixture(*parts: str) -> str:
    return FIXTURE_ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_amazon_prefers_json_ld_over_css() -> None:
    listings = AmazonScraper()._listings_from_html(
        _fixture("amazon_es", "structured_search.html"), limit=20
    )

    assert len(listings) == 1
    listing = listings[0]
    assert listing.title == "AMD Ryzen 9 9950X3D JSON-LD"
    assert listing.price_text == "599.99"
    assert listing.currency_hint == "EUR"
    assert listing.url == "https://www.amazon.es/dp/B0STRUCT01"
    assert listing.image_url == "https://www.amazon.es/images/9950x3d.jpg"


def test_amazon_falls_back_to_existing_css_fixture() -> None:
    listings = AmazonScraper()._listings_from_html(
        _fixture("amazon_es", "sample_search.html"), limit=1
    )

    assert len(listings) == 1
    assert listings[0].title.startswith("AMD Ryzen 9 9950X3D")
    assert listings[0].price_text == "609,82\xa0€"
    assert listings[0].extra["asin"] == "B0DVZSG8D5"


def test_amazon_falls_back_when_json_ld_is_malformed() -> None:
    html = """
    <script type="application/ld+json">{"@type": "Product", broken}</script>
    <div data-component-type="s-search-result" data-asin="B0FALLBACK">
      <h2 aria-label="Fallback product"></h2>
      <a href="/dp/B0FALLBACK"></a>
      <span class="a-price"><span class="a-offscreen">10,00 €</span></span>
    </div>
    """

    listings = AmazonScraper()._listings_from_html(html, limit=20)

    assert len(listings) == 1
    assert listings[0].title == "Fallback product"


def test_pccomponentes_prefers_json_ld_over_css() -> None:
    listings = PcComponentesScraper()._listings_from_html(
        _fixture("pccomponentes", "structured_search.html"), limit=20
    )

    assert len(listings) == 1
    listing = listings[0]
    assert listing.title == "GeForce RTX 5090 JSON-LD"
    assert listing.price_text == "2499.9"
    assert listing.currency_hint == "EUR"
    assert listing.url == "https://www.pccomponentes.pt/placa-grafica/rtx-5090"
    assert listing.image_url == "https://cdn.pccomponentes.com/rtx5090.jpg"


def test_pccomponentes_falls_back_to_css_without_json_ld() -> None:
    listings = PcComponentesScraper()._listings_from_html(
        _fixture("pccomponentes", "css_search.html"), limit=20
    )

    assert len(listings) == 1
    listing = listings[0]
    assert listing.title == "Portátil CSS only"
    assert listing.price_text == "1.299,00 €"
    assert listing.currency_hint == "EUR"
    assert listing.url == "https://www.pccomponentes.pt/portatil/css-only"
    assert listing.image_url == "https://www.pccomponentes.pt/images/css-only.jpg"


def test_incomplete_json_ld_falls_back_to_pccomponentes_css() -> None:
    html = """
    <script type="application/ld+json">
      {"@type": "Product", "name": "No offer or URL"}
    </script>
    <a href="/fallback"><article class="product-card">
      <span data-e2e="title-card">Fallback card</span>
      <span data-e2e="price-card">20,00 €</span>
    </article></a>
    """

    listings = PcComponentesScraper()._listings_from_html(html, limit=20)

    assert len(listings) == 1
    assert listings[0].title == "Fallback card"
