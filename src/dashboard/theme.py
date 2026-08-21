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
.hero-metrics {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 10px; }}
.hero-badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: .82rem; font-weight: 600; font-family: {MONO_FONT}; font-variant-numeric: tabular-nums; }}
.badge-atl {{ background: rgba(63, 185, 80, 0.15); color: {POSITIVE}; border: 1px solid rgba(63, 185, 80, 0.4); }}
.badge-tiered-low {{ background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.45); }}
.badge-percentile-low {{ background: rgba(168, 85, 247, 0.15); color: #C084FC; border: 1px solid rgba(168, 85, 247, 0.45); }}
.badge-tiered-row {{ display: inline-flex; align-items: center; margin-left: 6px; padding: 2px 6px; border-radius: 4px; font-size: .70rem; font-weight: 700; font-family: {MONO_FONT}; background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.35); }}
.badge-percentile-row {{ display: inline-flex; align-items: center; margin-left: 6px; padding: 2px 6px; border-radius: 4px; font-size: .70rem; font-weight: 700; font-family: {MONO_FONT}; background: rgba(168, 85, 247, 0.15); color: #C084FC; border: 1px solid rgba(168, 85, 247, 0.35); }}
.pill-delta-pos {{ background: rgba(63, 185, 80, 0.15); color: {POSITIVE}; border: 1px solid rgba(63, 185, 80, 0.4); }}
.pill-delta-neg {{ background: rgba(248, 81, 73, 0.15); color: {NEGATIVE}; border: 1px solid rgba(248, 81, 73, 0.4); }}
.pill-delta-neutral {{ background: rgba(139, 148, 158, 0.15); color: {MUTED_TEXT}; border: 1px solid {PANEL_BORDER}; }}
.badge-volatility {{ background: rgba(6, 182, 212, 0.12); color: #38BDF8; border: 1px solid rgba(6, 182, 212, 0.35); }}
.badge-trend-pos {{ background: rgba(63, 185, 80, 0.15); color: {POSITIVE}; border: 1px solid rgba(63, 185, 80, 0.4); }}
.badge-trend-neg {{ background: rgba(248, 81, 73, 0.15); color: {NEGATIVE}; border: 1px solid rgba(248, 81, 73, 0.4); }}
.badge-trend-neutral {{ background: rgba(139, 148, 158, 0.15); color: {MUTED_TEXT}; border: 1px solid {PANEL_BORDER}; }}
.stock-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
.stock-in {{ background-color: {POSITIVE}; }}
.stock-out {{ background-color: {NEGATIVE}; }}
.stock-stale {{ background-color: #F59E0B; }}
.stock-unknown {{ background-color: {MUTED_TEXT}; }}
.stale-banner {{ display: flex; align-items: center; gap: 10px; padding: 12px 16px; margin-bottom: 16px; background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 6px; color: #FBBF24; font-size: .84rem; }}
.stale-banner-icon {{ font-size: 1.1rem; flex-shrink: 0; }}
.stale-banner-title {{ font-weight: 700; margin-right: 4px; }}
.badge-blocked {{ display: inline-flex; align-items: center; margin-left: 8px; padding: 2px 6px; border-radius: 4px; font-size: .70rem; font-weight: 700; font-family: {MONO_FONT}; background: rgba(248, 81, 73, 0.2); color: {NEGATIVE}; border: 1px solid rgba(248, 81, 73, 0.45); }}
.badge-stale {{ display: inline-flex; align-items: center; margin-left: 6px; padding: 2px 6px; border-radius: 4px; font-size: .70rem; font-weight: 600; font-family: {MONO_FONT}; background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.35); }}
.price-strikethrough {{ text-decoration: line-through; opacity: 0.55; }}
.row-out-of-stock {{ opacity: 0.75; }}
.row-blocked {{ opacity: 0.7; }}
.reveal-anomalies-checkbox {{ margin: 0 0 16px; font-size: .82rem; }}
.reveal-anomalies-checkbox label, .reveal-anomalies-checkbox label:hover,
.reveal-anomalies-checkbox label span, .reveal-anomalies-checkbox label:hover span {{
    color: {MUTED_TEXT} !important; opacity: 1 !important;
}}
.reveal-anomalies-checkbox input {{ margin-right: 6px; accent-color: {POSITIVE}; }}
.chart-grid {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr); gap: 16px; margin-bottom: 16px; }}
.panel {{ padding: 18px; }}
.panel-heading {{ margin: 0 0 12px; font-size: .84rem; color: {MUTED_TEXT}; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }}
.forecast-panel {{ margin-bottom: 16px; border-color: rgba(88, 166, 255, 0.4); }}
.forecast-metadata {{ margin: -2px 0 10px; color: {MUTED_TEXT}; font-family: {MONO_FONT}; font-size: .76rem; }}
.empty-message {{ color: {MUTED_TEXT}; padding: 24px 0; }}
.retailer-table {{ width: 100%; border-collapse: collapse; }}
.retailer-table th, .retailer-table td {{ padding: 12px 8px; text-align: left; border-top: 1px solid {PANEL_BORDER}; }}
.retailer-table th {{ color: {MUTED_TEXT}; font-size: .75rem; letter-spacing: .06em; text-transform: uppercase; }}
.retailer-table a {{ color: #58A6FF; }}
.panel-header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
.discover-button {{ background-color: rgba(88, 166, 255, 0.15); border: 1px solid rgba(88, 166, 255, 0.4); color: #58A6FF; border-radius: 6px; padding: 6px 12px; font-size: .80rem; font-weight: 600; cursor: pointer; }}
.discover-button:hover {{ background-color: rgba(88, 166, 255, 0.25); }}
.candidate-table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
.candidate-table th, .candidate-table td {{ padding: 10px 8px; text-align: left; border-top: 1px solid {PANEL_BORDER}; font-size: .84rem; }}
.candidate-table th {{ color: {MUTED_TEXT}; font-size: .75rem; letter-spacing: .06em; text-transform: uppercase; }}
.btn-approve {{ background-color: rgba(63, 185, 80, 0.2); border: 1px solid rgba(63, 185, 80, 0.5); color: {POSITIVE}; border-radius: 4px; padding: 4px 8px; font-size: .75rem; font-weight: 600; cursor: pointer; margin-right: 6px; }}
.btn-approve:hover {{ background-color: rgba(63, 185, 80, 0.35); }}
.btn-reject {{ background-color: rgba(248, 81, 73, 0.15); border: 1px solid rgba(248, 81, 73, 0.4); color: {NEGATIVE}; border-radius: 4px; padding: 4px 8px; font-size: .75rem; font-weight: 600; cursor: pointer; }}
.btn-reject:hover {{ background-color: rgba(248, 81, 73, 0.3); }}
.badge-score {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: .72rem; font-family: {MONO_FONT}; background: rgba(56, 189, 248, 0.15); color: #38BDF8; }}
.custom-url-panel {{ margin-top: 16px; }}
.custom-url-input-row {{ display: flex; gap: 8px; margin-bottom: 12px; }}
.custom-url-input {{ flex: 1; background: {PANEL_BACKGROUND}; border: 1px solid {PANEL_BORDER}; color: {PRIMARY_TEXT}; border-radius: 6px; padding: 8px 12px; font-size: .84rem; }}
.custom-url-button {{ background-color: rgba(56, 189, 248, 0.2); border: 1px solid rgba(56, 189, 248, 0.4); color: #38BDF8; border-radius: 6px; padding: 8px 16px; font-size: .84rem; font-weight: 600; cursor: pointer; }}
.custom-url-button:hover {{ background-color: rgba(56, 189, 248, 0.35); }}
.custom-url-status {{ font-size: .80rem; margin-bottom: 8px; }}
.custom-url-table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
.custom-url-table th, .custom-url-table td {{ padding: 10px 8px; text-align: left; border-top: 1px solid {PANEL_BORDER}; font-size: .84rem; }}
.custom-url-table th {{ color: {MUTED_TEXT}; font-size: .75rem; letter-spacing: .06em; text-transform: uppercase; }}
.btn-remove-url {{ background: none; border: 1px solid rgba(248, 81, 73, 0.4); color: {NEGATIVE}; border-radius: 4px; padding: 2px 6px; font-size: .72rem; cursor: pointer; }}
.btn-remove-url:hover {{ background: rgba(248, 81, 73, 0.2); }}
.scorecard-panel {{ margin-top: 16px; }}
.scorecard-table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
.scorecard-table th, .scorecard-table td {{ padding: 12px 10px; text-align: left; border-top: 1px solid {PANEL_BORDER}; font-size: .84rem; vertical-align: top; }}
.scorecard-table th {{ color: {MUTED_TEXT}; font-size: .75rem; letter-spacing: .06em; text-transform: uppercase; }}
.scorecard-site-name {{ font-weight: 600; color: {PRIMARY_TEXT}; }}
.badge-condition {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: .70rem; font-family: {MONO_FONT}; font-weight: 600; background: rgba(139, 148, 158, 0.15); color: {MUTED_TEXT}; border: 1px solid {PANEL_BORDER}; text-transform: uppercase; }}
.scorecard-cell {{ display: flex; flex-direction: column; gap: 3px; }}
.scorecard-dim-ok {{ font-family: {MONO_FONT}; font-size: .82rem; font-weight: 600; color: {POSITIVE}; }}
.scorecard-dim-low {{ font-family: {MONO_FONT}; font-size: .82rem; font-weight: 600; color: #F59E0B; }}
.scorecard-dim-unavail {{ font-family: {MONO_FONT}; font-size: .82rem; font-weight: 500; color: {MUTED_TEXT}; font-style: italic; }}
.scorecard-detail {{ font-size: .72rem; color: {MUTED_TEXT}; line-height: 1.3; }}
.dash-dropdown .Select-control, .dash-dropdown .Select-menu-outer, .dash-dropdown .Select-menu {{ background-color: {PANEL_BACKGROUND}; border-color: {PANEL_BORDER}; color: {PRIMARY_TEXT}; }}
.dash-dropdown .Select-value-label, .dash-dropdown .Select-placeholder {{ color: {MUTED_TEXT} !important; }}
.dash-dropdown .VirtualizedSelectOption {{ background-color: {PANEL_BACKGROUND}; color: {PRIMARY_TEXT}; }}
.dash-dropdown .VirtualizedSelectFocusedOption {{ background-color: {PANEL_BORDER}; }}
@media (max-width: 800px) {{ .dashboard-shell {{ padding: 16px; }} .chart-grid {{ grid-template-columns: 1fr; }} .hero {{ align-items: flex-start; }} .product-image {{ width: 100px; height: 100px; }} }}
"""
