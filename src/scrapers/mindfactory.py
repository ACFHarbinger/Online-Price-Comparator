"""Scraper adapter for Mindfactory.de search results."""

from __future__ import annotations

from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig

_CONFIG = RetailerParserConfig(
    site_key="mindfactory",
    display_name="Mindfactory.de",
    base_url="https://www.mindfactory.de",
    search_url_template="https://www.mindfactory.de/search_result.php?search_query={query}",
    card_selector=(
        ".psearch-results .product, .product-item, article[data-testid*='product']"
    ),
    title_selector=".psearch-results h2, .product-name, h2, h3",
    price_selector=".price, .product-price, [data-price-amount]",
    link_selector="a[href]",
    accept_language="de-DE,de;q=0.9,en;q=0.7",
)


class MindfactoryScraper(IberianRetailerScraper):
    """Fetch Mindfactory.de listings using shared polite retailer behaviour."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)
