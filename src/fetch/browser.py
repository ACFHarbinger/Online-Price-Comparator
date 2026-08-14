"""Headless-browser fallback fetch, for sites a plain httpx GET can't render.

Playwright is an optional dependency (`pip install .[browser]` /
`uv sync --extra browser`, plus `playwright install chromium`) - imported
lazily here so the rest of the app works fine without it installed. Callers
must gate use of this module behind `Settings.browser_fallback_enabled` and
a per-site allowlist (`Settings.browser_fallback_site_keys()`); this module
itself does nothing to decide when it's appropriate to use.

Renders the page with a plain, honestly-identified headless Chromium and
nothing more - no stealth plugins, fingerprint spoofing, or CAPTCHA-solving.
Some sites' Cloudflare-style "JS challenge" auto-resolves for any browser
that can execute JavaScript, headless or not, which is what this relies on;
it does not attempt to defeat an interactive human challenge.
"""

from __future__ import annotations

import logging

from fetch.http_client import DEFAULT_USER_AGENT

LOGGER = logging.getLogger(__name__)


def fetch_rendered_html(
    url: str,
    *,
    wait_seconds: float = 5.0,
    timeout_ms: float = 20000,
    user_agent: str = DEFAULT_USER_AGENT,
) -> str | None:
    """Return the fully-rendered HTML for `url`, or None on any failure.

    `wait_seconds` is a fixed delay after navigation to let a JS challenge
    auto-resolve and the real page render, before reading the DOM - simpler
    and more predictable than trying to detect "challenge cleared" per site.
    """
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        LOGGER.warning(
            "browser fallback requested for %s but playwright is not "
            "installed (uv sync --extra browser && "
            "uv run playwright install chromium)",
            url,
        )
        return None

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=user_agent)
                page.goto(url, timeout=timeout_ms)
                page.wait_for_timeout(wait_seconds * 1000)
                return page.content()
            finally:
                browser.close()
    except PlaywrightError:
        LOGGER.warning("browser fallback fetch failed for %s", url, exc_info=True)
        return None
