"""Backfill the ``annotation_references`` bridge from ``references_update.xlsx``.

The workbook is the authoritative transform output (de-welding + dedup +
crossref/pubmed enrichment all done upstream by the curator). This script:

1. Folds ``enriched_references`` metadata into the existing ``references`` table,
   keeping ``references.id`` as the PK (decision: no parallel key scheme). Each
   workbook ``ref_id`` (R00001…) is resolved to an existing reference via its
   DOI/PMID (``reference_identifiers``); unresolved ones are created with the
   ``ref_id`` as their ``references.id`` and ``source='enriched'``. The workbook
   ``ref_id`` is recorded as a ``reference_identifiers`` row
   (``id_type='kcad_refkey'``) so the cross-walk is queryable.

2. Populates ``annotation_references`` — one row per (annotation, cited work),
   ordered by ``position``. DOI/PMID positions resolve through the folded map;
   citation-only positions are **best-effort** resolved on (surname, year) via
   :func:`db.references.resolve_reference` and left unlinked when no confident
   match exists.

3. Mirrors each annotation's position-1 reference onto the denormalized
   ``assay_annotations.reference_id`` (back-compat for current readers).

Idempotent: rebuilds ``annotation_references`` from scratch each run. Enrichment
is additive (fills placeholder fields only). Point at any DB via ``DATABASE_URL``;
run on a copy first to review the report before touching the live DB.

    DATABASE_URL=sqlite:///hkcc_copy.db python -m pipelines.backfill_annotation_refs
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select, update

from db.models import (
    AnnotationReference,
    AssayAnnotation,
    Reference,
    ReferenceIdentifier,
    ReferenceTag,
)
from db.references import normalize_doi, normalize_pmid, resolve_reference
from db.session import SessionLocal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = PROJECT_ROOT / "references_update.xlsx"

ENRICHED_SOURCE = "enriched"
ENRICHED_TAG = "enriched"
REFKEY_ID_TYPE = "kcad_refkey"
_PLACEHOLDER = {None, "", "—", "-NA-", "nan", "NaN"}


def _s(value: object) -> str | None:
    """Coerce a cell to a clean string or None (drops NaN / placeholders)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return None if s in _PLACEHOLDER else s


def _year(value: object) -> int | None:
    s = _s(value)
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _is_placeholder(value: str | None) -> bool:
    return value is None or value.strip() in _PLACEHOLDER


def _add_identifier(
    db, claimed: dict[tuple[str, str], str], reference_id: str,
    id_type: str, id_value: str | None, *, is_canonical: bool = False,
) -> None:
    """Insert a (id_type, id_value) → reference_id row, honouring global uniqueness."""
    if not id_value:
        return
    key = (id_type, id_value)
    owner = claimed.get(key)
    if owner is not None:
        return  # already claimed (by this or another ref) — never duplicate
    db.add(
        ReferenceIdentifier(
            reference_id=reference_id,
            id_type=id_type,
            id_value=id_value,
            is_canonical=is_canonical,
        )
    )
    claimed[key] = reference_id


def _enrich(ref: Reference, row: pd.Series) -> bool:
    """Fill placeholder bibliographic fields from an enriched_references row."""
    touched = False
    mapping = {
        "title": _s(row.get("title")),
        "authors": _s(row.get("authors")),
        "journal": _s(row.get("journal")),
        "vol": _s(row.get("vol")),
        "pages": _s(row.get("pages")),
        "url": _s(row.get("link")),
    }
    for attr, val in mapping.items():
        if val and _is_placeholder(getattr(ref, attr, None)):
            setattr(ref, attr, val)
            touched = True
    yr = _year(row.get("year"))
    if yr and ref.year is None:
        ref.year = yr
        touched = True
    return touched


def fold_enriched(db, enr: pd.DataFrame, claimed: dict) -> tuple[dict[str, str], dict]:
    """Resolve each workbook ref_id to a references.id; enrich/create as needed."""
    refkey_to_refid: dict[str, str] = {}
    stats = {"resolved_existing": 0, "created_new": 0, "enriched": 0}
    for _, row in enr.iterrows():
        ref_id = _s(row.get("ref_id"))
        if not ref_id:
            continue
        doi = normalize_doi(_s(row.get("doi")))
        pmid = normalize_pmid(_s(row.get("pmid")))
        res = resolve_reference(db, doi=doi, pmid=pmid)

        if res.reference_id:
            target = res.reference_id
            ref = db.get(Reference, target)
            if ref is not None and _enrich(ref, row):
                stats["enriched"] += 1
            stats["resolved_existing"] += 1
        else:
            target = ref_id
            ref = db.get(Reference, target)
            if ref is None:
                ref = Reference(
                    id=target,
                    year=_year(row.get("year")),
                    authors=_s(row.get("authors")) or "—",
                    title=_s(row.get("title")) or "—",
                    journal=_s(row.get("journal")) or "—",
                    vol=_s(row.get("vol")),
                    pages=_s(row.get("pages")),
                    doi=doi,
                    pmid=pmid,
                    url=_s(row.get("link")),
                    source=ENRICHED_SOURCE,
                )
                db.add(ref)
                db.flush()
                db.add(ReferenceTag(reference_id=target, tag=ENRICHED_TAG))
                _add_identifier(db, claimed, target, "doi", doi, is_canonical=True)
                _add_identifier(db, claimed, target, "pmid", pmid, is_canonical=doi is None)
                stats["created_new"] += 1
            else:
                if _enrich(ref, row):
                    stats["enriched"] += 1

        refkey_to_refid[ref_id] = target
        _add_identifier(db, claimed, target, REFKEY_ID_TYPE, ref_id.lower())

    db.flush()
    return refkey_to_refid, stats


