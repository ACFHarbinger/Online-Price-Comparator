"""Storage repository for custom listing URLs (v2.15 Tier A)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import Engine, delete, select, update

from storage.schema import custom_listing_urls


def extract_site_info_from_url(url: str) -> tuple[str, str]:
    """Extract (site_key, site_display_name) from an arbitrary URL."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "unknown").lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        site_key = hostname.replace(".", "_")
        site_display_name = hostname.capitalize()
        return site_key, site_display_name
    except Exception:
        return "custom_site", "Custom Site"


@dataclass(frozen=True)
class CustomListingUrl:
    """A user-added custom listing URL tracked against a product."""

    tracked_product_id: int
    url: str
    site_key: str
    site_display_name: str
    added_at: datetime
    id: int | None = None
    parser_confidence: float | None = None
    status: str = "active"  # active, failed, unmatched, inactive
    last_checked_at: datetime | None = None
    last_error: str | None = None


class CustomListingUrlRepository:
    """Manages custom product page URLs in the `custom_listing_urls` table."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def _row_to_model(self, row: Any) -> CustomListingUrl:
        return CustomListingUrl(
            id=int(row.id),
            tracked_product_id=int(row.tracked_product_id),
            url=str(row.url),
            site_key=str(row.site_key),
            site_display_name=str(row.site_display_name),
            parser_confidence=(
                float(row.parser_confidence)
                if row.parser_confidence is not None
                else None
            ),
            status=str(row.status),
            last_checked_at=row.last_checked_at,
            last_error=str(row.last_error) if row.last_error is not None else None,
            added_at=row.added_at,
        )

    def add(self, custom: CustomListingUrl) -> int | None:
        """Add a new custom listing URL. Returns primary key or None if duplicate."""
        now = custom.added_at or datetime.now(UTC)
        site_key = custom.site_key
        site_display_name = custom.site_display_name
        if not site_key or not site_display_name:
            extracted_key, extracted_name = extract_site_info_from_url(custom.url)
            site_key = site_key or extracted_key
            site_display_name = site_display_name or extracted_name

        stmt = (
            custom_listing_urls.insert()
            .values(
                tracked_product_id=custom.tracked_product_id,
                url=custom.url,
                site_key=site_key,
                site_display_name=site_display_name,
                parser_confidence=custom.parser_confidence,
                status=custom.status,
                last_checked_at=custom.last_checked_at,
                last_error=custom.last_error,
                added_at=now,
            )
            .prefix_with("OR IGNORE")
        )
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            if (
                result.inserted_primary_key is not None
                and len(result.inserted_primary_key) > 0
                and result.inserted_primary_key[0] is not None
            ):
                return int(result.inserted_primary_key[0])

            # If ignored as duplicate, find existing ID
            existing = conn.execute(
                select(custom_listing_urls.c.id).where(
                    custom_listing_urls.c.tracked_product_id
                    == custom.tracked_product_id,
                    custom_listing_urls.c.url == custom.url,
                )
            ).scalar_one_or_none()
            return int(existing) if existing is not None else None

    def get(self, custom_id: int) -> CustomListingUrl | None:
        """Fetch a custom listing URL by ID."""
        stmt = select(custom_listing_urls).where(custom_listing_urls.c.id == custom_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).first()
            if row is None:
                return None
            return self._row_to_model(row)

    def get_by_url(self, tracked_product_id: int, url: str) -> CustomListingUrl | None:
        """Fetch by tracked product and exact URL."""
        stmt = select(custom_listing_urls).where(
            custom_listing_urls.c.tracked_product_id == tracked_product_id,
            custom_listing_urls.c.url == url,
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt).first()
            if row is None:
                return None
            return self._row_to_model(row)

    def list_for_product(self, tracked_product_id: int) -> list[CustomListingUrl]:
        """List all custom URLs added for a tracked product."""
        stmt = (
            select(custom_listing_urls)
            .where(custom_listing_urls.c.tracked_product_id == tracked_product_id)
            .order_by(custom_listing_urls.c.added_at.desc())
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
            return [self._row_to_model(row) for row in rows]

    def list_all_active(self) -> list[CustomListingUrl]:
        """List all active custom URLs across all tracked products."""
        stmt = (
            select(custom_listing_urls)
            .where(custom_listing_urls.c.status == "active")
            .order_by(custom_listing_urls.c.id.asc())
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).all()
            return [self._row_to_model(row) for row in rows]

    def update_status(
        self,
        custom_id: int,
        *,
        last_checked_at: datetime,
        parser_confidence: float | None = None,
        status: str = "active",
        last_error: str | None = None,
    ) -> None:
        """Update check timestamp and parser health for a custom URL."""
        values: dict[str, Any] = {
            "last_checked_at": last_checked_at,
            "status": status,
            "last_error": last_error,
        }
        if parser_confidence is not None:
            values["parser_confidence"] = parser_confidence

        stmt = (
            update(custom_listing_urls)
            .where(custom_listing_urls.c.id == custom_id)
            .values(**values)
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def remove(self, custom_id: int) -> bool:
        """Remove a custom listing URL."""
        stmt = delete(custom_listing_urls).where(custom_listing_urls.c.id == custom_id)
        with self.engine.begin() as conn:
            result = conn.execute(stmt)
            return bool(result.rowcount > 0)
