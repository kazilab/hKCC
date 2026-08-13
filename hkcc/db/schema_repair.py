"""Bring an existing SQLite file up to the constraints the ORM declares.

``create_all`` builds missing *tables* but never alters an existing one, and
``ALTER TABLE`` in SQLite cannot add a CHECK constraint. So constraints added to
the models after a table was first created never reached any shipped database:
``evidence`` declared five and carried two. The rows were all valid, but nothing
stopped an invalid one — a ``direction`` outside the vocabulary, or a protective
cell with a positive score — from being written by a future import or an API
consumer with write access.

This module performs SQLite's documented table-rebuild procedure, generating the
target DDL from the ORM metadata so the rebuilt table matches the models by
construction rather than by a hand-copied string.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateIndex, CreateTable

from hkcc.db.models import Base

# Tables whose declared constraints must exist in the shipped file. Add a table
# here when constraints are introduced after its first release.
_CONSTRAINED_TABLES = ("evidence",)


def _declared_constraint_names(table_name: str) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {c.name for c in table.constraints if c.name}


def missing_constraints(bind: Engine, table_name: str) -> set[str]:
    """Constraint names the ORM declares that the live table does not carry."""
    if bind.url.get_backend_name() != "sqlite":
        return set()
    if table_name not in inspect(bind).get_table_names():
        return set()
    with bind.connect() as conn:
        ddl = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:n"),
            {"n": table_name},
        ).scalar()
    ddl = ddl or ""
    return {name for name in _declared_constraint_names(table_name) if name not in ddl}


def rebuild_table(bind: Engine, table_name: str) -> None:
    """Rebuild one table with the full ORM DDL, preserving every row.

    Follows the procedure in the SQLite docs for schema changes ALTER TABLE
    cannot express. ``legacy_alter_table`` is enabled for the rename so that
    other tables' foreign keys keep pointing at ``<table_name>`` instead of
    being rewritten to the temporary name.
    """
    table = Base.metadata.tables[table_name]
    columns = [c.name for c in table.columns]
    tmp = f"{table_name}__rebuild"

    create_sql = str(CreateTable(table).compile(bind)).strip().replace(
        f"CREATE TABLE {table_name}", f'CREATE TABLE "{tmp}"', 1
    )
    index_sql = [str(CreateIndex(ix).compile(bind)).strip() for ix in table.indexes]
    column_list = ", ".join(f'"{c}"' for c in columns)

    raw = bind.raw_connection()
    try:
        cur = raw.cursor()
        cur.execute("PRAGMA foreign_keys=OFF")
        cur.execute("BEGIN")
        try:
            cur.execute(create_sql)
            cur.execute(f'INSERT INTO "{tmp}" ({column_list}) SELECT {column_list} FROM "{table_name}"')
            cur.execute(f'DROP TABLE "{table_name}"')
            cur.execute("PRAGMA legacy_alter_table=ON")
            cur.execute(f'ALTER TABLE "{tmp}" RENAME TO "{table_name}"')
            cur.execute("PRAGMA legacy_alter_table=OFF")
            for statement in index_sql:
                cur.execute(statement)
            violations = cur.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"rebuild of {table_name} broke foreign keys: {violations[:3]}")
            raw.commit()
        except Exception:
            raw.rollback()
            raise
        finally:
            cur.execute("PRAGMA foreign_keys=ON")
    finally:
        raw.close()


def ensure_constraints(bind: Engine) -> list[str]:
    """Rebuild any table missing a declared constraint. Returns those rebuilt.

    Idempotent: a database already carrying its constraints is untouched, so
    this is safe to call on every start-up.
    """
    if bind.url.get_backend_name() != "sqlite":
        return []
    rebuilt = []
    for table_name in _CONSTRAINED_TABLES:
        if missing_constraints(bind, table_name):
            rebuild_table(bind, table_name)
            rebuilt.append(table_name)
    return rebuilt
