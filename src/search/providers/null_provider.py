"""Always-empty provider, used as a safe default and in tests."""

from __future__ import annotations

from models.listing import RawListing


class NullProvider:
    """A `SearchProvider` that is always configured and always returns no
    results. Exercises the "no results, no crash" pipeline path in tests
    without requiring a real API key."""

    name = "null"

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        return []
