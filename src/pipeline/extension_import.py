"""Import detected changes from the client-side monitor extension (v2.20).

The v2.20 extension (see `extension/`) reads Leboncoin ad pages from the user's
own browser, records detected price changes locally, and exports them as a
JSON-lines file. This module reads that file and pushes each record through the
**same** identity-matching -> condition -> FX -> ``persist_snapshot`` pipeline
every other source uses - an extension-sourced observation is not a trust
shortcut (same principle as v2.15 Tier A). The URL of each record must belong
to a tracked product (via `custom_listing_urls` or an existing `listings` row),
otherwise the record cannot be attributed and is skipped.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, select

from models.listing import RawListing
from pipeline.snapshot import persist_snapshot
from storage.repository import MATCHED_STATUSES
from storage.schema import custom_listing_urls, listings, products
from storage.watchlist import TrackedProductRepository

logger = logging.getLogger(__name__)

DEFAULT_SITE_DISPLAY_NAME = "Leboncoin"


@dataclass(frozen=True)
class ExtensionImportResult:
    """Summary of one ``--import-extension-file`` run."""

    lines_read: int
    records_imported: int
    products_handled: list[str]
    skipped: list[str] = field(default_factory=list)  # reasons for skipped lines


def _parse_observed_at(value: Any) -> datetime:
    """Parse the ISO-8601 ``observed_at`` from a record; fall back to now."""
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            logger.warning("Unparseable observed_at %r; using now", value)
    return datetime.now().astimezone()


def read_extension_records(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSON-lines file of extension records; skip blank/invalid lines."""
    records: list[dict[str, Any]] = []
    file_path = Path(path)
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            logger.warning("Skipping non-JSON line in %s: %r", path, stripped[:80])
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _query_text_for_url(engine: Engine, url: str) -> str | None:
    """Resolve the tracked query_text a record's URL belongs to.

    Prefers ``custom_listing_urls`` (the v2.15 source the extension monitors),
    then falls back to an existing ``listings`` row -> product. Returns None if
    the URL is not attributable to any tracked product.
    """
    with engine.connect() as conn:
        custom_row = conn.execute(
            select(custom_listing_urls.c.tracked_product_id).where(
                custom_listing_urls.c.url == url
            )
        ).first()
        if custom_row is not None:
            tracked = TrackedProductRepository(engine).get(int(custom_row[0]))
            if tracked is not None:
                return tracked.query_text

        listing_row = conn.execute(
            select(listings.c.product_id)
            .where(listings.c.url == url, listings.c.match_status.in_(MATCHED_STATUSES))
            .order_by(listings.c.last_seen_at.desc())
            .limit(1)
        ).first()
        if listing_row is None:
            return None
        product_row = conn.execute(
            select(products.c.query_text).where(products.c.id == listing_row[0])
        ).first()
        return str(product_row[0]) if product_row is not None else None


def _record_to_raw_listing(record: dict[str, Any]) -> RawListing | None:
    """Map one extension record to a ``RawListing``, or None if unusable."""
    url = record.get("url")
    title = record.get("title")
    price_text = record.get("price_text")
    if not url or not title or not price_text:
        logger.warning("Skipping record missing url/title/price_text: %r", record)
        return None
    site_key = record.get("site_key") or "leboncoin"
    return RawListing(
        source=site_key,
        source_kind="scraper",
        title=str(title),
        url=str(url),
        price_text=str(price_text),
        currency_hint=record.get("currency_hint"),
        image_url=record.get("image_url"),
        site_display_name=record.get("site_display_name") or DEFAULT_SITE_DISPLAY_NAME,
        fetched_at=_parse_observed_at(record.get("observed_at")),
        extra={"collection_method": "client_extension"},
    )


def import_records(
    records: list[dict[str, Any]], engine: Engine
) -> ExtensionImportResult:
    """Import detected-change records into the price-history pipeline.

    Shared by the file-based import (``import_extension_file``) and the v2.20
    v1 localhost HTTP callback (``dashboard.extension_api``): both feed the same
    list of records through identity-matching -> condition -> FX ->
    ``persist_snapshot``.
    """
    raw_by_query: dict[str, list[RawListing]] = {}
    skipped: list[str] = []

    for record in records:
        raw = _record_to_raw_listing(record)
        if raw is None:
            continue
        query_text = _query_text_for_url(engine, raw.url)
        if query_text is None:
            skipped.append(f"unattributed URL {raw.url}")
            logger.warning(
                "Extension record for %s has no tracked product; skipping", raw.url
            )
            continue
        raw_by_query.setdefault(query_text, []).append(raw)

    imported = 0
    products_handled: list[str] = []
    for query_text, raw_listings in raw_by_query.items():
        try:
            products_handled.append(query_text)
            imported += len(raw_listings)
            persist_snapshot(query_text, raw_listings, engine)
        except Exception:  # pragma: no cover - one product must not block others
            logger.exception("persist_snapshot failed for %r", query_text)

    return ExtensionImportResult(
        lines_read=len(records),
        records_imported=imported,
        products_handled=sorted(products_handled),
        skipped=skipped,
    )


def import_extension_file(
    path: str | Path,
    engine: Engine,
) -> ExtensionImportResult:
    """Import detected changes from ``path`` into the price-history pipeline."""
    return import_records(read_extension_records(path), engine)
