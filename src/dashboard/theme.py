"""Shared visual tokens for the dark financial-terminal dashboard."""

from __future__ import annotations

# ruff: noqa: E501

PAGE_BACKGROUND = "#0D1117"
PANEL_BACKGROUND = "#161B22"
PANEL_BORDER = "#21262D"
PRIMARY_TEXT = "#F0F6FC"
MUTED_TEXT = "#8B949E"
POSITIVE = "#3FB950"
NEGATIVE = "#F85149"
FALLBACK_RETAILER_COLOR = "#6E7681"

RETAILER_COLORS: dict[str, str] = {
    "amazon.es": "#F59E0B",
    "pccomponentes": "#06B6D4",
    "worten": "#EF4444",
    "fnac": "#EAB308",
    "pcdiga": "#8B5CF6",
    "kuantokusta": "#10B981",
    "chip7": "#EC4899",
}

UI_FONT = "Inter, system-ui, sans-serif"
MONO_FONT = '"JetBrains Mono", "Roboto Mono", monospace'

APP_CSS = f"""
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: {PAGE_BACKGROUND}; color: {PRIMARY_TEXT}; font-family: {UI_FONT}; }}
button, input {{ font: inherit; }}
.dashboard-shell {{ max-width: 1440px; margin: 0 auto; padding: 28px; }}
.dashboard-title {{ margin: 0 0 20px; font-size: 1.25rem; letter-spacing: .04em; }}
.search-row {{ display: flex; gap: 10px; margin-bottom: 16px; }}
.search-input {{ flex: 1; min-width: 0; padding: 11px 13px; color: {PRIMARY_TEXT}; background: {PANEL_BACKGROUND}; border: 1px solid {PANEL_BORDER}; border-radius: 6px; }}
.search-button {{ padding: 10px 18px; color: {PAGE_BACKGROUND}; background: {POSITIVE}; border: 0; border-radius: 6px; font-weight: 700; cursor: pointer; }}
.product-select {{ margin-bottom: 20px; }}
.show-browser-checkbox {{ margin: -6px 0 16px; font-size: .82rem; }}
.show-browser-checkbox label, .show-browser-checkbox label:hover,
.show-browser-checkbox label span, .show-browser-checkbox label:hover span {{
    color: {PRIMARY_TEXT} !important; opacity: 1 !important;
}}
.show-browser-checkbox input {{ margin-right: 6px; accent-color: {POSITIVE}; }}
.hero, .panel {{ background: {PANEL_BACKGROUND}; border: 1px solid {PANEL_BORDER}; border-radius: 8px; }}
.hero {{ display: flex; gap: 22px; align-items: center; min-height: 190px; padding: 22px; margin-bottom: 16px; }}
.product-image {{ width: 145px; height: 145px; object-fit: contain; background: {PAGE_BACKGROUND}; border-radius: 6px; }}
.product-image--empty {{ display: none; }}
.hero-copy {{ min-width: 0; }}
.product-name {{ margin: 0 0 12px; font-size: clamp(1.4rem, 2.5vw, 2rem); }}
.lowest-label {{ color: {MUTED_TEXT}; font-size: .75rem; font-weight: 700; letter-spacing: .08em; }}
.lowest-price, .price-value {{ font-family: {MONO_FONT}; font-variant-numeric: tabular-nums; }}
.lowest-price {{ margin-top: 5px; color: {POSITIVE}; font-size: 1.35rem; font-weight: 700; }}
.chart-grid {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr); gap: 16px; margin-bottom: 16px; }}
.panel {{ padding: 18px; }}
.panel-heading {{ margin: 0 0 12px; font-size: .84rem; color: {MUTED_TEXT}; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }}
.empty-message {{ color: {MUTED_TEXT}; padding: 24px 0; }}
.retailer-table {{ width: 100%; border-collapse: collapse; }}
.retailer-table th, .retailer-table td {{ padding: 12px 8px; text-align: left; border-top: 1px solid {PANEL_BORDER}; }}
.retailer-table th {{ color: {MUTED_TEXT}; font-size: .75rem; letter-spacing: .06em; text-transform: uppercase; }}
.retailer-table a {{ color: #58A6FF; }}
.dash-dropdown .Select-control, .dash-dropdown .Select-menu-outer, .dash-dropdown .Select-menu {{ background-color: {PANEL_BACKGROUND}; border-color: {PANEL_BORDER}; color: {PRIMARY_TEXT}; }}
.dash-dropdown .Select-value-label, .dash-dropdown .Select-placeholder {{ color: {MUTED_TEXT} !important; }}
.dash-dropdown .VirtualizedSelectOption {{ background-color: {PANEL_BACKGROUND}; color: {PRIMARY_TEXT}; }}
.dash-dropdown .VirtualizedSelectFocusedOption {{ background-color: {PANEL_BORDER}; }}
@media (max-width: 800px) {{ .dashboard-shell {{ padding: 16px; }} .chart-grid {{ grid-template-columns: 1fr; }} .hero {{ align-items: flex-start; }} .product-image {{ width: 100px; height: 100px; }} }}
"""
