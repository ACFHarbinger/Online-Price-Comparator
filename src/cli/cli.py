"""Command-line interface entry point for Online Price Comparator."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from config.settings import get_settings
from pipeline.discover import run_discovery
from pipeline.refresh import (
    refresh_watchlist,
    run_monitoring_loop,
)
from pipeline.snapshot import persist_snapshot
from scrapers.registry import registered_site_keys
from storage.db import create_db_engine
from storage.repository import ListingRepository
from storage.watchlist import (
    SiteOverrideRepository,
    SiteSettingsRepository,
    TrackedProductRepository,
)

__version__ = "0.1.0"


def _run_search(keywords: str, limit: int) -> int:
    """Discover, persist, and print a confirmed price snapshot for `keywords`."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)

    raw_listings = run_discovery(keywords, settings, limit=limit, engine=engine)
    if not raw_listings:
        print(f"No listings found for {keywords!r}.")
        return 0

    product_id = persist_snapshot(keywords, raw_listings, engine)

    # Read back from the repository (not the raw discovery results) so the
    # terminal output reflects the same identity-matching and anomaly
    # filtering the dashboard uses - never an unfiltered/unmatched listing.
    listings = ListingRepository(engine).list_with_latest_price(product_id)
    priced = [listing for listing in listings if listing.price_amount is not None]

    if not priced:
        print(
            f"Found {len(raw_listings)} listing(s) for {keywords!r}, but none "
            "were confirmed matches with a parseable price."
        )
        return 0

    print(f"Confirmed prices for {keywords!r}:")
    for listing in priced:
        assert listing.price_amount is not None and listing.currency is not None
        price = f"{listing.price_amount:>10.2f} {listing.currency}"
        print(f"  {price}  [{listing.site_display_name:<12}] {listing.url}")
    return 0


def _run_track(keywords: str, limit: int, scope: str, no_refresh: bool) -> int:
    """Persist a watchlist entry and optionally run a first snapshot."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    tracked_repo = TrackedProductRepository(engine)
    tracked = tracked_repo.get_or_create(keywords, search_scope_tier=scope)
    print(
        f"Tracking {tracked.query_text!r} "
        f"(id={tracked.id}, product_id={tracked.product_id}, "
        f"scope={tracked.search_scope_tier})"
    )
    if no_refresh:
        return 0

    raw_listings = run_discovery(
        tracked.query_text,
        settings,
        limit=limit,
        engine=engine,
        tracked_product_id=tracked.id,
    )
    persist_snapshot(tracked.query_text, raw_listings, engine)
    tracked_repo.touch_last_checked(tracked.id)

    listings = ListingRepository(engine).list_with_latest_price(tracked.product_id)
    priced = [listing for listing in listings if listing.price_amount is not None]
    if not priced:
        print(
            f"Watchlist entry saved. Found {len(raw_listings)} listing(s), "
            "but none were confirmed matches with a parseable price."
        )
        return 0
    print(f"Confirmed prices for {tracked.query_text!r}:")
    for listing in priced:
        assert listing.price_amount is not None and listing.currency is not None
        price = f"{listing.price_amount:>10.2f} {listing.currency}"
        print(f"  {price}  [{listing.site_display_name:<12}] {listing.url}")
    return 0


def _run_untrack(keywords: str) -> int:
    """Disable a watchlist entry without deleting price history."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    tracked_repo = TrackedProductRepository(engine)
    tracked = tracked_repo.get_by_query(keywords)
    if tracked is None:
        print(f"No watchlist entry for {keywords!r}.")
        return 1
    tracked_repo.set_enabled(tracked.id, False)
    print(f"Disabled watchlist entry {tracked.query_text!r} (history kept).")
    return 0


