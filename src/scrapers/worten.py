"""Scraper adapter for Worten Portugal search results."""

from __future__ import annotations

from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig

_CONFIG = RetailerParserConfig(
    site_key="worten",
    display_name="Worten",
    base_url="https://www.worten.pt",
    search_url_template="https://www.worten.pt/search?query={query}",
    card_selector=(
        "article[data-testid*='product'], .product-card, [data-testid*='product-card']"
    ),
    title_selector="[data-testid*='product-name'], .product-name, h2, h3",
    price_selector="[data-testid*='price'], .price, .product-price",
    link_selector="a[href]",
)


class WortenScraper(IberianRetailerScraper):
    """Fetch Worten listings using safe shared retailer-scraper behaviour."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)
