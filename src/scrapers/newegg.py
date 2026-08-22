"""Scraper adapter for Newegg US global-tier RAM search results."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from bs4.element import Tag

from models.listing import RawListing
from normalize.price import parse_price
from scrapers.landed_cost import estimate_newegg_portugal_landed_cost
from scrapers.retailer_base import IberianRetailerScraper, RetailerParserConfig
from scrapers.structured_data import StructuredProduct

_CONFIG = RetailerParserConfig(
    site_key="newegg",
    display_name="Newegg US",
    base_url="https://www.newegg.com",
    search_url_template="https://www.newegg.com/p/pl?d={query}",
    card_selector=".item-cell, .item-container, article[data-testid*='product']",
    title_selector=".item-title, .product-name, h2, h3",
    price_selector=".price-current, .price, .product-price, [data-price-amount]",
    link_selector="a.item-title[href], a[href]",
    accept_language="en-US,en;q=0.9",
    import_regime="row",
)


class NeweggScraper(IberianRetailerScraper):
    """Fetch Newegg US listings with an explicit Portugal cost estimate."""

    def __init__(self) -> None:
        super().__init__(_CONFIG)

    def _listing_from_structured(
        self, product: StructuredProduct, fetched_at: datetime
    ) -> RawListing:
        return self._with_landed_cost(
            super()._listing_from_structured(product, fetched_at)
        )

    def _parse_card(self, card: Tag, fetched_at: datetime) -> RawListing | None:
        listing = super()._parse_card(card, fetched_at)
        return self._with_landed_cost(listing) if listing is not None else None

    @staticmethod
    def _with_landed_cost(listing: RawListing) -> RawListing:
        try:
            amount, currency = parse_price(listing.price_text, listing.currency_hint)
        except ValueError:
            return listing
        estimate = estimate_newegg_portugal_landed_cost(amount, currency)
        if estimate is None:
            return listing
        return replace(listing, extra={**listing.extra, **estimate.as_extra()})
