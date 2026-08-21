"""Dash component tree for the single-product comparator screen."""

from __future__ import annotations

from dash import dcc, html

from dashboard.charts import build_bar_chart, build_forecast_chart, build_line_chart
from forecasting.holt import forecast_prices


def build_layout() -> html.Div:
    """Return the dashboard's initial, unselected-product layout."""
    return html.Div(
        className="dashboard-shell",
        children=[
            dcc.Store(id="selected-product-id"),
            dcc.Interval(
                id="tracked-products-loader",
                interval=1,
                max_intervals=1,
            ),
            html.H1("ONLINE PRICE COMPARATOR", className="dashboard-title"),
            html.Div(
                className="search-row",
                children=[
                    dcc.Input(
                        id="product-search-input",
                        className="search-input",
                        type="search",
                        placeholder="Search for a product to track",
                        debounce=False,
                    ),
                    html.Button(
                        "Search", id="product-search-button", className="search-button"
                    ),
                ],
            ),
            dcc.Checklist(
                id="show-browser-checkbox",
                className="show-browser-checkbox",
                options=[
                    {
                        "label": (
                            " Show browser window for this search (helps with "
                            "sites like PcComponentes that need a human to "
                            "click through a challenge)"
                        ),
                        "value": "visible",
                    }
                ],
                value=[],
            ),
            dcc.Dropdown(
                id="tracked-product-dropdown",
                className="dash-dropdown product-select",
                options=[],
                placeholder="Open a tracked product",
                clearable=True,
            ),
            html.Section(
                className="hero",
                children=[
                    html.Img(
                        id="product-image",
                        className="product-image product-image--empty",
                    ),
                    html.Div(
                        className="hero-copy",
                        children=[
                            html.H2(
                                "Select or search for a product",
                                id="product-title",
                                className="product-name",
                            ),
                            html.Div("CURRENT LOWEST", className="lowest-label"),
                            html.Div(
                                [
                                    html.Span(
                                        "—",
                                        id="current-lowest-price",
                                        className="lowest-price",
                                    ),
                                    html.Div(
                                        id="hero-metrics-container",
                                        className="hero-metrics",
                                    ),
                                ]
                            ),
                        ],
                    ),
                ],
            ),
            dcc.Checklist(
                id="reveal-anomalies-checkbox",
                className="reveal-anomalies-checkbox",
                options=[
                    {
                        "label": " Show anomalous listings (flagged price outliers)",
                        "value": "reveal",
                    }
                ],
                value=[],
            ),
            dcc.Loading(
                type="default",
                children=html.Div(
                    id="product-data-area",
                    children=[
                        html.Div(
                            className="chart-grid",
                            children=[
                                html.Section(
                                    className="panel",
                                    children=[
                                        html.H3(
                                            "Historical Price Trend",
                                            className="panel-heading",
                                        ),
                                        dcc.Graph(
                                            id="price-history-chart",
                                            figure=build_line_chart([]),
                                            config={"displayModeBar": False},
                                        ),
                                    ],
                                ),
                                html.Section(
                                    className="panel",
                                    children=[
                                        html.H3(
                                            "Current Prices", className="panel-heading"
                                        ),
                                        dcc.Graph(
                                            id="current-prices-chart",
                                            figure=build_bar_chart([]),
                                            config={"displayModeBar": False},
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        html.Section(
                            className="panel forecast-panel",
                            children=[
                                html.H3(
                                    "Projected Price Range — Not a Guarantee",
                                    className="panel-heading",
                                ),
                                html.Div(
                                    "Uses an 80% confidence band from a Holt "
                                    "linear-trend model. This is separate from "
                                    "observed price history.",
                                    id="forecast-metadata",
                                    className="forecast-metadata",
                                ),
                                dcc.Graph(
                                    id="price-forecast-chart",
                                    figure=build_forecast_chart(forecast_prices([])),
                                    config={"displayModeBar": False},
                                ),
                            ],
                        ),
                        html.Section(
                            className="panel",
                            children=[
                                html.H3("Retailer Links", className="panel-heading"),
                                html.Div(
                                    "Choose a product to see retailer listings.",
                                    id="retailer-table",
                                ),
                            ],
                        ),
                        html.Section(
                            className="panel candidate-panel",
                            children=[
                                html.Div(
                                    className="panel-header-row",
                                    children=[
                                        html.H3(
                                            "Discovered Source Candidates",
                                            className="panel-heading",
                                            style={"margin": "0"},
                                        ),
                                        html.Button(
                                            "Discover More Sources",
                                            id="discover-sources-button",
                                            className="discover-button",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    "Choose a tracked product to discover "
                                    "and review candidate sources.",
                                    id="candidate-sources-container",
                                ),
                            ],
                        ),
                        html.Section(
                            className="panel custom-url-panel",
                            children=[
                                html.Div(
                                    className="panel-header-row",
                                    children=[
                                        html.H3(
                                            "Custom Listing URLs (Tier A)",
                                            className="panel-heading",
                                            style={"margin": "0"},
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="custom-url-input-row",
                                    children=[
                                        dcc.Input(
                                            id="custom-url-input",
                                            type="text",
                                            placeholder=(
                                                "Paste exact product page URL "
                                                "(e.g. https://shop.com/product)..."
                                            ),
                                            className="custom-url-input",
                                        ),
                                        html.Button(
                                            "Track URL",
                                            id="custom-url-submit-button",
                                            className="custom-url-button",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    id="custom-url-status-message",
                                    className="custom-url-status",
                                ),
                                html.Div(
                                    "Choose a tracked product to view and "
                                    "add custom listing URLs.",
                                    id="custom-urls-container",
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )
