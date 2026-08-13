"""Command-line interface entry point for Online Price Comparator."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from config.settings import get_settings
from models.listing import RawListing
from normalize.price import parse_price
from pipeline.discover import run_discovery
from pipeline.snapshot import persist_snapshot
from storage.db import create_db_engine

__version__ = "0.1.0"


def _run_search(keywords: str, limit: int) -> int:
    """Discover, persist, and print a price snapshot for `keywords`."""
    settings = get_settings()
    engine = create_db_engine(settings.database_path)

    raw_listings = run_discovery(keywords, settings, limit=limit)
    if not raw_listings:
        print(f"No listings found for {keywords!r}.")
        return 0

    persist_snapshot(keywords, raw_listings, engine)

    priced: list[tuple[float, str, RawListing]] = []
    for raw in raw_listings:
        try:
            amount, currency = parse_price(raw.price_text, raw.currency_hint)
        except ValueError:
            continue
        priced.append((amount, currency, raw))

    if not priced:
        print(f"Found {len(raw_listings)} listing(s), but none had a parseable price.")
        return 0

    priced.sort(key=lambda p: p[0])
    print(f"Prices for {keywords!r} (results may include loosely-matched items):")
    for amount, currency, raw in priced:
        price = f"{amount:>10.2f} {currency}"
        title = raw.title[:60]
        print(f"  {price}  [{raw.site_display_name:<12}] {title}")
        print(f"             {raw.url}")
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
