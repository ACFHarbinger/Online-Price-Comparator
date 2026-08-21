"""Callback registration and repository-backed view updates."""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta
from typing import Any

from dash import ALL, Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
from sqlalchemy import Engine

from config.settings import get_settings, override_settings
from dashboard.charts import build_bar_chart, build_forecast_chart, build_line_chart
from dashboard.stats import (
    DEFAULT_TREND_WINDOW_DAYS,
    DEFAULT_VOLATILITY_WINDOW_DAYS,
    PriceSeriesStats,
    compute_price_stats,
)
from fetch.circuit_breaker import CircuitBreaker
from forecasting.holt import ForecastResult, forecast_prices
from pipeline.custom_url import track_and_process_custom_url
from pipeline.discover import run_discovery
from pipeline.snapshot import persist_snapshot
from pipeline.source_discovery import discover_sources_for_product
from storage.candidates import CandidateListing, CandidateListingRepository
from storage.custom_urls import CustomListingUrl, CustomListingUrlRepository
from storage.repository import (
    ListingRepository,
    ListingSummary,
    PriceHistoryRepository,
    ProductPriceStats,
    ProductRepository,
)
from storage.watchlist import TrackedProductRepository

STALE_THRESHOLD_HOURS = 24


def _format_time_ago(observed_at: datetime | None, as_of: datetime) -> str:
    if observed_at is None:
        return "unknown"
    diff = as_of - observed_at
    total_seconds = max(0.0, diff.total_seconds())
    hours = int(total_seconds / 3600)
    if hours < 1:
        minutes = max(1, int(total_seconds / 60))
        return f"{minutes}m ago"
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


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
    settings = get_settings()
    existing = {
        site.strip()
        for site in settings.browser_fallback_sites.split(",")
        if site.strip()
    }
    existing.add("pccomponentes")
    return override_settings(
        browser_fallback_enabled=True,
        browser_fallback_headless=False,
        browser_fallback_sites=",".join(sorted(existing)),
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
    listings: list[ListingSummary],
    avg_30d: float | None,
    *,
    circuit_breaker: CircuitBreaker | None = None,
    as_of: datetime | None = None,
) -> html.Div | html.Table:
    if not listings:
        return html.Div(
            "No retailer listings have been recorded yet.", className="empty-message"
        )

    cb = circuit_breaker or CircuitBreaker()
    ref_time = as_of or datetime.now()
    open_breakers = cb.open_sites()

    banners: list[html.Div] = []
    affected_sites: dict[str, str] = {}
    for listing in listings:
        if listing.site_key in open_breakers:
            affected_sites[listing.site_key] = listing.site_display_name

    for site_key, site_display_name in affected_sites.items():
        banners.append(
            html.Div(
                [
                    html.Span("⚠", className="stale-banner-icon"),
                    html.Span("Scraper Paused:", className="stale-banner-title"),
                    (
                        f"Scraper for {site_display_name} ({site_key}) is "
                        "temporarily paused due to repeated failures. "
                        "Prices shown below may be outdated."
                    ),
                ],
                className="stale-banner",
            )
        )

    table_rows = []
    for listing in listings:
        is_blocked = listing.site_key in open_breakers
        is_out_of_stock = listing.price_amount is None
        is_stale = listing.observed_at is not None and (
            ref_time - listing.observed_at
        ) >= timedelta(hours=STALE_THRESHOLD_HOURS)

        row_classes: list[str] = []
        if is_blocked:
            row_classes.append("row-blocked")
        if is_out_of_stock:
            row_classes.append("row-out-of-stock")

        # Store cell
        store_children: list[Any] = [listing.site_display_name]
        if is_blocked:
            store_children.append(html.Span("PAUSED", className="badge-blocked"))
        elif is_stale and listing.observed_at is not None:
            time_ago = _format_time_ago(listing.observed_at, ref_time)
            store_children.append(
                html.Span(f"STALE ({time_ago})", className="badge-stale")
            )

        # Price cell
        if is_out_of_stock:
            price_elem: Any = html.Span(
                "Out of stock", className="price-value price-strikethrough"
            )
        else:
            price_elem = html.Span(
                _format_price(listing.price_amount, listing.currency),
                className="price-value",
            )

        # Stock cell
        if is_blocked:
            stock_elem = html.Span(
                [
                    html.Span(className="stock-dot stock-stale"),
                    "Scraper Paused",
                ]
            )
        elif is_out_of_stock:
            stock_elem = html.Span(
                [
                    html.Span(className="stock-dot stock-out"),
                    "Out of Stock",
                ]
            )
        elif is_stale:
            time_ago = _format_time_ago(listing.observed_at, ref_time)
            stock_elem = html.Span(
                [
                    html.Span(className="stock-dot stock-stale"),
                    f"Seen {time_ago}",
                ]
            )
        else:
            stock_elem = html.Span(
                [
                    html.Span(className="stock-dot stock-in"),
                    "In Stock",
                ]
            )

        table_rows.append(
            html.Tr(
                className=" ".join(row_classes) if row_classes else None,
                children=[
                    html.Td(html.Span(store_children)),
                    html.Td(price_elem),
                    html.Td(stock_elem),
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
                ],
            )
        )

    table = html.Table(
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
            html.Tbody(table_rows),
        ],
    )

    if banners:
        return html.Div([*banners, table])
    return table


