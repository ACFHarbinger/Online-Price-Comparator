"""Process-wide per-host politeness throttle for scrapers."""

from __future__ import annotations

import random
import threading
import time
from collections import defaultdict

from config.settings import get_settings

# Shared across every HostRateLimiter instance in this process so constructing
# a fresh limiter per search() (or per scraper instance) still coordinates.
_last_request_at: dict[str, float] = defaultdict(lambda: 0.0)
_lock = threading.Lock()


class HostRateLimiter:
    """Blocks until at least `min_interval_seconds` has passed since the last
    request to a given host, so scrapers don't hammer a single site.

    Timing state lives at module level, not on the instance: any
    ``HostRateLimiter()`` in this process shares the same per-host clock.

    Jitter is read from ``Settings.request_jitter_fraction`` (default 0.20)
    inside ``wait()`` rather than taken as a constructor argument, so existing
    ``HostRateLimiter(min_interval_seconds).wait(host)`` call sites stay
    unchanged and one env var controls jitter process-wide.
    """

    def __init__(self, min_interval_seconds: float = 1.5) -> None:
        self.min_interval_seconds = min_interval_seconds

    def wait(self, host: str) -> None:
        """Sleep long enough to respect the minimum interval plus jitter for `host`."""
        jitter_fraction = max(0.0, get_settings().request_jitter_fraction)
        extra = random.uniform(0.0, self.min_interval_seconds * jitter_fraction)
        with _lock:
            now = time.monotonic()
            elapsed = now - _last_request_at[host]
            remaining = self.min_interval_seconds - elapsed
            delay = max(0.0, remaining) + extra
            # Reserve the slot before sleeping so concurrent waiters stack.
            _last_request_at[host] = now + delay
        if delay > 0:
            time.sleep(delay)
