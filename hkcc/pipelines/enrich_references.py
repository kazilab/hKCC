"""Fetch real bibliographic metadata for references from their DOI / PMID.

Many KCAD rows arrived with placeholder ``authors``/``title`` (the in-text citation
key, e.g. ``"Hwa Yun 2017"``, with both fields identical). This backfills verified
metadata from the canonical registries:

- **DOI**  → Crossref (``api.crossref.org/works/{doi}``)
- **PMID** → NCBI E-utilities (``esummary``)

It reads the canonical identifier from ``reference_identifiers`` (falling back to
the flat ``doi``/``pmid`` columns), so run ``normalize_references`` first. Only rows
that still look like placeholders are touched unless ``--all`` is given; a field is
overwritten only when the fetched value is non-empty. Idempotent and rate-limited.

Usage::

    python -m pipelines.enrich_references                 # dry-run, placeholders only
    python -m pipelines.enrich_references --apply
    python -m pipelines.enrich_references --apply --all --limit 50
    python -m pipelines.enrich_references --apply --mailto you@lab.org
"""

from __future__ import annotations

import argparse
import time
from typing import Any

import httpx
from sqlalchemy import select

from hkcc.db.config import APP_CONTACT_EMAIL, APP_VERSION
from hkcc.db.models import Reference, ReferenceIdentifier
from hkcc.db.references import normalized_dois, normalized_pmids
from hkcc.db.session import SessionLocal

CROSSREF_BASE = "https://api.crossref.org/works"
EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


# ─── fetchers ────────────────────────────────────────────────────────────────


def _format_crossref_authors(authors: list[dict[str, Any]]) -> str:
    parts = []
    for a in authors:
        family = (a.get("family") or "").strip()
        given = (a.get("given") or "").strip()
        if family and given:
            initials = "".join(w[0] for w in given.replace(".", " ").split() if w)
            parts.append(f"{family} {initials}".strip())
        elif family:
            parts.append(family)
        elif a.get("name"):
            parts.append(a["name"].strip())
    return ", ".join(parts)


def fetch_crossref(client: httpx.Client, doi: str) -> dict[str, Any] | None:
    try:
        r = client.get(f"{CROSSREF_BASE}/{doi}")
        if r.status_code != 200:
            return None
        msg = r.json().get("message", {})
    except (httpx.HTTPError, ValueError):
        return None
    issued = (msg.get("issued") or {}).get("date-parts") or [[]]
    year = issued[0][0] if issued and issued[0] else None
    title = (msg.get("title") or [None])[0]
    journal = (msg.get("container-title") or [None])[0]
    return {
        "authors": _format_crossref_authors(msg.get("author") or []) or None,
        "title": title,
        "year": year,
        "journal": journal,
        "vol": msg.get("volume"),
        "citations": msg.get("is-referenced-by-count"),
    }


def fetch_pubmed(client: httpx.Client, pmid: str) -> dict[str, Any] | None:
    try:
        r = client.get(
            EUTILS_BASE,
            params={"db": "pubmed", "id": pmid, "retmode": "json"},
        )
        if r.status_code != 200:
            return None
        doc = r.json().get("result", {}).get(pmid)
    except (httpx.HTTPError, ValueError):
        return None
    if not doc:
        return None
    authors = ", ".join(a.get("name", "") for a in doc.get("authors", []) if a.get("name"))
    pubdate = (doc.get("pubdate") or "").split(" ")[0]
    year = int(pubdate) if pubdate.isdigit() else None
    return {
        "authors": authors or None,
        "title": doc.get("title") or None,
        "year": year,
        "journal": doc.get("fulljournalname") or doc.get("source") or None,
        "vol": doc.get("volume") or None,
        "citations": None,
    }


# ─── selection / update ────────────────────────────────────────────────────────


def _is_placeholder(ref: Reference) -> bool:
    """Heuristic: the citation-key signature, where authors == title (KCAD imports)."""
    a = (ref.authors or "").strip()
    t = (ref.title or "").strip()
    return a == t or not a or not t


def _canonical_ids(session, ref: Reference) -> tuple[str | None, str | None]:
    """(doi, pmid) for a reference, preferring reference_identifiers."""
    rows = session.execute(
        select(ReferenceIdentifier.id_type, ReferenceIdentifier.id_value)
        .where(ReferenceIdentifier.reference_id == ref.id)
        .order_by(ReferenceIdentifier.is_canonical.desc())
    ).all()
    doi = next((v for t, v in rows if t == "doi"), None)
    pmid = next((v for t, v in rows if t == "pmid"), None)
    doi = doi or (normalized_dois(ref.doi)[0] if normalized_dois(ref.doi) else None)
    pmid = pmid or (normalized_pmids(ref.pmid)[0] if normalized_pmids(ref.pmid) else None)
    return doi, pmid


def _apply_meta(ref: Reference, meta: dict[str, Any]) -> list[str]:
    """Fill empty/placeholder fields from fetched metadata; return changed field names."""
    changed = []
    placeholder = _is_placeholder(ref)
    for fieldname in ("authors", "title", "journal", "vol", "year", "citations"):
        new = meta.get(fieldname)
        if new in (None, ""):
            continue
        cur = getattr(ref, fieldname)
        # Always fill blanks; overwrite authors/title only if they were placeholders.
        if cur in (None, "") or (fieldname in ("authors", "title") and placeholder) or (
            fieldname in ("year", "vol", "journal", "citations") and not cur
        ):
            if cur != new:
                setattr(ref, fieldname, new)
                changed.append(fieldname)
    return changed


def enrich(
    session,
    *,
    apply: bool,
    only_placeholders: bool,
    limit: int | None,
    mailto: str,
    delay: float,
) -> None:
    headers = {"User-Agent": f"hKCC/{APP_VERSION} (mailto:{mailto})"}
    refs = session.scalars(select(Reference)).all()
    targets = [r for r in refs if not only_placeholders or _is_placeholder(r)]
    if limit:
        targets = targets[:limit]

    print(f"candidates: {len(targets)} reference(s)  |  {'APPLY' if apply else 'DRY-RUN'}")
    updated = skipped = failed = 0

    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        for ref in targets:
            doi, pmid = _canonical_ids(session, ref)
            meta = None
            if doi:
                meta = fetch_crossref(client, doi)
                time.sleep(delay)
            if not meta and pmid:
                meta = fetch_pubmed(client, pmid)
                time.sleep(delay)
            if not meta:
                failed += 1
                continue
            changed = _apply_meta(ref, meta)
            if changed:
                updated += 1
                print(f"  ~ {ref.id}: {', '.join(changed)}")
            else:
                skipped += 1

    if apply:
        session.commit()
    print(f"\nupdated: {updated}   unchanged: {skipped}   no-metadata: {failed}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default dry-run).")
    parser.add_argument(
        "--all",
        dest="all_rows",
        action="store_true",
        help="Enrich every reference, not just placeholder rows.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Cap rows processed.")
    parser.add_argument(
        "--mailto",
        default=APP_CONTACT_EMAIL,
        help="Contact email for the Crossref polite pool / NCBI.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="Seconds between API calls (NCBI allows ~3/s).",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        enrich(
            session,
            apply=args.apply,
            only_placeholders=not args.all_rows,
            limit=args.limit,
            mailto=args.mailto,
            delay=args.delay,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
