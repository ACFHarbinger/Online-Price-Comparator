"""Shared pytest fixtures for Online Price Comparator test suite."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from storage.schema import metadata


@pytest.fixture
def in_memory_engine() -> Engine:
    """A shared in-memory SQLite engine with the full schema bootstrapped.

    Uses ``StaticPool`` so every connection (and thus every repository/session
    opened against the returned engine) sees the same in-memory database —
    the default per-connection pool would otherwise give each connection a
    fresh, empty database. Schema tables are created via ``metadata.create_all``
    mirroring :func:`storage.db.create_db_engine`'s bootstrap step.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    return engine
