"""Shared httpx client factory and a retrying GET helper."""

from __future__ import annotations

import logging
import random
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from config.settings import get_settings

LOGGER = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def build_http_client(*, user_agent: str = DEFAULT_USER_AGENT) -> httpx.Client:
    """Build an httpx.Client configured with a real User-Agent and sane timeouts."""
    return httpx.Client(
        headers={"User-Agent": user_agent, "Accept-Language": "en-US,en;q=0.9"},
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
    )


def get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    max_attempts: int = 2,
    initial_backoff_seconds: float = 2.0,
    max_backoff_seconds: float = 30.0,
) -> httpx.Response:
    """GET with retry-on-transient-failure, exponential backoff, jitter.

    Retries on: connection errors (httpx.ConnectError/httpx.TimeoutException/
    similar transport-level errors) and HTTP 429/500/502/503/504. Does NOT
    retry on other 4xx (403, 404, etc.) - those are treated as final, the
    caller decides what to do (e.g. a scraper's existing block-detection
    logic). Respects a `Retry-After` response header when present (seconds
    or HTTP-date - at minimum handle the common seconds-integer form,
    fall back to your own backoff value if the header is absent or
    unparseable). Backoff schedule: initial_backoff_seconds, doubling each
    retry, capped at max_backoff_seconds, with jitter. Raises the final
    httpx exception (or returns the final non-2xx response for the caller's
    existing `response.raise_for_status()` to handle) after exhausting
    `max_attempts` - don't swallow the final failure silently.
    """
    attempts = max(1, max_attempts)
    backoff = max(0.0, initial_backoff_seconds)
    cap = max(0.0, max_backoff_seconds)

    for attempt in range(attempts):
        try:
            response = client.get(url, headers=headers)
        except httpx.TransportError:
            if attempt >= attempts - 1:
                raise
            delay = _jittered_delay(backoff)
            LOGGER.debug(
                "GET %s transport error on attempt %s/%s; retrying in %.2fs",
                url,
                attempt + 1,
                attempts,
                delay,
                exc_info=True,
            )
            time.sleep(delay)
            backoff = min(backoff * 2.0, cap)
            continue

        if response.status_code in _RETRYABLE_STATUS_CODES and attempt < attempts - 1:
            retry_after = _retry_after_seconds(response)
            delay = _jittered_delay(retry_after if retry_after is not None else backoff)
            LOGGER.debug(
                "GET %s HTTP %s on attempt %s/%s; retrying in %.2fs",
                url,
                response.status_code,
                attempt + 1,
                attempts,
                delay,
            )
            time.sleep(delay)
            backoff = min(backoff * 2.0, cap)
            continue

        return response

    raise RuntimeError(f"GET {url} exhausted {attempts} attempts without a response")


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """Parse a Retry-After header as integer seconds or an HTTP-date."""
    raw = response.headers.get("Retry-After")
    if raw is None or not raw.strip():
        return None
    text = raw.strip()
    try:
        return max(0.0, float(int(text)))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def _jittered_delay(base_seconds: float) -> float:
    """Return `base` plus 0..request_jitter_fraction of `base` extra delay."""
    base = max(0.0, base_seconds)
    fraction = max(0.0, get_settings().request_jitter_fraction)
    return base + random.uniform(0.0, base * fraction)
