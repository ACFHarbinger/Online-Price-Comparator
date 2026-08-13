"""Dash component tree for the single-product comparator screen."""

from __future__ import annotations

from dash import dcc, html

from dashboard.charts import build_bar_chart, build_line_chart


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
                                "—", id="current-lowest-price", className="lowest-price"
                            ),
                        ],
                    ),
                ],
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
                            className="panel",
                            children=[
                                html.H3("Retailer Links", className="panel-heading"),
                                html.Div(
                                    "Choose a product to see retailer listings.",
                                    id="retailer-table",
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        ],
    )