def _candidate_sources_panel(
    candidates: list[CandidateListing],
    *,
    as_of: datetime | None = None,
) -> html.Div | html.Table:
    """Render the pending candidate sources list with approve/reject actions."""
    if not candidates:
        return html.Div(
            "No pending candidate sources for this product. "
            "Click 'Discover More Sources' to search.",
            className="empty-message",
        )

    ref_time = as_of or datetime.now()
    rows = []
    for cand in candidates:
        time_left = cand.expires_at - ref_time
        days_left = max(0, int(time_left.total_seconds() / 86400))
        expiry_str = f"{days_left}d left" if days_left > 0 else "Expiring today"

        score_badge = (
            html.Span(
                f"{int(cand.match_score * 100)}%",
                className="badge-score",
            )
            if cand.match_score is not None
            else html.Span("—", className="price-value")
        )

        rows.append(
            html.Tr(
                [
                    html.Td(cand.site_display_name),
                    html.Td(cand.title),
                    html.Td(
                        _format_price(cand.price_amount, cand.currency),
                        className="price-value",
                    ),
                    html.Td(score_badge),
                    html.Td(expiry_str, className="price-value"),
                    html.Td(
                        html.A(
                            "View listing ↗",
                            href=cand.url,
                            target="_blank",
                            rel="noreferrer",
                        )
                    ),
                    html.Td(
                        [
                            html.Button(
                                "Approve",
                                id={"type": "candidate-approve-btn", "index": cand.id},
                                className="btn-approve",
                            ),
                            html.Button(
                                "Reject",
                                id={"type": "candidate-reject-btn", "index": cand.id},
                                className="btn-reject",
                            ),
                        ]
                    ),
                ]
            )
        )

    return html.Table(
        className="candidate-table",
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th("Store"),
                        html.Th("Discovered Product Title"),
                        html.Th("Price"),
                        html.Th("Match Score"),
                        html.Th("Time Limit"),
                        html.Th("Link"),
                        html.Th("Actions"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
    )


def _custom_urls_panel(
    custom_urls: list[CustomListingUrl],
    *,
    as_of: datetime | None = None,
) -> html.Div | html.Table:
    """Build the custom listing URLs review table."""
    if not custom_urls:
        return html.Div(
            "No custom listing URLs tracked yet for this product. "
            "Paste an exact product page URL above to track it.",
            className="empty-message",
        )

    ref_time = as_of or datetime.now()
    rows = []
    for item in custom_urls:
        confidence_str = (
            f"{int(item.parser_confidence * 100)}%"
            if item.parser_confidence is not None
            else "—"
        )
        checked_str = (
            _format_time_ago(item.last_checked_at, ref_time)
            if item.last_checked_at
            else "Pending"
        )
        status_color = (
            "#3FB950"
            if item.status == "active"
            else "#F85149"
            if item.status in ("failed", "unmatched")
            else "#8B949E"
        )
        status_badge = html.Span(
            item.status.capitalize(),
            style={"color": status_color, "fontWeight": "600"},
        )

        rows.append(
            html.Tr(
                [
                    html.Td(item.site_display_name),
                    html.Td(
                        html.A(
                            item.url,
                            href=item.url,
                            target="_blank",
                            rel="noreferrer",
                            style={
                                "maxWidth": "300px",
                                "overflow": "hidden",
                                "textOverflow": "ellipsis",
                                "display": "inline-block",
                                "whiteSpace": "nowrap",
                            },
                        )
                    ),
                    html.Td(confidence_str, className="price-value"),
                    html.Td(status_badge),
                    html.Td(checked_str, className="price-value"),
                    html.Td(
                        html.Button(
                            "Remove",
                            id={"type": "custom-url-remove-btn", "index": item.id},
                            className="btn-remove-url",
                        )
                    ),
                ]
            )
        )

    return html.Table(
        className="custom-url-table",
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th("Store"),
                        html.Th("Product Page URL"),
                        html.Th("Confidence"),
                        html.Th("Status"),
                        html.Th("Last Checked"),
                        html.Th("Actions"),
                    ]
                )
            ),
            html.Tbody(rows),
        ],
    )


