"""Seed the EXTENDED-KCC (11-14) reference and candidate-assay layer.

The 14 framework definitions already ship in ``db/seed/kccs.json``; this pipeline
fills the gap left by the two upstream importers (KCAD / IARC 10-yr), which only
map the original ten characteristics. It populates, idempotently:

  * ``references``      - anchor literature for KCC 11-14
  * ``reference_tags``  - faceting tags
  * ``reference_kccs``  - reference -> KCC links (the join that was empty)
  * ``assays`` + ``assay_kccs`` - candidate method library for KCC 11-14

It NEVER writes ``evidence`` rows: per docs/KCC_EVIDENCE_RULES.md, agent x KCC
scores must come from a peer-reviewed source table or a curator Revision, not
from this seeder. Re-running is safe (merge / INSERT-OR-IGNORE semantics).

Usage:
    python -m pipelines.import_extended_kccs
    python -m pipelines.import_extended_kccs --data path/to/kcc11-14_extended.json
    python -m pipelines.import_extended_kccs --reset   # drop only extended-kcc rows first
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db.models import Assay, AssayKCC, KCC, Reference, ReferenceKCC, ReferenceTag
from db.session import SessionLocal, ensure_sqlite_schema

log = logging.getLogger("import_extended_kccs")

DEFAULT_DATA_FILE = (
    Path(__file__).resolve().parents[1] / "db" / "seed" / "refs" / "kcc11-14_extended.json"
)
SOURCE_TAG = "extended-kcc"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _known_kcc_ids(db: Session) -> set[str]:
    return set(db.scalars(select(KCC.id)).all())


def _reset_extended(db: Session) -> None:
    """Remove only rows previously written by this seeder (source='extended-kcc')."""
    ext_ref_ids = list(
        db.scalars(select(Reference.id).where(Reference.source == SOURCE_TAG)).all()
    )
    ext_assay_ids = list(
        db.scalars(select(Assay.id).where(Assay.source == SOURCE_TAG)).all()
    )
    if ext_ref_ids:
        db.execute(delete(ReferenceKCC).where(ReferenceKCC.reference_id.in_(ext_ref_ids)))
        db.execute(delete(ReferenceTag).where(ReferenceTag.reference_id.in_(ext_ref_ids)))
        db.execute(delete(Reference).where(Reference.id.in_(ext_ref_ids)))
    if ext_assay_ids:
        db.execute(delete(AssayKCC).where(AssayKCC.assay_id.in_(ext_assay_ids)))
        db.execute(delete(Assay).where(Assay.id.in_(ext_assay_ids)))
    db.commit()


def seed_extended(db: Session, data: dict, *, reset: bool = False) -> dict:
    if reset:
        _reset_extended(db)

    valid_kccs = _known_kcc_ids(db)
    report = {
        "refs": 0,
        "ref_tags": 0,
        "ref_kcc_links": 0,
        "assays": 0,
        "assay_kcc_links": 0,
        "skipped_kccs": [],
    }

    # --- references + tags + reference_kccs ---------------------------------
    for r in data.get("references", []):
        notes = r.get("_note")
        db.merge(
            Reference(
                id=r["id"],
                year=r.get("year"),
                authors=r.get("authors", "\u2014"),
                title=r.get("title", "\u2014"),
                journal=r.get("journal", "\u2014"),
                vol=r.get("vol"),
                doi=r.get("doi"),
                pmid=r.get("pmid"),
                source=r.get("source", SOURCE_TAG),
                url=r.get("url"),
                # Park provenance/review notes + verbatim citation for curator audit.
                raw_citation=notes,
            )
        )
        report["refs"] += 1
        for tag in r.get("tags", []) or []:
            db.merge(ReferenceTag(reference_id=r["id"], tag=tag))
            report["ref_tags"] += 1
        for kcc_id in r.get("kccs", []) or []:
            if kcc_id not in valid_kccs:
                report["skipped_kccs"].append((r["id"], kcc_id))
                continue
            db.merge(ReferenceKCC(reference_id=r["id"], kcc_id=kcc_id))
            report["ref_kcc_links"] += 1
    db.commit()

    # --- candidate assays + assay_kccs --------------------------------------
    for a in data.get("candidate_assays", []):
        db.merge(
            Assay(
                id=a["id"],
                name=a["name"],
                type=a.get("type", "\u2014"),
                target=a.get("target", "\u2014"),
                throughput=a.get("throughput", "\u2014"),
                oecd_tg=a.get("oecd_tg"),
                notes=a.get("notes"),
                source=a.get("source", SOURCE_TAG),
                granularity=a.get("granularity", "category"),
            )
        )
        report["assays"] += 1
        for kcc_id in a.get("kccs", []) or []:
            if kcc_id not in valid_kccs:
                report["skipped_kccs"].append((a["id"], kcc_id))
                continue
            db.merge(AssayKCC(assay_id=a["id"], kcc_id=kcc_id))
            report["assay_kcc_links"] += 1
    db.commit()
    return report


def run(
    *,
    data_path: Path = DEFAULT_DATA_FILE,
    reset: bool = False,
    db: Session | None = None,
) -> dict:
    """Load the extended-KCC reference and candidate-assay seed data."""
    data = _load(data_path)
    own_db = db is None
    if own_db:
        ensure_sqlite_schema()
        db = SessionLocal()
    try:
        report = seed_extended(db, data, reset=reset)
        log.info(
            "Extended-KCC seed complete: %d refs, %d tags, %d ref-KCC links, "
            "%d assays, %d assay-KCC links.",
            report["refs"],
            report["ref_tags"],
            report["ref_kcc_links"],
            report["assays"],
            report["assay_kcc_links"],
        )
        if report["skipped_kccs"]:
            log.warning("Skipped unknown KCC ids: %s", report["skipped_kccs"])
        return report
    finally:
        if own_db:
            db.close()


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Seed extended-KCC (11-14) reference + assay layer"
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_FILE)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop existing source='extended-kcc' rows first",
    )
    args = parser.parse_args(argv)
    run(data_path=args.data, reset=args.reset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
