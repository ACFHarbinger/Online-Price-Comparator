"""Short-lived in-process cache of successful scraper HTML responses."""

from __future__ import annotations

import threading
import time

from config.settings import get_settings

_cache: dict[tuple[str, str], tuple[float, str]] = {}
_lock = threading.Lock()


def _normalize_query(query: str) -> str:
    """Collapse trivial whitespace/casing differences for cache keys."""
    return query.strip().lower()


def get_cached(site_key: str, query: str) -> str | None:
    """Return a cached HTML body if one was stored recently enough, else None."""
    key = (site_key, _normalize_query(query))
    ttl = float(get_settings().response_cache_ttl_seconds)
    now = time.monotonic()
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        stored_at, html = entry
        if now - stored_at > ttl:
            del _cache[key]
            return None
        return html


def set_cached(site_key: str, query: str, html: str) -> None:
    """Store a successful response, keyed by (site_key, normalized query)."""
    key = (site_key, _normalize_query(query))
    with _lock:
        _cache[key] = (time.monotonic(), html)
