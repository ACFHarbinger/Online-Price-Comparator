"""Scraper adapter for Overclockers UK search results."""

from __future__ import annotations

from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig

_CONFIG = RetailerParserConfig(
    site_key="overclockers.co.uk",
    display_name="Overclockers UK",
    base_url="https://www.overclockers.co.uk",
    search_url_template="https://www.overclockers.co.uk/search?sSearch={query}",
    card_selector="article, .product-card, .product-box, [data-testid*='product']",
    title_selector=".product-name, [data-testid*='product-name'], h2, h3",
    price_selector=".price, .product-price, [data-price-amount]",
    link_selector="a[href]",
    accept_language="en-GB,en;q=0.9",
    import_regime="uk_import",
)


class OverclockersScraper(IberianRetailerScraper):
    """Fetch Overclockers UK listings as UK-import observations."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)
