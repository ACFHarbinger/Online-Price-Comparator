"""Scraper adapter for PCDIGA Portugal search results."""

from __future__ import annotations

from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig

_CONFIG = RetailerParserConfig(
    site_key="pcdiga",
    display_name="PCDIGA",
    base_url="https://www.pcdiga.com",
    search_url_template="https://www.pcdiga.com/search?query={query}",
    card_selector=".product-item, .product-card, article[data-testid*='product']",
    title_selector=".product-item-link, .product-name, [data-testid*='product-name']",
    price_selector="[data-price-amount], .price, .product-price",
    link_selector="a.product-item-link[href], a[href]",
)


class PcdigaScraper(IberianRetailerScraper):
    """Fetch PCDIGA listings using safe shared retailer-scraper behaviour."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)
