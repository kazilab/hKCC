"""Backfill ``reference_identifiers`` and auto-split conflated reference rows.

Operates on an existing database. Two jobs, both idempotent:

1. **Backfill identifiers.** For every reference, split the flat ``doi`` / ``pmid``
   cells on whitespace, normalize each token, and write one
   ``reference_identifiers`` row per distinct identifier. The first DOI (else the
   first PMID) is marked ``is_canonical``.

2. **Auto-split conflated rows.** A row carrying *more than one DOI* welded several
   distinct papers into one record (the ``authors``/``title`` fields confirm it).
   The canonical (first) DOI + any PMIDs stay on the original; every *additional*
   DOI is moved to a freshly created child reference (deterministic id, so re-runs
   are safe). The original is flagged ``needs_split=1`` because its inbound links
   (``agent_references`` / ``evidence_citations`` / ``reference_kccs``) may belong
   to any of the split papers — that reassignment is left to a curator, by design.

Inbound links are **never** moved automatically; this is the "flag" half of the
"auto-split + flag" strategy.

Usage::

    python -m pipelines.normalize_references            # dry-run report
    python -m pipelines.normalize_references --apply     # write changes
"""

from __future__ import annotations

import argparse
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import func, select

from hkcc.db.models import (
    AgentReference,
    EvidenceCitation,
    Reference,
    ReferenceIdentifier,
    ReferenceKCC,
)
from hkcc.db.references import normalized_dois, normalized_pmids
from hkcc.db.session import SessionLocal


def _slugify(s: str, maxlen: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen] or "unknown"


def _short_hash(s: str, n: int = 6) -> str:
    return hashlib.blake2b(s.encode("utf-8"), digest_size=4).hexdigest()[:n]


def child_reference_id(doi: str) -> str:
    """Deterministic id for a child reference carved off a conflated row."""
    return f"split-doi-{_slugify(doi)}-{_short_hash(doi)}"


@dataclass
class Report:
    refs_seen: int = 0
    identifiers_created: int = 0
    identifiers_skipped: int = 0
    conflated_refs: list[str] = field(default_factory=list)
    children_created: list[str] = field(default_factory=list)
    flagged_with_links: list[tuple[str, int]] = field(default_factory=list)

    def render(self, applied: bool) -> str:
        mode = "APPLIED" if applied else "DRY-RUN (no changes written)"
        lines = [
            f"=== normalize_references — {mode} ===",
            f"references scanned        : {self.refs_seen}",
            f"identifiers created       : {self.identifiers_created}",
            f"identifiers already present: {self.identifiers_skipped}",
            f"conflated rows (multi-DOI) : {len(self.conflated_refs)}",
            f"child references created   : {len(self.children_created)}",
        ]
        if self.flagged_with_links:
            lines.append("")
            lines.append("Conflated rows that carry inbound links (need curator review):")
            for rid, n in sorted(self.flagged_with_links, key=lambda x: -x[1]):
                lines.append(f"  [{n} links] {rid}")
        return "\n".join(lines)


def _existing_identifier_refs(session) -> set[tuple[str, str]]:
    return {
        (t, v)
        for t, v in session.execute(
            select(ReferenceIdentifier.id_type, ReferenceIdentifier.id_value)
        ).all()
    }


def _link_count(session, reference_id: str) -> int:
    n = 0
    for model in (AgentReference, EvidenceCitation, ReferenceKCC):
        n += session.scalar(
            select(func.count()).select_from(model).where(
                model.reference_id == reference_id
            )
        )
    return n


def normalize(session, *, apply: bool) -> Report:
    report = Report()
    taken = _existing_identifier_refs(session)
    existing_ref_ids = set(session.scalars(select(Reference.id)).all())

    def claim(reference_id: str, id_type: str, id_value: str, canonical: bool) -> None:
        key = (id_type, id_value)
        if key in taken:
            report.identifiers_skipped += 1
            return
        taken.add(key)
        report.identifiers_created += 1
        if apply:
            session.add(
                ReferenceIdentifier(
                    reference_id=reference_id,
                    id_type=id_type,
                    id_value=id_value,
                    is_canonical=canonical,
                )
            )

    for ref in session.scalars(select(Reference)).all():
        report.refs_seen += 1
        dois = normalized_dois(ref.doi)
        pmids = normalized_pmids(ref.pmid)

        # Identifiers for the original row: canonical DOI (or canonical PMID) + PMIDs.
        canonical_doi = dois[0] if dois else None
        for i, d in enumerate(dois[:1]):  # only the first DOI stays on the original
            claim(ref.id, "doi", d, canonical=True)
        for j, p in enumerate(pmids):
            claim(ref.id, "pmid", p, canonical=(canonical_doi is None and j == 0))

        if len(dois) <= 1:
            continue

        # ── conflated row: carve a child reference per extra DOI ──
        report.conflated_refs.append(ref.id)
        if apply and not ref.needs_split:
            ref.needs_split = True
            if ref.raw_citation is None:
                ref.raw_citation = ref.doi  # preserve the original multi-DOI blob

        links = _link_count(session, ref.id)
        if links:
            report.flagged_with_links.append((ref.id, links))

        for d in dois[1:]:
            cid = child_reference_id(d)
            claim(cid, "doi", d, canonical=True)
            if cid in existing_ref_ids:
                continue
            existing_ref_ids.add(cid)
            report.children_created.append(cid)
            if apply:
                session.add(
                    Reference(
                        id=cid,
                        year=ref.year,
                        authors=ref.authors,
                        title=ref.title,
                        journal=ref.journal,
                        vol=ref.vol,
                        doi=d,
                        pmid=None,
                        source=ref.source,
                        needs_split=False,
                        raw_citation=ref.raw_citation or ref.doi,
                    )
                )

    if apply:
        session.commit()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without it, runs a dry-run report only.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        report = normalize(session, apply=args.apply)
    print(report.render(applied=args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
