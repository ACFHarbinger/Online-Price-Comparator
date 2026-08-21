"""SQLite connection management and bootstrap."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Column, Engine, create_engine, inspect, text

from storage.schema import metadata


def create_db_engine(database_path: str) -> Engine:
    """Create (and bootstrap/migrate, if needed) the SQLite engine at `database_path`.

    Also adds any columns present in `metadata` but missing from an
    existing DB file (see `_add_missing_columns`).
    """
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    metadata.create_all(engine)
    _add_missing_columns(engine)
    return engine


def _add_missing_columns(engine: Engine) -> None:
    """Additive-only schema sync: add columns `metadata` has that the DB lacks.

    A deliberately minimal stand-in for real migrations (Alembic) - this
    project's schema changes so far have all been new nullable/defaulted
    columns, so this covers them without adding a migrations framework.
    Never drops, renames, or alters an existing column. Pre-existing rows
    simply get NULL in the new column (e.g. a listing persisted before
    `match_status` existed) - every read-side query already treats an
    unmatched/unset value as "not confirmed", so old rows are safely
    excluded rather than misread, not corrupted.
    """
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in metadata.tables.values():
            if not inspector.has_table(table.name):
                continue
            existing_columns = {
                col["name"] for col in inspector.get_columns(table.name)
            }
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                conn.execute(text(_add_column_ddl(table.name, column, engine)))


def _add_column_ddl(table_name: str, column: Column[object], engine: Engine) -> str:
    """`ALTER TABLE ... ADD COLUMN ...` DDL for one missing column.

    Intentionally omits NOT NULL/DEFAULT even if the column is declared
    `nullable=False` in `schema.py` - SQLite requires a non-null default to
    backfill existing rows for a NOT NULL column, and there's no sensible
    synthetic default for something like `match_status`. Application code
    always supplies a value on insert, so this only affects historical rows.
    """
    type_sql = column.type.compile(dialect=engine.dialect)
    return f"ALTER TABLE {table_name} ADD COLUMN {column.name} {type_sql}"