def build_bridge(
    db, doi_df, pmid_df, cite_df, refkey_to_refid: dict[str, str]
) -> dict:
    """Rebuild annotation_references; mirror position-1 onto reference_id."""
    doi_map: dict[tuple[int, int], str] = {}
    pmid_map: dict[tuple[int, int], str] = {}
    cite_map: dict[tuple[int, int], tuple[str | None, int | None]] = {}

    for _, r in doi_df.iterrows():
        rk = _s(r.get("ref_id"))
        if rk:
            doi_map[(int(r["id"]), int(r["position"]))] = rk
    for _, r in pmid_df.iterrows():
        rk = _s(r.get("ref_id"))
        if rk:
            pmid_map[(int(r["id"]), int(r["position"]))] = rk
    for _, r in cite_df.iterrows():
        cite_map[(int(r["id"]), int(r["position"]))] = (
            _s(r.get("author")),
            _year(r.get("year")),
        )

    keys = set(doi_map) | set(pmid_map) | set(cite_map)
    by_ann: dict[int, dict[int, tuple[str, str]]] = defaultdict(dict)
    fuzzy_cache: dict[tuple[str | None, int | None], str | None] = {}
    stats = {
        "via_doi": 0, "via_pmid": 0, "via_citation": 0,
        "citation_unresolved": 0, "positions_total": len(keys),
    }

    for aid, pos in sorted(keys):
        if (aid, pos) in doi_map:
            rid = refkey_to_refid.get(doi_map[(aid, pos)])
            id_type = "doi"
            stats["via_doi"] += 1
        elif (aid, pos) in pmid_map:
            rid = refkey_to_refid.get(pmid_map[(aid, pos)])
            id_type = "pmid"
            stats["via_pmid"] += 1
        else:
            author, year = cite_map[(aid, pos)]
            ck = (author, year)
            if ck not in fuzzy_cache:
                fuzzy_cache[ck] = resolve_reference(
                    db, author=author, year=year
                ).reference_id
            rid = fuzzy_cache[ck]
            id_type = "citation"
            if rid:
                stats["via_citation"] += 1
            else:
                stats["citation_unresolved"] += 1
                continue
        if rid is None:
            continue
        by_ann[aid][pos] = (rid, id_type)

    db.execute(delete(AnnotationReference))
    rows = [
        {"annotation_id": aid, "position": pos, "reference_id": rid, "id_type": t}
        for aid, posmap in by_ann.items()
        for pos, (rid, t) in posmap.items()
    ]
    if rows:
        db.execute(AnnotationReference.__table__.insert(), rows)

    for aid, posmap in by_ann.items():
        primary = posmap.get(1) or posmap[min(posmap)]
        db.execute(
            update(AssayAnnotation)
            .where(AssayAnnotation.id == aid)
            .values(reference_id=primary[0])
        )

    stats["bridge_rows"] = len(rows)
    stats["annotations_linked"] = len(by_ann)
    return stats


def run(workbook: Path, *, dry_run: bool) -> dict:
    xl = pd.ExcelFile(workbook)
    enr = xl.parse("enriched_references")
    doi_df = xl.parse("Ref_DOI")
    pmid_df = xl.parse("Ref_PMID")
    cite_df = xl.parse("Ref_CITE")

    db = SessionLocal()
    try:
        claimed = {
            (t, v): rid
            for (t, v, rid) in db.execute(
                select(
                    ReferenceIdentifier.id_type,
                    ReferenceIdentifier.id_value,
                    ReferenceIdentifier.reference_id,
                )
            )
        }
        refkey_to_refid, fold_stats = fold_enriched(db, enr, claimed)
        bridge_stats = build_bridge(db, doi_df, pmid_df, cite_df, refkey_to_refid)
        report = {"fold": fold_stats, "bridge": bridge_stats}
        if dry_run:
            db.rollback()
            report["committed"] = False
        else:
            db.commit()
            report["committed"] = True
        return report
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    ap.add_argument("--dry-run", action="store_true", help="compute + report, no commit")
    args = ap.parse_args()
    report = run(args.workbook, dry_run=args.dry_run)
    import json

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
