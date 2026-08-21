"""Scraper adapter for Alternate.de search results."""

from __future__ import annotations

from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig

_CONFIG = RetailerParserConfig(
    site_key="alternate",
    display_name="Alternate.de",
    base_url="https://www.alternate.de",
    search_url_template="https://www.alternate.de/listing.xhtml?q={query}",
    card_selector="article, .product-card, .list-item, [data-testid*='product']",
    title_selector=".product-name, [data-testid*='product-name'], h2, h3",
    price_selector=".price, .product-price, [data-price-amount]",
    link_selector="a[href]",
    accept_language="de-DE,de;q=0.9,en;q=0.7",
)


class AlternateScraper(IberianRetailerScraper):
    """Fetch Alternate.de listings using shared polite retailer behaviour."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)
