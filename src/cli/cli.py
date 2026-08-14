"""Command-line interface entry point for Online Price Comparator."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from config.settings import get_settings
from pipeline.discover import run_discovery
from pipeline.snapshot import persist_snapshot
from storage.db import create_db_engine
from storage.repository import ListingRepository

__version__ = "0.1.0"


def _run_search(keywords: str, limit: int) -> int:
    """Discover, persist, and print a confirmed price snapshot for `keywords`."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)

    raw_listings = run_discovery(keywords, settings, limit=limit)
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

    args = parser.parse_args(argv)

    if args.version:
        print(f"online-price-comparator v{__version__}")
        return 0

    if args.command == "search":
        return _run_search(args.keywords, args.limit)

    if args.command == "dashboard":
        return _run_dashboard(args.host, args.port, args.debug)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
