"""Scraper adapter for Scan.co.uk search results."""

from __future__ import annotations

from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig

_CONFIG = RetailerParserConfig(
    site_key="scan.co.uk",
    display_name="Scan.co.uk",
    base_url="https://www.scan.co.uk",
    search_url_template="https://www.scan.co.uk/search?q={query}",
    card_selector=(
        "article, .product-card, .product-list-item, [data-testid*='product']"
    ),
    title_selector=".product-name, [data-testid*='product-name'], h2, h3",
    price_selector=".price, .product-price, [data-price-amount]",
    link_selector="a[href]",
    accept_language="en-GB,en;q=0.9",
    import_regime="uk_import",
)


class ScanScraper(IberianRetailerScraper):
    """Fetch Scan.co.uk listings as UK-import observations."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)
