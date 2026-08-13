"""Minimal per-host politeness throttle for scrapers."""

from __future__ import annotations

import time
from collections import defaultdict


class HostRateLimiter:
    """Blocks until at least `min_interval_seconds` has passed since the last
    request to a given host, so scrapers don't hammer a single site."""

    def __init__(self, min_interval_seconds: float = 1.5) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at: dict[str, float] = defaultdict(lambda: 0.0)

    def wait(self, host: str) -> None:
        """Sleep just long enough to respect the minimum interval for `host`."""
        now = time.monotonic()
        elapsed = now - self._last_request_at[host]
        remaining = self.min_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_at[host] = time.monotonic()
