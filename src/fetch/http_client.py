"""Shared httpx client factory: sane timeouts, retries-friendly config, a real UA."""

from __future__ import annotations

import httpx

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def build_http_client(*, user_agent: str = DEFAULT_USER_AGENT) -> httpx.Client:
    """Build an httpx.Client configured with a real User-Agent and sane timeouts."""
    return httpx.Client(
        headers={"User-Agent": user_agent, "Accept-Language": "en-US,en;q=0.9"},
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
    )
