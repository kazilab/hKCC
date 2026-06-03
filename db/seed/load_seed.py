"""Seed KCC framework definitions into the configured hKCC database."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from db.models import KCC
from db.session import SessionLocal

SEED_DIR = Path(__file__).resolve().parent
KCC_SEED_PATH = SEED_DIR / "kccs.json"


def _load_kcc_rows() -> list[dict]:
    return json.loads(KCC_SEED_PATH.read_text(encoding="utf-8"))["kccs"]


def seed_framework_session(db: Session, *, reset: bool = False) -> None:
    """Seed only the KCC framework definitions."""
    if reset:
        db.execute(delete(KCC))
        db.commit()

    for row in _load_kcc_rows():
        db.merge(
            KCC(
                id=row["id"],
                n=row["n"],
                title=row["title"],
                short=row["short"],
                description=row["description"],
                mechanism=row.get("mechanism", ""),
                icon=row["icon"],
                is_extended=bool(row.get("is_extended")),
            )
        )
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed hKCC database")
    parser.add_argument("--reset", action="store_true", help="Clear tables before seeding")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        seed_framework_session(db, reset=args.reset)
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
