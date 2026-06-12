from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from db.config import get_settings
from db.models import Base

settings = get_settings()


def _engine_kwargs(database_url: str) -> dict:
    kwargs = {"pool_pre_ping": True}
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
        if url.database and url.database != ":memory:":
            Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)
    return kwargs


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))


if engine.url.get_backend_name() == "sqlite":

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


# Columns added to the SQLite schema after a release. ``create_all`` makes missing
# *tables* but never ALTERs an existing one, so a committed/older ``hkcc.db`` read
# by newer model code would lack these. Deployments (e.g. Streamlit Cloud) read the
# committed DB without running Alembic, so this is the only place that heals drift.
# Keep in sync with the model definitions in :mod:`db.models`.
_SQLITE_LATE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "references": [
        ("needs_split", "BOOLEAN NOT NULL DEFAULT 0"),
        ("raw_citation", "TEXT"),
        ("pages", "VARCHAR(64)"),
    ],
}


def add_late_columns(bind=engine) -> None:
    """Idempotently ALTER-in any post-release SQLite columns. SQLite-only."""
    from sqlalchemy import text

    if bind.url.get_backend_name() != "sqlite":
        return
    with bind.begin() as conn:
        for table, cols in _SQLITE_LATE_COLUMNS.items():
            existing = {
                row[1] for row in conn.execute(text(f'PRAGMA table_info("{table}")'))
            }
            for name, ddl in cols:
                if name not in existing:
                    conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {name} {ddl}'))


def ensure_sqlite_schema(bind=engine) -> None:
    """Best-effort: bring an existing local SQLite DB up to the current model.

    Creates any missing tables (e.g. ``annotation_references``) and adds late
    columns. Guarded so it never (a) runs against Postgres, or (b) fabricates an
    empty DB when the app is API/remote-backed — it only heals a DB file that
    already exists. Failures (e.g. a read-only deploy filesystem) are swallowed:
    healing is an optimisation, not a hard dependency.
    """
    from sqlalchemy.exc import OperationalError

    url = bind.url
    if url.get_backend_name() != "sqlite":
        return
    db_path = url.database
    if db_path and db_path != ":memory:" and not Path(db_path).exists():
        return  # no local DB to heal; don't create an empty one
    try:
        Base.metadata.create_all(bind=bind)
        add_late_columns(bind)
    except OperationalError:
        pass
