"""Registry gating tests for the search providers (v2.17a)."""

from __future__ import annotations

from config.settings import Settings
from search.registry import enabled_providers


def test_enabled_providers_includes_configured_serpapi() -> None:
    settings = Settings(_env_file=None, serpapi_key="real-key")  # type: ignore[call-arg]
    names = [provider.name for provider in enabled_providers(settings)]
    assert "serpapi" in names


def test_enabled_providers_skips_unconfigured_serpapi() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    names = [provider.name for provider in enabled_providers(settings)]
    assert "serpapi" not in names
    # The null provider is always available so the tool works with no keys.
    assert "null" in names
