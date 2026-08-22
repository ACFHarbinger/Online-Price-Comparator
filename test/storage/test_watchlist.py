"""Tests for v2.1 watchlist tables and site enablement."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import Engine

from models.listing import RawListing
from pipeline.discover import run_discovery
from storage.schema import site_settings
from storage.watchlist import (
    SiteOverrideRepository,
    SiteSettingsRepository,
    TrackedProductRepository,
    resolve_site_keys,
)


def test_resolve_site_keys_global_and_per_product_exceptions() -> None:
    registered = ["amazon.es", "pccomponentes", "worten"]
    assert resolve_site_keys(registered) == registered

    without_pcc = resolve_site_keys(registered, globally_disabled={"pccomponentes"})
    assert without_pcc == ["amazon.es", "worten"]

    opted_out = resolve_site_keys(
        registered,
        overrides={"amazon.es": False},
    )
    assert opted_out == ["pccomponentes", "worten"]

    opted_in = resolve_site_keys(
        registered,
        globally_disabled={"amazon.es", "worten"},
        overrides={"amazon.es": True},
    )
    assert opted_in == ["amazon.es", "pccomponentes"]


def test_tracked_product_get_or_create_and_untrack(
    in_memory_engine: Engine,
) -> None:
    repo = TrackedProductRepository(in_memory_engine)
    first = repo.get_or_create("AMD Ryzen 9 9950X3D", search_scope_tier="eu_wide")
    assert first.query_text == "AMD Ryzen 9 9950X3D"
    assert first.enabled is True
    assert first.search_scope_tier == "eu_wide"
    assert first.product_id >= 1
    assert first.last_checked_at is None

    again = repo.get_or_create("AMD Ryzen 9 9950X3D")
    assert again.id == first.id
    assert again.product_id == first.product_id

    repo.set_enabled(first.id, False)
    disabled = repo.get(first.id)
    assert disabled is not None
    assert disabled.enabled is False

    reenabled = repo.get_or_create("AMD Ryzen 9 9950X3D", search_scope_tier="local")
    assert reenabled.id == first.id
    assert reenabled.enabled is True
    assert reenabled.search_scope_tier == "local"
    same = repo.get_or_create("AMD Ryzen 9 9950X3D", search_scope_tier="local")
    assert same.id == first.id
    assert repo.get(999_999) is None

    repo.touch_last_checked(first.id, when=datetime(2026, 8, 21, 12, 0, 0))
    touched = repo.get(first.id)
    assert touched is not None
    assert touched.last_checked_at == datetime(2026, 8, 21, 12, 0, 0)

    listed = repo.list_all(enabled_only=True)
    assert [item.query_text for item in listed] == ["AMD Ryzen 9 9950X3D"]


def test_tracked_product_rejects_empty_and_unknown_scope(
    in_memory_engine: Engine,
) -> None:
    repo = TrackedProductRepository(in_memory_engine)
    with pytest.raises(ValueError, match="query_text"):
        repo.get_or_create("   ")
    with pytest.raises(ValueError, match="search_scope_tier"):
        repo.get_or_create("ram", search_scope_tier="mars")
    with pytest.raises(ValueError, match="historical_low_alert_mode"):
        repo.get_or_create("ram", historical_low_alert_mode="psychic")


def test_site_settings_and_overrides(in_memory_engine: Engine) -> None:
    tracked = TrackedProductRepository(in_memory_engine).get_or_create("rtx 4070")
    sites = SiteSettingsRepository(in_memory_engine)
    overrides = SiteOverrideRepository(in_memory_engine)

    assert sites.disabled_keys() == set()
    sites.set_enabled("pccomponentes", False)
    assert sites.disabled_keys() == {"pccomponentes"}
    sites.set_enabled("pccomponentes", True)
    assert sites.disabled_keys() == set()
    persisted = {row.site_key: row.enabled for row in sites.list_all()}
    assert persisted["pccomponentes"] is True
    with pytest.raises(ValueError, match="site_key"):
        sites.set_enabled("  ", False)

    overrides.set_override(
        tracked.id,
        "amazon.es",
        included=False,
        reason="bundle-only listing",
    )
    assert overrides.as_map(tracked.id) == {"amazon.es": False}
    rows = overrides.list_for(tracked.id)
    assert len(rows) == 1
    assert rows[0].reason == "bundle-only listing"

    overrides.set_override(tracked.id, "amazon.es", included=True, reason="ok now")
    assert overrides.as_map(tracked.id) == {"amazon.es": True}

    overrides.clear_override(tracked.id, "amazon.es")
    assert overrides.as_map(tracked.id) == {}
    with pytest.raises(ValueError, match="site_key"):
        overrides.set_override(tracked.id, " ", included=False)


def test_site_settings_collection_method(in_memory_engine: Engine) -> None:
    sites = SiteSettingsRepository(in_memory_engine)
    assert sites.non_server_scrape_keys() == set()

    # A site with no row defaults to server_scrape (never in the non-scrape set).
    sites.set_enabled("pccomponentes", True)
    assert sites.non_server_scrape_keys() == set()
    assert sites.list_all()[0].collection_method == "server_scrape"

    # Flag Leboncoin as client_extension -> it is no longer server-scraped.
    with in_memory_engine.begin() as conn:
        conn.execute(
            site_settings.insert().values(
                site_key="leboncoin",
                enabled=True,
                collection_method="client_extension",
            )
        )
    assert sites.non_server_scrape_keys() == {"leboncoin"}
    by_key = {row.site_key: row for row in sites.list_all()}
    assert by_key["leboncoin"].collection_method == "client_extension"


def test_site_settings_shipping_cost_estimate(in_memory_engine: Engine) -> None:
    sites = SiteSettingsRepository(in_memory_engine)
    assert sites.shipping_cost_estimates() == {}

    sites.set_shipping_cost_estimate("fnac", 2.5)
    assert sites.shipping_cost_estimates() == {"fnac": 2.5}
    assert sites.list_all()[0].shipping_cost_estimate_eur == 2.5

    sites.set_shipping_cost_estimate("fnac", None)
    assert sites.shipping_cost_estimates() == {}
    assert sites.list_all()[0].shipping_cost_estimate_eur is None

    with pytest.raises(ValueError, match="negative"):
        sites.set_shipping_cost_estimate("fnac", -0.01)


class _FakeScraper:
    def __init__(self, site_key: str) -> None:
        self.site_key = site_key
        self.calls = 0

    def search(self, query: str, *, limit: int = 20) -> list[RawListing]:
        self.calls += 1
        return []


def test_run_discovery_honors_global_and_per_product_site_flags(
    in_memory_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    amazon = _FakeScraper("amazon.es")
    pcc = _FakeScraper("pccomponentes")
    monkeypatch.setattr(
        "pipeline.discover.enabled_scrapers",
        lambda _settings: [amazon, pcc],
    )
    monkeypatch.setattr(
        "pipeline.discover.enabled_providers",
        lambda _settings: [],
    )

    from config.settings import Settings

    settings = Settings()
    tracked = TrackedProductRepository(in_memory_engine).get_or_create("9950X3D")
    SiteSettingsRepository(in_memory_engine).set_enabled("pccomponentes", False)

    run_discovery("9950X3D", settings, engine=in_memory_engine)
    assert amazon.calls == 1
    assert pcc.calls == 0

    amazon.calls = 0
    SiteOverrideRepository(in_memory_engine).set_override(
        tracked.id, "pccomponentes", included=True
    )
    run_discovery(
        "9950X3D",
        settings,
        engine=in_memory_engine,
        tracked_product_id=tracked.id,
    )
    assert amazon.calls == 1
    assert pcc.calls == 1

    amazon.calls = 0
    pcc.calls = 0
    SiteOverrideRepository(in_memory_engine).set_override(
        tracked.id, "amazon.es", included=False
    )
    run_discovery(
        "9950X3D",
        settings,
        engine=in_memory_engine,
        tracked_product_id=tracked.id,
    )
    assert amazon.calls == 0
    assert pcc.calls == 1


def test_site_settings_set_collection_method(in_memory_engine: Engine) -> None:
    sites = SiteSettingsRepository(in_memory_engine)
    assert sites.non_server_scrape_keys() == set()

    sites.set_collection_method("leboncoin", "client_extension")
    assert sites.non_server_scrape_keys() == {"leboncoin"}
    by_key = {row.site_key: row for row in sites.list_all()}
    assert by_key["leboncoin"].collection_method == "client_extension"

    with pytest.raises(ValueError, match="collection_method"):
        sites.set_collection_method("leboncoin", "bogus")
    with pytest.raises(ValueError, match="site_key"):
        sites.set_collection_method("  ", "client_extension")

    # set_enabled alone leaves the default server_scrape.
    sites.set_enabled("pccomponentes", False)
    by_key2 = {row.site_key: row for row in sites.list_all()}
    assert by_key2["pccomponentes"].collection_method == "server_scrape"
