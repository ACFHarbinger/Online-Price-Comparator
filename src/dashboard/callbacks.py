"""Callback registration and repository-backed view updates."""

from __future__ import annotations

from typing import Any

from dash import Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
from sqlalchemy import Engine

from config.settings import get_settings
from dashboard.charts import build_bar_chart, build_line_chart
from pipeline.discover import run_discovery
from pipeline.snapshot import persist_snapshot
from storage.repository import (
    ListingRepository,
    ListingSummary,
    PriceHistoryRepository,
    ProductRepository,
)


def _product_options(product_repository: ProductRepository) -> list[dict[str, Any]]:
    return [
        {
            "label": product.canonical_name or product.query_text,
            "value": product.id,
        }
        for product in product_repository.list_products()
    ]


def _format_price(amount: float | None, currency: str | None) -> str:
    if amount is None or currency is None:
        return "—"
    return f"{currency} {amount:,.2f}"


def _retailer_table(listings: list[ListingSummary]) -> html.Div | html.Table:
    if not listings:
        return html.Div(
            "No retailer listings have been recorded yet.", className="empty-message"
        )
    return html.Table(
        className="retailer-table",
        children=[
            html.Thead(html.Tr([html.Th("Store"), html.Th("Price"), html.Th("Link")])),
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Td(listing.site_display_name),
                            html.Td(
                                _format_price(listing.price_amount, listing.currency),
                                className="price-value",
                            ),
                            html.Td(
                                html.A(
                                    "Visit retailer",
                                    href=listing.url,
                                    target="_blank",
                                    rel="noreferrer",
                                )
                            ),
                        ]
                    )
                    for listing in listings
                ]
            ),
        ],
    )


def _product_view(
    product_id: int | None,
    product_repository: ProductRepository,
    listing_repository: ListingRepository,
    price_repository: PriceHistoryRepository,
) -> tuple[str, str | None, str, Any, Any, html.Div | html.Table]:
    if product_id is None:
        return (
            "Select or search for a product",
            None,
            "—",
            build_bar_chart([]),
            build_line_chart([]),
            html.Div(
                "Choose a product to see retailer listings.", className="empty-message"
            ),
        )

    product = product_repository.get(product_id)
    if product is None:
        return _product_view(
            None, product_repository, listing_repository, price_repository
        )

    listings = listing_repository.list_with_latest_price(product_id)
    latest_prices = price_repository.latest_prices_by_site(product_id)
    history = price_repository.price_history_by_site(product_id)
    image_url = next(
        (listing.image_url for listing in listings if listing.image_url), None
    )
    lowest = min(latest_prices, key=lambda point: point.price_amount, default=None)
    lowest_text = "—"
    if lowest is not None:
        formatted_price = _format_price(lowest.price_amount, lowest.currency)
        lowest_text = f"{formatted_price} ({lowest.site_display_name})"
    return (
        product.canonical_name or product.query_text,
        image_url,
        lowest_text,
        build_bar_chart(latest_prices),
        build_line_chart(history),
        _retailer_table(listings),
    )


def register_callbacks(app: Dash, engine: Engine) -> None:
    """Attach search, selection, and product-detail callbacks to ``app``."""
    product_repository = ProductRepository(engine)
    listing_repository = ListingRepository(engine)
    price_repository = PriceHistoryRepository(engine)

    @app.callback(
        Output("selected-product-id", "data"),
        Output("tracked-product-dropdown", "options"),
        Output("tracked-product-dropdown", "value"),
        Input("product-search-button", "n_clicks"),
        Input("product-search-input", "n_submit"),
        Input("tracked-product-dropdown", "value"),
        Input("tracked-products-loader", "n_intervals"),
        State("product-search-input", "value"),
        prevent_initial_call=True,
    )
    def select_product(
        _clicks: int | None,
        _submits: int | None,
        dropdown_product_id: int | None,
        _load_interval: int | None,
        query: str | None,
    ) -> tuple[Any, list[dict[str, Any]], Any]:
        """Persist a requested search or select an existing product."""
        if ctx.triggered_id == "tracked-products-loader":
            return no_update, _product_options(product_repository), no_update
        if ctx.triggered_id == "tracked-product-dropdown":
            if dropdown_product_id is None:
                raise PreventUpdate
            return (
                dropdown_product_id,
                _product_options(product_repository),
                dropdown_product_id,
            )
        if not query or not query.strip():
            raise PreventUpdate
        product_id = persist_snapshot(
            query.strip(), run_discovery(query.strip(), get_settings()), engine
        )
        return product_id, _product_options(product_repository), product_id

    @app.callback(
        Output("product-title", "children"),
        Output("product-image", "src"),
        Output("product-image", "className"),
        Output("current-lowest-price", "children"),
        Output("current-prices-chart", "figure"),
        Output("price-history-chart", "figure"),
        Output("retailer-table", "children"),
        Input("selected-product-id", "data"),
    )
    def refresh_product(
        product_id: int | None,
    ) -> tuple[str, str | None, str, str, Any, Any, html.Div | html.Table]:
        """Load every dashboard panel for the selected tracked product."""
        title, image_url, lowest, bar_chart, line_chart, table = _product_view(
            product_id, product_repository, listing_repository, price_repository
        )
        image_class = (
            "product-image" if image_url else "product-image product-image--empty"
        )
        return title, image_url, image_class, lowest, bar_chart, line_chart, table
