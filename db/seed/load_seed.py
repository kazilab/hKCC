"""Load mockup data.js into the configured hKCC database."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from db.models import (
    KCC,
    Agent,
    AgentSite,
    Assay,
    AssayKCC,
    DatasetRelease,
    Evidence,
    EvidenceCitation,
    Reference,
    ReferenceKCC,
    ReferenceTag,
)
from db.seed.parse_mockup import load_mockup_data
from db.session import SessionLocal


def _normalize_cas(cas: str | None) -> str | None:
    if not cas or cas.strip() in ("—", "-", ""):
        return None
    return cas.strip()


def _normalize_group(group: str | None) -> str | None:
    if not group or group.strip() in ("—", "-", ""):
        return None
    return group.strip()


def seed_framework_session(db: Session, *, reset: bool = False) -> None:
    """Seed only the KCC framework definitions.

    This intentionally avoids the legacy demo agents, assays, references, and
    evidence rows from ``data.js``. The reference-backed SQLite build uses this
    as its starting point before importing KCAD and IARC data.
    """
    data = load_mockup_data()
    if reset:
        db.execute(delete(KCC))
        db.commit()

    for row in data["kccs"]:
        db.merge(
            KCC(
                id=row["id"],
                n=row["n"],
                title=row["title"],
                short=row["short"],
                description=row.get("desc") or row.get("description", ""),
                mechanism=row.get("mechanism", ""),
                icon=row["icon"],
                is_extended=bool(row.get("isNew")),
            )
        )
    db.commit()


def seed_session(db: Session, *, reset: bool = False) -> None:
    data = load_mockup_data()
    if reset:
        for table in (
            EvidenceCitation,
            Evidence,
            AgentSite,
            AssayKCC,
            ReferenceKCC,
            ReferenceTag,
            Agent,
            Assay,
            Reference,
            KCC,
        ):
            db.execute(delete(table))
        db.commit()

    for row in data["kccs"]:
        db.merge(
            KCC(
                id=row["id"],
                n=row["n"],
                title=row["title"],
                short=row["short"],
                description=row.get("desc") or row.get("description", ""),
                mechanism=row.get("mechanism", ""),
                icon=row["icon"],
                is_extended=bool(row.get("isNew")),
            )
        )

    for row in data["literature"]:
        db.merge(
            Reference(
                id=row["id"],
                year=row.get("year"),
                authors=row["authors"],
                title=row["title"],
                journal=row["journal"],
                vol=row.get("vol"),
                doi=None if row.get("doi") in (None, "—", "") else row.get("doi"),
                citations=row.get("cites"),
            )
        )
        if row.get("tag"):
            db.merge(ReferenceTag(reference_id=row["id"], tag=row["tag"]))
        kccs_field = row.get("kccs")
        if isinstance(kccs_field, list):
            for kid in kccs_field:
                db.merge(ReferenceKCC(reference_id=row["id"], kcc_id=kid))

    for row in data["assays"]:
        db.merge(
            Assay(
                id=row["id"],
                name=row["name"],
                type=row["type"],
                target=row["target"],
                throughput=row["throughput"],
                oecd_tg=row.get("oecd"),
                notes=row.get("notes"),
            )
        )
        for kid in row.get("kccs", []):
            db.merge(AssayKCC(assay_id=row["id"], kcc_id=kid))

    foundational = next((r["id"] for r in data["literature"] if r["id"] == "smith2016"), None)

    for row in data["carcinogens"]:
        db.merge(
            Agent(
                id=row["id"],
                name=row["name"],
                cas=_normalize_cas(row.get("cas")),
                iarc_group=_normalize_group(row.get("group")),
                agent_type=row["type"],
                summary=row["summary"],
                last_review=datetime.now(UTC),
            )
        )
        for site in row.get("sites", []):
            db.merge(AgentSite(agent_id=row["id"], site=site))

        evidence_map = row.get("evidence", {})
        for kcc_id, score in evidence_map.items():
            ev = Evidence(
                agent_id=row["id"],
                kcc_id=kcc_id,
                score=int(score),
                n_refs=1 if int(score) > 0 and foundational else 0,
            )
            db.add(ev)
            db.flush()
            if int(score) > 0 and foundational:
                db.merge(EvidenceCitation(evidence_id=ev.id, reference_id=foundational))

    db.merge(DatasetRelease(tag="0.1.0-seed", notes="Initial seed from mockup data.js"))
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed hKCC database")
    parser.add_argument("--reset", action="store_true", help="Clear tables before seeding")
    parser.add_argument(
        "--framework-only",
        action="store_true",
        help="Deprecated no-op; framework-only seeding is now the default.",
    )
    parser.add_argument(
        "--legacy-demo",
        action="store_true",
        help="Load legacy data.js demo rows. Not used by the production/reference-backed build.",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.legacy_demo:
            seed_session(db, reset=args.reset)
        else:
            seed_framework_session(db, reset=args.reset)
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
