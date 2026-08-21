"""Plotly figure builders for price snapshot and history views."""

from __future__ import annotations

from collections import defaultdict

import plotly.graph_objects as go  # type: ignore[import-untyped]
from dashboard.theme import (
    FALLBACK_RETAILER_COLOR,
    MONO_FONT,
    MUTED_TEXT,
    PANEL_BACKGROUND,
    PANEL_BORDER,
    POSITIVE,
    PRIMARY_TEXT,
    RETAILER_COLORS,
    UI_FONT,
)
from storage.repository import SitePricePoint


def _color_for(site_key: str) -> str:
    return RETAILER_COLORS.get(site_key, FALLBACK_RETAILER_COLOR)


def _base_figure() -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        paper_bgcolor=PANEL_BACKGROUND,
        plot_bgcolor=PANEL_BACKGROUND,
        font={"family": UI_FONT, "color": PRIMARY_TEXT},
        margin={"l": 52, "r": 18, "t": 16, "b": 45},
        hoverlabel={"font": {"family": MONO_FONT}},
        xaxis={"gridcolor": PANEL_BORDER, "linecolor": PANEL_BORDER},
        yaxis={
            "gridcolor": PANEL_BORDER,
            "linecolor": PANEL_BORDER,
            "tickprefix": "EUR ",
            "tickfont": {"family": MONO_FONT},
        },
        showlegend=True,
        legend={"font": {"color": MUTED_TEXT}, "orientation": "h", "y": -0.24},
    )
    return figure


def _empty_figure(message: str) -> go.Figure:
    figure = _base_figure()
    figure.update_layout(
        showlegend=False, xaxis={"visible": False}, yaxis={"visible": False}
    )
    figure.add_annotation(
        text=message,
        showarrow=False,
        font={"family": UI_FONT, "size": 14, "color": MUTED_TEXT},
    )
    return figure


def build_bar_chart(points: list[SitePricePoint]) -> go.Figure:
    """Build a cheapest-first current-price bar chart, one bar per retailer."""
    if not points:
        return _empty_figure("No current prices recorded yet")

    sorted_points = sorted(points, key=lambda point: point.price_amount)
    figure = _base_figure()
    figure.add_bar(
        x=[point.site_display_name for point in sorted_points],
        y=[point.price_amount for point in sorted_points],
        marker_color=[_color_for(point.site_key) for point in sorted_points],
        customdata=[[point.currency] for point in sorted_points],
        hovertemplate="%{x}<br>%{customdata[0]} %{y:,.2f}<extra></extra>",
    )
    figure.update_layout(showlegend=False, bargap=0.35)
    figure.update_xaxes(tickangle=-25, tickfont={"color": MUTED_TEXT})
    return figure


def build_line_chart(
    points: list[SitePricePoint], *, all_time_low: float | None = None
) -> go.Figure:
    """Build a historical price chart with range selectors and an ATL line."""
    if not points:
        return _empty_figure("No price history recorded yet")

    by_site: defaultdict[str, list[SitePricePoint]] = defaultdict(list)
    for point in points:
        by_site[point.site_key].append(point)

    figure = _base_figure()
    for site_key, site_points in sorted(by_site.items()):
        ordered_points = sorted(site_points, key=lambda point: point.observed_at)
        figure.add_scatter(
            x=[point.observed_at for point in ordered_points],
            y=[point.price_amount for point in ordered_points],
            mode="lines+markers",
            name=ordered_points[0].site_display_name,
            line={"color": _color_for(site_key), "width": 2},
            marker={"color": _color_for(site_key), "size": 7},
            customdata=[[point.currency] for point in ordered_points],
            hovertemplate=(
                "%{x|%Y-%m-%d %H:%M}<br>%{customdata[0]} %{y:,.2f}"
                "<extra>%{fullData.name}</extra>"
            ),
        )

    if all_time_low is not None:
        figure.add_hline(
            y=all_time_low,
            line_dash="dash",
            line_color=POSITIVE,
            line_width=1.5,
            annotation_text=f"ATL: EUR {all_time_low:,.2f}",
            annotation_position="bottom right",
            annotation_font={"family": MONO_FONT, "size": 11, "color": POSITIVE},
        )

    figure.update_xaxes(
        tickfont={"color": MUTED_TEXT},
        type="date",
        rangeselector={
            "buttons": [
                {"count": 7, "label": "1W", "step": "day", "stepmode": "backward"},
                {"count": 1, "label": "1M", "step": "month", "stepmode": "backward"},
                {"count": 3, "label": "3M", "step": "month", "stepmode": "backward"},
                {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
                {"step": "all", "label": "ALL"},
            ],
            "bgcolor": PANEL_BACKGROUND,
            "activecolor": PANEL_BORDER,
            "bordercolor": PANEL_BORDER,
            "borderwidth": 1,
            "font": {"family": UI_FONT, "color": PRIMARY_TEXT, "size": 11},
        },
    )
    return figure
