"""Tests for dashboard charts and view functions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from dashboard.callbacks import (
    _build_hero_metrics,
    _build_trend_indicator,
    _build_volatility_badge,
    _forecast_metadata,
    _format_delta_vs_avg,
    _retailer_table,
)
from dashboard.charts import build_bar_chart, build_forecast_chart, build_line_chart
from dashboard.stats import PriceSeriesStats
from forecasting.holt import forecast_prices
from storage.repository import ListingSummary, ProductPriceStats, SitePricePoint


def test_build_line_chart_with_atl_and_range_selectors() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)
    points = [
        SitePricePoint(
            site_key="amazon.es",
            site_display_name="Amazon.es",
            price_amount=450.0,
            currency="EUR",
            observed_at=now,
        ),
        SitePricePoint(
            site_key="pccomponentes",
            site_display_name="PcComponentes",
            price_amount=429.0,
            currency="EUR",
            observed_at=now,
        ),
    ]

    fig = build_line_chart(points, all_time_low=429.0)
    assert fig is not None

    # Check rangeselector buttons
    xaxis = fig.layout.xaxis
    assert xaxis.rangeselector is not None
    button_labels = [b.label for b in xaxis.rangeselector.buttons]
    assert button_labels == ["1W", "1M", "3M", "1Y", "ALL"]

    # Check dashed ATL reference line
    shapes = fig.layout.shapes
    assert len(shapes) == 1
    assert shapes[0].type == "line"
    assert shapes[0].y0 == 429.0
    assert shapes[0].y1 == 429.0
    assert shapes[0].line.dash == "dash"

    # Check annotation on ATL line
    annotations = fig.layout.annotations
    assert any("ATL: EUR 429.00" in a.text for a in annotations)


def test_build_line_chart_empty() -> None:
    fig = build_line_chart([])
    assert fig is not None
    assert fig.layout.showlegend is False
    assert any("No price history" in a.text for a in fig.layout.annotations)


def test_build_bar_chart() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)
    points = [
        SitePricePoint(
            site_key="amazon.es",
            site_display_name="Amazon.es",
            price_amount=450.0,
            currency="EUR",
            observed_at=now,
        ),
        SitePricePoint(
            site_key="pccomponentes",
            site_display_name="PcComponentes",
            price_amount=429.0,
            currency="EUR",
            observed_at=now,
        ),
    ]
    fig = build_bar_chart(points)
    assert fig is not None
    assert len(fig.data) == 1
    # PcComponentes (429.0) should be first (cheapest first)
    assert fig.data[0].x[0] == "PcComponentes"
    assert fig.data[0].y[0] == 429.0


def test_build_forecast_chart_has_only_a_projected_confidence_band() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)
    points = [
        SitePricePoint(
            site_key="amazon.es",
            site_display_name="Amazon.es",
            price_amount=500.0 - (index * 5),
            currency="EUR",
            observed_at=now.replace(day=index + 1),
        )
        for index in range(8)
    ]
    # Spread the series over the required 21-day minimum.
    points[-1] = SitePricePoint(
        site_key="amazon.es",
        site_display_name="Amazon.es",
        price_amount=465.0,
        currency="EUR",
        observed_at=now.replace(day=28),
    )
    forecast = forecast_prices(points)

    figure = build_forecast_chart(forecast)

    assert forecast.is_available is True
    assert len(figure.data) == 2
    assert figure.data[1].fill == "tonexty"
    assert figure.data[1].line.dash == "dash"
    assert "PROJECTED — NOT A GUARANTEE" in figure.layout.annotations[0].text
    metadata = _forecast_metadata(forecast)
    assert "80% confidence band" in metadata
    assert "last retrained" in metadata


def test_build_hero_metrics() -> None:
    stats = ProductPriceStats(
        all_time_low=429.0,
        all_time_low_currency="EUR",
        avg_30d=484.0,
        avg_30d_currency="EUR",
    )
    current_lowest = 449.0
    badges = _build_hero_metrics(stats, current_lowest)
    assert len(badges) == 2

    # Check ATL badge
    atl_badge = cast(Any, badges[0])
    assert atl_badge.children == "ATL: EUR 429.00"
    assert "badge-atl" in str(atl_badge.className)

    # Check 30d delta pill: current 449 vs avg 484 -> -35.00 / -7.2%
    delta_pill = cast(Any, badges[1])
    assert "-EUR 35.00 / -7.2% vs 30-day avg" in str(delta_pill.children)
    assert "pill-delta-pos" in str(delta_pill.className)


def test_build_statistic_badges() -> None:
    price_stats = PriceSeriesStats(
        window_days=30,
        count=4,
        coefficient_of_variation=0.06,
        iqr_pct_of_median=0.08,
        trend_per_day=-0.5,
        trend_per_week=-3.5,
        trend_pct_per_week=-0.0078,
        currency="EUR",
    )

    assert "±6.0% over last 30d" in str(_build_volatility_badge(price_stats).children)
    assert "▼ -EUR 3.50/wk" in str(_build_trend_indicator(price_stats).children)


def test_format_delta_vs_avg() -> None:
    # Cheaper than avg
    span = cast(Any, _format_delta_vs_avg(400.0, 500.0, "EUR"))
    assert "-EUR 100.00 (-20.0%)" in str(span.children)
    assert "pill-delta-pos" in str(span.className)

    # More expensive than avg
    span_neg = cast(Any, _format_delta_vs_avg(550.0, 500.0, "EUR"))
    assert "+EUR 50.00 (+10.0%)" in str(span_neg.children)
    assert "pill-delta-neg" in str(span_neg.className)

    # None cases
    span_none = cast(Any, _format_delta_vs_avg(None, 500.0, "EUR"))
    assert span_none.children == "—"


def test_retailer_table_columns() -> None:
    now = datetime(2026, 8, 21, 12, 0, 0)
    listings = [
        ListingSummary(
            site_key="amazon.es",
            site_display_name="Amazon.es",
            url="https://amazon.es/dp/B123",
            image_url=None,
            price_amount=450.0,
            currency="EUR",
            observed_at=now,
        ),
        ListingSummary(
            site_key="pccomponentes",
            site_display_name="PcComponentes",
            url="https://pccomponentes.com/item",
            image_url=None,
            price_amount=None,
            currency=None,
            observed_at=None,
        ),
    ]
    table = _retailer_table(listings, avg_30d=500.0)
    assert table is not None
    table_any = cast(Any, table)
    # Check headers
    thead = table_any.children[0]
    headers = [th.children for th in thead.children.children]
    assert headers == ["Store", "Price", "Stock", "Shipping", "Price vs Avg", "Link"]