def _run_watchlist() -> int:
    """Print every watchlist entry."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    tracked_repo = TrackedProductRepository(engine)
    override_repo = SiteOverrideRepository(engine)
    entries = tracked_repo.list_all()
    if not entries:
        print("Watchlist is empty. Use `track <keywords>` to add a product.")
        return 0
    print("Watchlist:")
    for item in entries:
        flag = "on" if item.enabled else "off"
        overrides = override_repo.list_for(item.id)
        extra = ""
        if overrides:
            parts = [
                f"{row.site_key}:{'in' if row.included else 'out'}" for row in overrides
            ]
            extra = "  overrides=" + ",".join(parts)
        print(
            f"  [{item.id}] {flag:3}  {item.search_scope_tier:8}  "
            f"{item.query_text}{extra}"
        )
    return 0


def _run_sites_list() -> int:
    """Print global site enablement for every registered scraper."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    disabled = SiteSettingsRepository(engine).disabled_keys()
    print("Sites:")
    for site_key in registered_site_keys(settings):
        flag = "off" if site_key in disabled else "on"
        print(f"  {flag:3}  {site_key}")
    return 0


def _require_registered_site(site_key: str) -> str | None:
    """Return a cleaned site key, or None after printing an error."""
    cleaned = site_key.strip()
    known = set(registered_site_keys(get_settings()))
    if cleaned not in known:
        known_list = ", ".join(sorted(known)) or "(none)"
        print(f"Unknown site {cleaned!r}. Known sites: {known_list}")
        return None
    return cleaned


def _run_sites_set(site_key: str, enabled: bool) -> int:
    """Set the global enabled flag for one registered site."""
    cleaned = _require_registered_site(site_key)
    if cleaned is None:
        return 1
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    SiteSettingsRepository(engine).set_enabled(cleaned, enabled)
    state = "enabled" if enabled else "disabled"
    print(f"Site {cleaned} {state} globally.")
    return 0


def _run_sites_set_collection(site_key: str, method: str) -> int:
    """Set a registered site's v2.20 collection method."""
    cleaned = _require_registered_site(site_key)
    if cleaned is None:
        return 1
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    try:
        SiteSettingsRepository(engine).set_collection_method(cleaned, method)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Site {cleaned} collection method set to {method.strip()!r}.")
    return 0


