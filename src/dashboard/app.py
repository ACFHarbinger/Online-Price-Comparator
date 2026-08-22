"""Application factory for the Online Price Comparator Dash interface."""

from __future__ import annotations

from dash import Dash

from config.settings import get_settings
from dashboard.callbacks import register_callbacks
from dashboard.extension_api import register_extension_api
from dashboard.layout import build_layout
from dashboard.theme import APP_CSS
from storage.db import create_db_engine

GOOGLE_FONT_STYLESHEET = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Roboto+Mono:wght@400;500;700&display=swap"

INDEX_STRING = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Online Price Comparator</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>"""


def create_app() -> Dash:
    """Create a fully wired Dash app without starting its development server."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    app = Dash(
        __name__,
        external_stylesheets=[GOOGLE_FONT_STYLESHEET],
        title="Online Price Comparator",
    )
    app.index_string = INDEX_STRING
    app.layout = build_layout()
    app.index_string = app.index_string.replace(
        "{%css%}",
        f"<style>{APP_CSS}</style>{{%css%}}",
    )
    register_callbacks(app, engine)
    # v2.20 v1: localhost-only endpoint the browser extension POSTs to.
    register_extension_api(app.server, engine)
    return app
