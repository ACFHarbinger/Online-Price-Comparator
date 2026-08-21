"""Scraper adapter for CHIP7 Portugal search results."""

from __future__ import annotations

from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig

_CONFIG = RetailerParserConfig(
    site_key="chip7",
    display_name="CHIP7",
    base_url="https://chip7.pt",
    search_url_template="https://chip7.pt/?query={query}",
    card_selector="article[data-testid*='product'], .product-card, .ais-Hits-item",
    title_selector="[data-testid*='product-name'], .product-name, h2, h3",
    price_selector="[data-testid*='price'], .price, .product-price",
    link_selector="a[href]",
)


class Chip7Scraper(IberianRetailerScraper):
    """Fetch CHIP7 listings using safe shared retailer-scraper behaviour."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)
