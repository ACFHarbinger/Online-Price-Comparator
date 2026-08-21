"""End-to-end test that a configured SerpAPI provider flows through discovery."""

from __future__ import annotations

import httpx
import respx

from config.settings import Settings
from pipeline.discover import run_discovery
from search.providers.serpapi import SEARCH_URL

# A bogus enabled_scrapers allowlist yields an empty scraper list, so this test
# exercises only the search-provider path - no scraper makes a network call.
_NO_SCRAPERS = "__never__"


def _payload() -> dict[str, object]:
    return {
        "shopping_results": [
            {
                "title": "AMD Ryzen 9 9950X3D",
                "link": "https://www.amazon.es/dp/B0DGHHMW2G",
                "source": "Amazon.es",
                "price": "609,82 €",
            }
        ]
    }


@respx.mock
def test_run_discovery_surfaces_serpapi_rows_when_configured() -> None:
    """A configured SerpAPI provider contributes search_api rows to discovery."""
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=_payload())
    )
    settings = Settings(
        _env_file=None,
        serpapi_key="test-key",
        enabled_scrapers=_NO_SCRAPERS,  # type: ignore[call-arg]
    )

    results = run_discovery("AMD Ryzen 9 9950X3D", settings, limit=5)

    assert route.called is True
    serpapi_rows = [row for row in results if row.source == "serpapi"]
    assert len(serpapi_rows) == 1
    assert serpapi_rows[0].source_kind == "search_api"
    assert serpapi_rows[0].site_display_name == "Amazon.es"


@respx.mock
def test_run_discovery_without_key_omits_serpapi_rows() -> None:
    """No key -> the provider is skipped and discovery stays clean of SerpAPI."""
    settings = Settings(
        _env_file=None,
        enabled_scrapers=_NO_SCRAPERS,  # type: ignore[call-arg]
    )

    results = run_discovery("AMD Ryzen 9 9950X3D", settings, limit=5)

    assert not any(row.source == "serpapi" for row in results)
