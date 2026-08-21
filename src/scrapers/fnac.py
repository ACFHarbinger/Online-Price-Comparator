"""Scraper adapter for Fnac.pt search results."""

from __future__ import annotations

from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig

_CONFIG = RetailerParserConfig(
    site_key="fnac",
    display_name="Fnac.pt",
    base_url="https://www.fnac.pt",
    search_url_template="https://www.fnac.pt/SearchResult/ResultList.aspx?Search={query}",
    card_selector=".Article-item, .product-card, article[data-testid*='product']",
    title_selector=(
        ".Article-item-title, .product-name, [data-testid*='product-name'], h2, h3"
    ),
    price_selector=".Article-item-price, .price, [data-testid*='price']",
    link_selector="a[href]",
)


class FnacScraper(IberianRetailerScraper):
    """Fetch Fnac.pt listings using safe shared retailer-scraper behaviour."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)
