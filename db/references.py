"""Reference identity: normalization, citation parsing, and deterministic linking.

This is the single place anything that needs to *link* to a reference should go,
instead of parsing the flat ``references.doi`` / ``references.pmid`` columns ad hoc.

Why it exists
-------------
KCAD source rows sometimes packed several space-separated DOIs into one cell, and
the human "citation" field is a free-text ``"Author year"`` label (e.g.
``"Bridges et al. 1981"``) that a naive ``str.split()`` mangles. The robust model
is: one external identifier == one row in ``reference_identifiers``; resolution
goes through identifiers first and only falls back to a fuzzy
``(surname, year)`` match — never the reverse.

Resolution order (strongest → weakest):
    1. DOI   (exact, after normalization)
    2. PMID  (exact, after normalization)
    3. fuzzy (first-author surname + year, then title similarity tie-break)

Below the fuzzy confidence threshold, ``resolve_reference`` returns ``None`` so the
caller can flag the citation for manual review rather than mislink it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Reference, ReferenceIdentifier

# ─── normalization ──────────────────────────────────────────────────────────

_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
    "doi.org/",
)

# A DOI is "10." followed by a registrant code and a suffix. Used to pull valid
# DOIs out of a blob and to validate a single token.
_DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)
_PMID_RE = re.compile(r"\d{1,9}")
# Trailing 4-digit year (optionally suffixed "a"/"b"), the anchor for citation parsing.
_YEAR_RE = re.compile(r"\b((?:18|19|20)\d{2})([a-z])?\b")


def normalize_doi(value: str | None) -> str | None:
    """Lowercase, strip URL/``doi:`` prefixes and trailing punctuation.

    Returns ``None`` if no DOI-shaped token is present.
    """
    if not value:
        return None
    s = value.strip()
    low = s.lower()
    for p in _DOI_PREFIXES:
        if low.startswith(p):
            s = s[len(p):]
            break
    s = s.strip().rstrip(".,;)")
    m = _DOI_RE.search(s)
    if not m:
        return None
    return m.group(0).lower().rstrip(".,;)")


def normalize_pmid(value: str | None) -> str | None:
    """Reduce to a digits-only PMID (drops ``PMID:`` prefixes, leading zeros)."""
    if not value:
        return None
    m = _PMID_RE.search(value.strip())
    if not m:
        return None
    pmid = m.group(0).lstrip("0") or "0"
    return pmid


def split_identifiers(value: str | None) -> list[str]:
    """Split a possibly multi-valued identifier cell on whitespace.

    ``"10.1016/x 10.1021/y"`` → ``["10.1016/x", "10.1021/y"]``. Single values and
    empty/None pass through cleanly.
    """
    if not value:
        return []
    return [tok for tok in value.split() if tok]


def normalized_dois(value: str | None) -> list[str]:
    """All distinct normalized DOIs in a (possibly multi-valued) cell, order-preserving."""
    out: list[str] = []
    for tok in split_identifiers(value):
        d = normalize_doi(tok)
        if d and d not in out:
            out.append(d)
    return out


def normalized_pmids(value: str | None) -> list[str]:
    out: list[str] = []
    for tok in split_identifiers(value):
        p = normalize_pmid(tok)
        if p and p not in out:
            out.append(p)
    return out


# ─── citation parsing ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ParsedCitation:
    surname: str | None
    year: int | None
    raw: str


def _ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def parse_citation(citation: str | None) -> ParsedCitation:
    """Best-effort ``"Author year"`` → ``(surname, year)``.

    Anchors on the **last** 4-digit year token (so ``"Smith MT et al. 2016"`` works),
    taking the first capitalized word before it as the author surname. This is a
    *hint* for fuzzy resolution only — never an identity. Strings holding several
    concatenated citations (``"Ames 1973  Bridges et al. 1981"``) parse to whichever
    citation the last year belongs to and should be treated as low-confidence; such
    rows are exactly the ones flagged ``needs_split`` upstream.
    """
    if not citation:
        return ParsedCitation(None, None, "")
    raw = citation.strip()
    matches = list(_YEAR_RE.finditer(raw))
    if not matches:
        head = _ascii_fold(raw).strip(" ,;.")
        surname = head.split()[0] if head.split() else None
        return ParsedCitation(surname, None, raw)
    m = matches[-1]
    year = int(m.group(1))
    before = _ascii_fold(raw[: m.start()]).strip(" ,;.")
    words = [w for w in re.split(r"[\s,]+", before) if w]
    surname = words[0].lower() if words else None
    return ParsedCitation(surname, year, raw)


# ─── resolution ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ResolveResult:
    reference_id: str | None
    method: str  # "doi" | "pmid" | "fuzzy" | "none"
    confidence: float  # 1.0 for exact id hits; [0,1) for fuzzy


def _by_identifier(session: Session, id_type: str, id_value: str) -> str | None:
    stmt = select(ReferenceIdentifier.reference_id).where(
        ReferenceIdentifier.id_type == id_type,
        ReferenceIdentifier.id_value == id_value,
    )
    return session.scalars(stmt).first()


def resolve_reference(
    session: Session,
    *,
    doi: str | None = None,
    pmid: str | None = None,
    citation: str | None = None,
    author: str | None = None,
    year: int | None = None,
    fuzzy_threshold: float = 0.82,
) -> ResolveResult:
    """Resolve an inbound citation to a single ``Reference.id``.

    Pass any subset of ``doi`` / ``pmid`` / ``citation`` (free text) / explicit
    ``author`` + ``year``. Exact identifier hits win and report confidence ``1.0``.
    The fuzzy fallback requires a matching ``(surname, year)`` and uses title
    similarity only to break ties; below ``fuzzy_threshold`` it returns
    ``reference_id=None`` (method ``"none"``) so the caller can queue manual review.
    """
    for d in normalized_dois(doi):
        rid = _by_identifier(session, "doi", d)
        if rid:
            return ResolveResult(rid, "doi", 1.0)

    for p in normalized_pmids(pmid):
        rid = _by_identifier(session, "pmid", p)
        if rid:
            return ResolveResult(rid, "pmid", 1.0)

    # Fuzzy fallback on (surname, year).
    surname = author.split()[0].lower() if author else None
    if citation and (surname is None or year is None):
        parsed = parse_citation(citation)
        surname = surname or parsed.surname
        year = year or parsed.year
    if not (surname and year):
        return ResolveResult(None, "none", 0.0)

    candidates = session.scalars(
        select(Reference).where(Reference.year == year)
    ).all()
    best_id: str | None = None
    best_score = 0.0
    for ref in candidates:
        hay = _ascii_fold(f"{ref.authors} {ref.title}").lower()
        if surname not in hay:
            continue
        score = SequenceMatcher(None, surname, hay[: len(surname) + 4]).ratio()
        # Reward an exact surname-at-start match; title only breaks ties.
        score = max(score, 0.85 if hay.startswith(surname) else score)
        if score > best_score:
            best_score, best_id = score, ref.id

    if best_id and best_score >= fuzzy_threshold:
        return ResolveResult(best_id, "fuzzy", round(best_score, 3))
    return ResolveResult(None, "none", round(best_score, 3))