def _run_sites_collection_methods() -> int:
    """Print each registered site's current collection method."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    methods = {
        row.site_key: row.collection_method
        for row in SiteSettingsRepository(engine).list_all()
    }
    print("Site collection methods:")
    for site_key in registered_site_keys(settings):
        method = methods.get(site_key, "server_scrape")
        print(f"  {method:<16}  {site_key}")
    return 0


def _run_site_override(
    keywords: str,
    site_key: str,
    *,
    included: bool | None,
    reason: str | None,
) -> int:
    """Set or clear a per-tracked-product site exception."""
    cleaned = _require_registered_site(site_key)
    if cleaned is None:
        return 1
    settings = get_settings()
    engine = create_db_engine(settings.database_path)
    tracked = TrackedProductRepository(engine).get_by_query(keywords)
    if tracked is None:
        print(f"No watchlist entry for {keywords!r}. Track it first.")
        return 1
    overrides = SiteOverrideRepository(engine)
    if included is None:
        overrides.clear_override(tracked.id, cleaned)
        print(
            f"Cleared site override for {cleaned} on {tracked.query_text!r} "
            "(follows global default)."
        )
        return 0
    overrides.set_override(tracked.id, cleaned, included=included, reason=reason)
    verb = "included in" if included else "excluded from"
    note = f" ({reason})" if reason else ""
    print(f"Site {cleaned} {verb} {tracked.query_text!r}{note}.")
    return 0


def _run_refresh(
    force: bool,
    limit: int,
    watch: bool,
    interval_seconds: float,
    import_extension_file: str | None,
) -> int:
    """Refresh prices for due (or all, if force) watchlist products.

    When ``import_extension_file`` is set, the detected changes exported by the
    v2.20 client-side monitor extension are first imported through the normal
    identity-matching -> condition -> FX -> persist_snapshot pipeline.
    """
    settings = get_settings()
    engine = create_db_engine(settings.database_path)

    if import_extension_file:
        from pipeline.extension_import import import_extension_file as _import

        result = _import(import_extension_file, engine)
        print(
            f"Imported {result.records_imported} extension record(s) "
            f"for {len(result.products_handled)} product(s)."
        )
        for reason in result.skipped:
            print(f"  skipped: {reason}")

    if watch:
        print(
            f"Starting passive watchlist monitoring (interval: {interval_seconds}s). "
            "Press Ctrl+C to stop."
        )
        try:
            run_monitoring_loop(
                engine,
                settings,
                check_interval_seconds=interval_seconds,
            )
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
        return 0

    refreshed = refresh_watchlist(engine, settings, force=force, limit=limit)
    if not refreshed:
        print("No watchlist products were due for refresh. Use --force to refresh all.")
        return 0

    print(f"Refreshed {len(refreshed)} watchlist product(s):")
    listing_repo = ListingRepository(engine)
    tracked_repo = TrackedProductRepository(engine)
    for prod_id, count in refreshed.items():
        tracked = tracked_repo.get(prod_id)
        name = tracked.query_text if tracked else f"Product #{prod_id}"
        target_prod_id = tracked.product_id if tracked else prod_id
        listings = listing_repo.list_with_latest_price(target_prod_id)
        priced = [item for item in listings if item.price_amount is not None]
        print(f"\n  [{prod_id}] {name} ({count} listings, {len(priced)} confirmed):")
        for listing in priced:
            assert listing.price_amount is not None and listing.currency is not None
            price = f"{listing.price_amount:>10.2f} {listing.currency}"
            print(f"    {price}  [{listing.site_display_name:<12}] {listing.url}")

    return 0


def _run_dashboard(host: str, port: int, debug: bool) -> int:
    """Launch the Dash dashboard's development server."""
    from dashboard.app import create_app

    app = create_app()
    app.run(host=host, port=port, debug=debug)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI main execution entry point.

    Args:
        argv: Optional command line argument list.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = argparse.ArgumentParser(
        prog="online-price-comparator",
        description="Search for a product across online retailers and compare prices.",
    )
    parser.add_argument("--version", action="store_true", help="Show version info")

    subparsers = parser.add_subparsers(dest="command")

    search_parser = subparsers.add_parser("search", help="Search for a product's price")
    search_parser.add_argument("keywords", help="Product keywords to search for")
    search_parser.add_argument(
        "--limit", type=int, default=20, help="Max results per source"
    )

    dashboard_parser = subparsers.add_parser(
        "dashboard", help="Launch the Dash price-comparison dashboard"
    )
    dashboard_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind the dev server to"
    )
    dashboard_parser.add_argument(
        "--port", type=int, default=8050, help="Port to bind the dev server to"
    )
    dashboard_parser.add_argument(
        "--debug", action="store_true", help="Run the Dash dev server in debug mode"
    )

    track_parser = subparsers.add_parser(
        "track", help="Add a product to the persistent watchlist"
    )
    track_parser.add_argument("keywords", help="Product keywords to track")
    track_parser.add_argument(
        "--limit", type=int, default=20, help="Max results per source on first refresh"
    )
    track_parser.add_argument(
        "--scope",
        choices=["local", "eu_wide", "global"],
        default="local",
        help="Search geography for this product (default: local = PT+ES)",
    )
    track_parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Save the watchlist entry without scraping",
    )

    refresh_parser = subparsers.add_parser(
        "refresh", help="Refresh prices for tracked watchlist products"
    )
    refresh_parser.add_argument(
        "--force",
        "--all",
        action="store_true",
        dest="force",
        help="Refresh all enabled products even if not yet due",
    )
    refresh_parser.add_argument(
        "--limit", type=int, default=20, help="Max results per source"
    )
    refresh_parser.add_argument(
        "--watch",
        action="store_true",
        help="Run continuously as a monitoring loop",
    )
    refresh_parser.add_argument(
        "--interval-seconds",
        type=float,
        default=60.0,
        help="Seconds between monitoring passes in watch mode",
    )
    refresh_parser.add_argument(
        "--import-extension-file",
        type=str,
        default=None,
        help=(
            "Import detected changes exported by the v2.20 client-side monitor "
            "extension (a JSON-lines file) before refreshing"
        ),
    )

    untrack_parser = subparsers.add_parser(
        "untrack", help="Disable a watchlist entry (price history is kept)"
    )
    untrack_parser.add_argument("keywords", help="Product keywords to untrack")

    subparsers.add_parser("watchlist", help="List persistent watchlist entries")

    sites_parser = subparsers.add_parser(
        "sites", help="Enable/disable retailers globally or per tracked product"
    )
    sites_sub = sites_parser.add_subparsers(dest="sites_command")
    sites_sub.add_parser("list", help="Show global site enablement")
    enable_parser = sites_sub.add_parser("enable", help="Enable a site globally")
    enable_parser.add_argument("site_key")
    disable_parser = sites_sub.add_parser("disable", help="Disable a site globally")
    disable_parser.add_argument("site_key")
    exclude_parser = sites_sub.add_parser(
        "exclude", help="Opt a site out of one tracked product"
    )
    exclude_parser.add_argument("keywords")
    exclude_parser.add_argument("site_key")
    exclude_parser.add_argument("--reason", default=None)
    include_parser = sites_sub.add_parser(
        "include", help="Opt a site into one tracked product (even if globally off)"
    )
    include_parser.add_argument("keywords")
    include_parser.add_argument("site_key")
    include_parser.add_argument("--reason", default=None)
    clear_parser = sites_sub.add_parser(
        "clear-override", help="Drop a per-product site exception"
    )
    clear_parser.add_argument("keywords")
    clear_parser.add_argument("site_key")
    set_collection_parser = sites_sub.add_parser(
        "set-collection",
        help=(
            "Set a site's collection method "
            "(server_scrape / client_extension / search_api / hint_only)"
        ),
    )
    set_collection_parser.add_argument("site_key")
    set_collection_parser.add_argument("method")
    sites_sub.add_parser(
        "collection-methods",
        help="Show each registered site's current collection method",
    )

    args = parser.parse_args(argv)

    if args.version:
        print(f"online-price-comparator v{__version__}")
        return 0

    if args.command == "search":
        return _run_search(args.keywords, args.limit)

    if args.command == "dashboard":
        return _run_dashboard(args.host, args.port, args.debug)

    if args.command == "track":
        return _run_track(args.keywords, args.limit, args.scope, args.no_refresh)

    if args.command == "refresh":
        return _run_refresh(
            args.force,
            args.limit,
            args.watch,
            args.interval_seconds,
            args.import_extension_file,
        )

    if args.command == "untrack":
        return _run_untrack(args.keywords)

    if args.command == "watchlist":
        return _run_watchlist()

    if args.command == "sites":
        sites_command = args.sites_command
        if sites_command in (None, "list"):
            return _run_sites_list()
        if sites_command == "enable":
            return _run_sites_set(args.site_key, True)
        if sites_command == "disable":
            return _run_sites_set(args.site_key, False)
        if sites_command == "exclude":
            return _run_site_override(
                args.keywords, args.site_key, included=False, reason=args.reason
            )
        if sites_command == "include":
            return _run_site_override(
                args.keywords, args.site_key, included=True, reason=args.reason
            )
        if sites_command == "clear-override":
            return _run_site_override(
                args.keywords, args.site_key, included=None, reason=None
            )
        if sites_command == "set-collection":
            return _run_sites_set_collection(args.site_key, args.method)
        if sites_command == "collection-methods":
            return _run_sites_collection_methods()

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