def _build_trend_indicator(price_stats: PriceSeriesStats) -> html.Span:
    """Build the trend/gradient arrow + rate badge for the hero.

    Descriptive of observed history only - it never claims to predict a
    future price (that is v2.18, which ships on a separate surface).
    """
    if price_stats.trend_per_week is None or price_stats.trend_pct_per_week is None:
        return html.Span(
            "not enough history yet",
            className="hero-badge badge-trend-neutral",
        )
    currency = price_stats.currency or "EUR"
    slope_week = price_stats.trend_per_week
    pct_week = price_stats.trend_pct_per_week * 100
    if slope_week < -0.01:
        arrow, badge_class = "▼", "badge-trend-pos"  # falling = cheaper = good
    elif slope_week > 0.01:
        arrow, badge_class = "▲", "badge-trend-neg"  # rising = more expensive = bad
    else:
        arrow, badge_class = "→", "badge-trend-neutral"
    sign = "-" if slope_week < 0 else "+"
    text = (
        f"{arrow} {sign}{currency} {abs(slope_week):,.2f}/wk "
        f"({sign}{abs(pct_week):.1f}%/wk)"
    )
    return html.Span(text, className=f"hero-badge {badge_class}")


def _build_volatility_badge(price_stats: PriceSeriesStats) -> html.Span:
    """Build the volatility stat tile: coefficient of variation for the window."""
    if price_stats.coefficient_of_variation is None:
        return html.Span(
            "volatility: not enough history yet",
            className="hero-badge badge-volatility",
        )
    cv_pct = price_stats.coefficient_of_variation * 100
    return html.Span(
        f"±{cv_pct:.1f}% over last {price_stats.window_days}d",
        className="hero-badge badge-volatility",
    )


def _forecast_metadata(forecast: ForecastResult) -> str:
    """State forecast honesty metadata without presenting a point estimate."""
    if not forecast.is_available:
        return f"Forecast unavailable: {forecast.unavailable_reason}"
    assert forecast.trained_at is not None
    return (
        f"80% confidence band · Holt linear trend · {forecast.observation_count} "
        "compatible observations · last retrained from data through "
        f"{forecast.trained_at:%Y-%m-%d}"
    )


def _build_hero_metrics(
    stats: ProductPriceStats,
    current_lowest: float | None,
    volatility: PriceSeriesStats | None = None,
    trend: PriceSeriesStats | None = None,
) -> list[html.Span]:
    badges: list[html.Span] = []
    if volatility is not None:
        badges.append(_build_volatility_badge(volatility))
    if trend is not None:
        badges.append(_build_trend_indicator(trend))
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
    Any,
    str,
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
            build_forecast_chart(forecast_prices([])),
            "Forecast unavailable: choose a product first",
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
    volatility = compute_price_stats(
        history, window_days=DEFAULT_VOLATILITY_WINDOW_DAYS
    )
    trend = compute_price_stats(history, window_days=DEFAULT_TREND_WINDOW_DAYS)
    forecast = forecast_prices(history)

    image_url = next(
        (listing.image_url for listing in listings if listing.image_url), None
    )
    lowest = min(latest_prices, key=lambda point: point.price_amount, default=None)
    lowest_text = "—"
    lowest_amount = lowest.price_amount if lowest is not None else None
    if lowest is not None:
        formatted_price = _format_price(lowest.price_amount, lowest.currency)
        lowest_text = f"{formatted_price} ({lowest.site_display_name})"

    hero_metrics = _build_hero_metrics(stats, lowest_amount, volatility, trend)

    return (
        product.canonical_name or product.query_text,
        image_url,
        lowest_text,
        hero_metrics,
        build_bar_chart(latest_prices),
        build_line_chart(history, all_time_low=stats.all_time_low),
        _retailer_table(listings, stats.avg_30d),
        build_forecast_chart(forecast),
        _forecast_metadata(forecast),
    )


