"""SQLite connection management and bootstrap."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine

from storage.schema import metadata


def create_db_engine(database_path: str) -> Engine:
    """Create (and bootstrap, if needed) the SQLite engine at `database_path`."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    metadata.create_all(engine)
    return engine
