"""Callback registration and repository-backed view updates."""

from __future__ import annotations

import contextlib
from typing import Any

from dash import Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
from sqlalchemy import Engine

from config.settings import get_settings, override_settings
from dashboard.charts import build_bar_chart, build_line_chart
from pipeline.discover import run_discovery
from pipeline.snapshot import persist_snapshot
from storage.repository import (
    ListingRepository,
    ListingSummary,
    PriceHistoryRepository,
    PriceSeriesStatistics,
    ProductPriceStats,
    ProductRepository,
)


def _visible_browser_override(
    show_browser: list[str] | None,
) -> contextlib.AbstractContextManager[None]:
    """Build the settings-override context for the "show browser" checkbox.

    Checked: force-enables the browser fallback (regardless of .env) with a
    real, visible window - the union of whatever sites were already
    allowlisted plus every site that actually implements the fallback
    (currently just PcComponentes) - for this one search only. Unchecked:
    a no-op context, .env's settings apply unchanged.
    """
    if not show_browser or "visible" not in show_browser:
        return contextlib.nullcontext()
    base = get_settings()
    sites = base.browser_fallback_site_keys() | {"pccomponentes"}
    return override_settings(
        browser_fallback_enabled=True,
        browser_fallback_headless=False,
        browser_fallback_sites=",".join(sorted(sites)),
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


def _format_delta_vs_avg(
    price: float | None, avg: float | None, currency: str | None
) -> html.Span:
    if price is None or avg is None or avg <= 0:
        return html.Span("—", className="price-value")
    diff = price - avg
    pct = (diff / avg) * 100
    sign = "+" if diff > 0 else "-"
    abs_diff = abs(diff)
    curr_str = currency or "EUR"
    text = f"{sign}{curr_str} {abs_diff:,.2f} ({sign}{abs(pct):.1f}%)"
    if diff < -0.01:
        color_class = "pill-delta-pos"  # cheaper than avg = good
    elif diff > 0.01:
        color_class = "pill-delta-neg"  # more expensive than avg = bad
    else:
        color_class = "pill-delta-neutral"
    return html.Span(
        text, className=f"hero-badge {color_class}", style={"fontSize": "0.75rem"}
    )


def _retailer_table(
    listings: list[ListingSummary], avg_30d: float | None
) -> html.Div | html.Table:
    if not listings:
        return html.Div(
            "No retailer listings have been recorded yet.", className="empty-message"
        )
    return html.Table(
        className="retailer-table",
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th("Store"),
                        html.Th("Price"),
                        html.Th("Stock"),
                        html.Th("Shipping"),
                        html.Th("Price vs Avg"),
                        html.Th("Link"),
                    ]
                )
            ),
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
                                html.Span(
                                    [
                                        html.Span(
                                            className=(
                                                "stock-dot stock-in"
                                                if listing.price_amount is not None
                                                else "stock-dot stock-unknown"
                                            )
                                        ),
                                        (
                                            "In Stock"
                                            if listing.price_amount is not None
                                            else "Unknown"
                                        ),
                                    ]
                                )
                            ),
                            html.Td("—", className="price-value"),
                            html.Td(
                                _format_delta_vs_avg(
                                    listing.price_amount, avg_30d, listing.currency
                                )
                            ),
                            html.Td(
                                html.A(
                                    "Visit retailer ↗",
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


def _build_hero_metrics(
    stats: ProductPriceStats,
    arg2: PriceSeriesStatistics | float | None = None,
    arg3: float | None = None,
) -> list[html.Span]:
    if isinstance(arg2, PriceSeriesStatistics):
        series_stats: PriceSeriesStatistics | None = arg2
        current_lowest: float | None = arg3
    else:
        series_stats = None
        current_lowest = arg2

    badges: list[html.Span] = []
    if stats.all_time_low is not None:
        curr = stats.all_time_low_currency or "EUR"
        badges.append(
            html.Span(
                f"ATL: {curr} {stats.all_time_low:,.2f}",
                className="hero-badge badge-atl",
            )
        )
    if stats.avg_30d is not None and current_lowest is not None and stats.avg_30d > 0:
        diff = current_lowest - stats.avg_30d
        pct = (diff / stats.avg_30d) * 100
        sign = "+" if diff > 0 else "-"
        abs_diff = abs(diff)
        curr = stats.avg_30d_currency or "EUR"
        pill_class = (
            "pill-delta-pos"
            if diff < -0.01
            else ("pill-delta-neg" if diff > 0.01 else "pill-delta-neutral")
        )
        badges.append(
            html.Span(
                f"{sign}{curr} {abs_diff:,.2f} / {sign}{abs(pct):.1f}% vs 30-day avg",
                className=f"hero-badge {pill_class}",
            )
        )

    # If series_stats is explicitly provided
    if series_stats is not None:
        if series_stats.volatility_pct is None or series_stats.trend_per_week is None:
            badges.append(
                html.Span(
                    "Price statistics: not enough history yet "
                    f"({series_stats.observation_count}/4 points in "
                    f"{series_stats.window_days}d)",
                    className="hero-badge pill-delta-neutral",
                )
            )
            return badges

        badges.append(
            html.Span(
                "Price moved "
                f"±{series_stats.volatility_pct:.1f}% over the last "
                f"{series_stats.window_days} days",
                className="hero-badge stat-volatility",
            )
        )
        trend = series_stats.trend_per_week
        direction = "↓" if trend < -0.01 else ("↑" if trend > 0.01 else "→")
        trend_class = (
            "stat-trend-down"
            if trend < -0.01
            else ("stat-trend-up" if trend > 0.01 else "pill-delta-neutral")
        )
        badges.append(
            html.Span(
                "Observed trend: "
                f"{direction} {series_stats.currency or 'EUR'} {abs(trend):,.2f}/week "
                f"({series_stats.window_days}d)",
                className=f"hero-badge {trend_class}",
            )
        )
    elif stats.volatility_90d is not None or stats.trend_30d is not None:
        # If stats has volatility_90d and trend_30d populated
        if (
            stats.volatility_90d is not None
            and stats.volatility_90d.is_sparse
            and stats.trend_30d is not None
            and stats.trend_30d.is_sparse
        ):
            badges.append(
                html.Span(
                    "Price statistics: not enough history yet "
                    f"({stats.trend_30d.sample_size}/4 points in "
                    f"{stats.trend_30d.window_days}d)",
                    className="hero-badge pill-delta-neutral",
                )
            )
            return badges

        if stats.volatility_90d is not None and not stats.volatility_90d.is_sparse:
            vol = stats.volatility_90d
            pct_str = f"{vol.cv_percent:.1f}" if vol.cv_percent is not None else "0.0"
            badges.append(
                html.Span(
                    f"Price moved ±{pct_str}% over the last {vol.window_days} days",
                    className="hero-badge stat-volatility",
                )
            )
        if stats.trend_30d is not None and not stats.trend_30d.is_sparse:
            trend_obj = stats.trend_30d
            t_class = (
                "stat-trend-down"
                if trend_obj.direction == "down"
                else (
                    "stat-trend-up"
                    if trend_obj.direction == "up"
                    else "pill-delta-neutral"
                )
            )
            badges.append(
                html.Span(
                    f"Observed trend: {trend_obj.description}",
                    className=f"hero-badge {t_class}",
                )
            )

    return badges


def _product_view(
    product_id: int | None,
    include_anomalous: bool,
    product_repository: ProductRepository,
    listing_repository: ListingRepository,
    price_repository: PriceHistoryRepository,
) -> tuple[
    str,
    str | None,
    str,
    list[html.Span],
    Any,
    Any,
    html.Div | html.Table,
]:
    if product_id is None:
        return (
            "Select or search for a product",
            None,
            "—",
            [],
            build_bar_chart([]),
            build_line_chart([]),
            html.Div(
                "Choose a product to see retailer listings.", className="empty-message"
            ),
        )

    product = product_repository.get(product_id)
    if product is None:
        return _product_view(
            None,
            include_anomalous,
            product_repository,
            listing_repository,
            price_repository,
        )

    listings = listing_repository.list_with_latest_price(
        product_id, include_anomalous=include_anomalous
    )
    latest_prices = price_repository.latest_prices_by_site(
        product_id, include_anomalous=include_anomalous
    )
    history = price_repository.price_history_by_site(
        product_id, include_anomalous=include_anomalous
    )
    stats = price_repository.product_price_stats(
        product_id, include_anomalous=include_anomalous
    )
    series_stats = price_repository.product_price_series_statistics(
        product_id, include_anomalous=include_anomalous
    )

    image_url = next(
        (listing.image_url for listing in listings if listing.image_url), None
    )
    lowest = min(latest_prices, key=lambda point: point.price_amount, default=None)
    lowest_text = "—"
    lowest_amount = lowest.price_amount if lowest is not None else None
    if lowest is not None:
        formatted_price = _format_price(lowest.price_amount, lowest.currency)
        lowest_text = f"{formatted_price} ({lowest.site_display_name})"

    hero_metrics = _build_hero_metrics(stats, series_stats, lowest_amount)

    return (
        product.canonical_name or product.query_text,
        image_url,
        lowest_text,
        hero_metrics,
        build_bar_chart(latest_prices),
        build_line_chart(history, all_time_low=stats.all_time_low),
        _retailer_table(listings, stats.avg_30d),
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
        State("show-browser-checkbox", "value"),
        prevent_initial_call=True,
    )
    def select_product(
        _clicks: int | None,
        _submits: int | None,
        dropdown_product_id: int | None,
        _load_interval: int | None,
        query: str | None,
        show_browser: list[str] | None,
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

        with _visible_browser_override(show_browser):
            product_id = persist_snapshot(
                query.strip(), run_discovery(query.strip(), get_settings()), engine
            )
        return product_id, _product_options(product_repository), product_id

    @app.callback(
        Output("product-title", "children"),
        Output("product-image", "src"),
        Output("product-image", "className"),
        Output("current-lowest-price", "children"),
        Output("hero-metrics-container", "children"),
        Output("current-prices-chart", "figure"),
        Output("price-history-chart", "figure"),
        Output("retailer-table", "children"),
        Input("selected-product-id", "data"),
        Input("reveal-anomalies-checkbox", "value"),
    )
    def refresh_product(
        product_id: int | None,
        reveal_anomalies: list[str] | None,
    ) -> tuple[
        str,
        str | None,
        str,
        str,
        list[html.Span],
        Any,
        Any,
        html.Div | html.Table,
    ]:
        """Load every dashboard panel for the selected tracked product."""
        include_anomalous = bool(reveal_anomalies and "reveal" in reveal_anomalies)
        (
            title,
            image_url,
            lowest,
            hero_metrics,
            bar_chart,
            line_chart,
            table,
        ) = _product_view(
            product_id,
            include_anomalous,
            product_repository,
            listing_repository,
            price_repository,
        )
        image_class = (
            "product-image" if image_url else "product-image product-image--empty"
        )
        return (
            title,
            image_url,
            image_class,
            lowest,
            hero_metrics,
            bar_chart,
            line_chart,
            table,
        )
