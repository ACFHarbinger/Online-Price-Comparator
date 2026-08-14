"""Shared low-level HTTP fetching concerns."""

from .browser import fetch_rendered_html
from .circuit_breaker import CircuitBreaker
from .http_client import DEFAULT_USER_AGENT, build_http_client, get_with_retry
from .rate_limit import HostRateLimiter
from .response_cache import get_cached, set_cached
from .robots import is_allowed

__all__ = [
    "DEFAULT_USER_AGENT",
    "CircuitBreaker",
    "HostRateLimiter",
    "build_http_client",
    "fetch_rendered_html",
    "get_cached",
    "get_with_retry",
    "is_allowed",
    "set_cached",
]