def register_callbacks(app: Dash, engine: Engine) -> None:
    """Attach search, selection, and product-detail callbacks to ``app``."""
    product_repository = ProductRepository(engine)
    listing_repository = ListingRepository(engine)
    price_repository = PriceHistoryRepository(engine)
    tracked_repository = TrackedProductRepository(engine)

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

        cleaned_query = query.strip()
        tracked = tracked_repository.get_by_query(cleaned_query)
        with _visible_browser_override(show_browser):
            product_id = persist_snapshot(
                cleaned_query,
                run_discovery(
                    cleaned_query,
                    get_settings(),
                    engine=engine,
                    tracked_product_id=tracked.id if tracked is not None else None,
                ),
                engine,
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
        Output("price-forecast-chart", "figure"),
        Output("forecast-metadata", "children"),
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
        Any,
        str,
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
            forecast_chart,
            forecast_metadata,
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
            forecast_chart,
            forecast_metadata,
        )

    candidates_repository = CandidateListingRepository(engine)

    @app.callback(
        Output("candidate-sources-container", "children"),
        Input("selected-product-id", "data"),
        Input("discover-sources-button", "n_clicks"),
        Input({"type": "candidate-approve-btn", "index": ALL}, "n_clicks"),
        Input({"type": "candidate-reject-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=False,
    )
    def manage_candidates(
        product_id: int | None,
        _discover_clicks: int | None,
        _approve_clicks: list[int | None] | None,
        _reject_clicks: list[int | None] | None,
    ) -> html.Div | html.Table:
        """Handle candidate source discovery, approval, rejection, and listing."""
        if product_id is None:
            return html.Div(
                "Choose a tracked product to discover and review candidate sources.",
                className="empty-message",
            )

        # Lookup tracked product associated with this product_id
        tracked = None
        for tp in tracked_repository.list_all():
            if tp.product_id == product_id:
                tracked = tp
                break

        if tracked is None:
            return html.Div(
                "This product is not in your tracked watchlist. "
                "Track it first to discover sources.",
                className="empty-message",
            )

        triggered = ctx.triggered_id
        if isinstance(triggered, dict):
            btn_type = triggered.get("type")
            cand_id = triggered.get("index")
            if btn_type == "candidate-approve-btn" and isinstance(cand_id, int):
                candidates_repository.approve(cand_id)
            elif btn_type == "candidate-reject-btn" and isinstance(cand_id, int):
                candidates_repository.reject(cand_id)
        elif triggered == "discover-sources-button":
            discover_sources_for_product(tracked.id, engine, get_settings())

        pending = candidates_repository.list_pending(tracked.id)
        return _candidate_sources_panel(pending)

    custom_urls_repository = CustomListingUrlRepository(engine)

    @app.callback(
        Output("custom-urls-container", "children"),
        Output("custom-url-status-message", "children"),
        Output("custom-url-status-message", "style"),
        Output("custom-url-input", "value"),
        Input("selected-product-id", "data"),
        Input("custom-url-submit-button", "n_clicks"),
        Input({"type": "custom-url-remove-btn", "index": ALL}, "n_clicks"),
        State("custom-url-input", "value"),
        prevent_initial_call=False,
    )
    def manage_custom_urls(
        product_id: int | None,
        _submit_clicks: int | None,
        _remove_clicks: list[int | None] | None,
        url_value: str | None,
    ) -> tuple[html.Div | html.Table, str, dict[str, str], str]:
        """Handle custom listing URL addition, removal, and listing."""
        empty_style = {"display": "none"}
        if product_id is None:
            return (
                html.Div(
                    "Choose a tracked product to view and add custom listing URLs.",
                    className="empty-message",
                ),
                "",
                empty_style,
                "",
            )

        tracked = None
        for tp in tracked_repository.list_all():
            if tp.product_id == product_id:
                tracked = tp
                break

        if tracked is None:
            return (
                html.Div(
                    "This product is not in your tracked watchlist. "
                    "Track it first to add custom URLs.",
                    className="empty-message",
                ),
                "",
                empty_style,
                "",
            )

        status_msg = ""
        status_style = empty_style
        input_clear = ""

        triggered = ctx.triggered_id
        if isinstance(triggered, dict):
            btn_type = triggered.get("type")
            custom_id = triggered.get("index")
            if btn_type == "custom-url-remove-btn" and isinstance(custom_id, int):
                custom_urls_repository.remove(custom_id)
                status_msg = "Removed custom listing URL."
                status_style = {"color": "#8B949E"}
        elif (
            triggered == "custom-url-submit-button" and url_value and url_value.strip()
        ):
            success, msg = track_and_process_custom_url(
                tracked.id,
                url_value.strip(),
                engine,
                get_settings(),
            )
            status_msg = msg
            status_style = {"color": "#3FB950" if success else "#F85149"}
            input_clear = "" if success else url_value

        custom_list = custom_urls_repository.list_for_product(tracked.id)
        return (
            _custom_urls_panel(custom_list),
            status_msg,
            status_style,
            input_clear,
        )
