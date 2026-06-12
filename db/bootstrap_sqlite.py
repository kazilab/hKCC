"""Build a local SQLite database for hKCC.

This is the no-server path for local Streamlit/API use. It creates tables from
the current SQLAlchemy models rather than running Alembic migrations, because
the migration history targets PostgreSQL-style ALTER operations.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "hkcc.db"


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _format_size(path: Path) -> str:
    size = path.stat().st_size
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and populate a local hKCC SQLite database")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="SQLite file to create. Defaults to ./hkcc.db in the project root.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete the existing SQLite file before rebuilding it.",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only load the KCC framework definitions, skipping KCAD and IARC imports.",
    )
    parser.add_argument(
        "--skip-iarc",
        action="store_true",
        help="Load KCAD but skip the IARC 10-year retrospective matrix.",
    )
    args = parser.parse_args()

    db_path = args.db_path.expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if args.replace and db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = _sqlite_url(db_path)

    from db.models import Base
    from db.seed.load_seed import seed_framework_session
    from db.session import SessionLocal, add_late_columns, engine

    Base.metadata.create_all(bind=engine)
    add_late_columns(engine)

    db = SessionLocal()
    try:
        seed_framework_session(db)
    finally:
        db.close()

    if not args.seed_only:
        from pipelines import import_kcad

        import_kcad.run(reset=True, include_supplementary=True)

    if not args.seed_only and not args.skip_iarc:
        from pipelines import import_10yr_kcc

        import_10yr_kcc.run(reset=True)

    if not args.seed_only:
        from pipelines import import_extended_kccs

        import_extended_kccs.run(reset=True)

    print(f"SQLite database ready: {db_path} ({_format_size(db_path)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
