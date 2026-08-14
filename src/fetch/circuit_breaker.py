"""Per-site circuit breaker with process-wide shared state."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta

from config.settings import get_settings

_failure_counts: dict[str, int] = {}
_open_until_mono: dict[str, float] = {}
_lock = threading.Lock()


class CircuitBreaker:
    """Tracks consecutive failures per site key; once a threshold is hit,
    the site is 'open' (skip attempting) until a cooldown elapses.

    Module-level shared state (same rationale as HostRateLimiter) -
    constructing a new CircuitBreaker() anywhere should observe the same
    per-site state as any other instance in the process.

    Threshold and cooldown come from Settings
    (``block_circuit_breaker_failures``, ``block_circuit_breaker_cooldown_hours``),
    defaulting to 2 failures / 24h when unconfigured.
    """

    def is_open(self, site_key: str) -> bool:
        """True if `site_key` is currently paused after repeated failures."""
        with _lock:
            until = _open_until_mono.get(site_key)
            if until is None:
                return False
            return time.monotonic() < until

    def open_until(self, site_key: str) -> datetime | None:
        """UTC instant when the breaker closes, or None if it is not open."""
        with _lock:
            until = _open_until_mono.get(site_key)
            if until is None:
                return None
            remaining = until - time.monotonic()
            if remaining <= 0:
                return None
            return datetime.now(UTC) + timedelta(seconds=remaining)

    def record_failure(self, site_key: str) -> None:
        """Count a failure; open the breaker once the configured threshold is hit."""
        settings = get_settings()
        threshold = settings.block_circuit_breaker_failures
        cooldown_seconds = settings.block_circuit_breaker_cooldown_hours * 3600.0
        with _lock:
            count = _failure_counts.get(site_key, 0) + 1
            _failure_counts[site_key] = count
            if count >= threshold:
                cooldown = max(0.0, cooldown_seconds)
                _open_until_mono[site_key] = time.monotonic() + cooldown

    def record_success(self, site_key: str) -> None:
        """Reset the failure count and close the breaker for `site_key`."""
        with _lock:
            _failure_counts[site_key] = 0
            _open_until_mono.pop(site_key, None)
