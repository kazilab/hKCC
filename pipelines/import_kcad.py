"""Import the KCAD supplementary export (`suppl_data/`) into hKCC.

KCAD = Key Characteristics Assay Database, Rigutto et al. 2025. Two CSVs:

- ``pivot_table.csv``    one row per Method × KC1..KC10 presence (+ / empty)
- ``filtered_table.csv`` one row per study annotation (assay × KC × chem × PMID)

Unlike the earlier ``references/data/claude_2/kcad_import.py`` prototype, the
files in ``suppl_data/`` are already clean: the pivot has 11 columns
(``Method, KC1..KC10``) with no offset, and ``filtered_table`` has 30 aligned
columns. No header patching or column-shift mapping is needed.

Scope:
- KC1..KC10 only. Extended hKCC KCs (kcc-11..kcc-14) get no rows from this source.
- Writes ``assays``, ``assay_kccs``, ``references``, ``reference_tags`` (tag=``kcad``),
  ``assay_annotations``, and ``agent_references`` (via the hand-curated
  ``db/seed/kcad/monograph_chem_map.json``).
- Does **not** touch ``evidence`` — KCAD has no 0–4 scores. Curators stay in charge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from datetime import UTC, datetime

from db.models import (
    Agent,
    AgentReference,
    AgentSite,
    Assay,
    AssayAnnotation,
    AssayKCC,
    DatasetRelease,
    Evidence,
    EvidenceCitation,
    Reference,
    ReferenceKCC,
    ReferenceTag,
)
from db.session import SessionLocal

KCAD_SOURCE_TAG = "kcad"
KCAD_RELEASE_TAG = "0.2.0-kcad"
KCAD_REF_TAG = "kcad"
KC_RANGE = range(1, 11)

# Canonical reference id for the KCAD source publication:
#   Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT.
#   "Mapping assays to the key characteristics of carcinogens to support
#   decision-making." Database (Oxford) 2025, article baaf026.
# Every KCAD-derived row carries this id in `source_ref_id` so the data can
# always be traced back to the paper that produced it.
KCAD_PAPER_REF_ID = "kcad-paper-rigutto-2025"
KCAD_PAPER_DOI = "10.1093/database/baaf026"
KCAD_PAPER_URL = f"https://doi.org/{KCAD_PAPER_DOI}"

KCAD_SEED_DIR = Path(__file__).resolve().parents[1] / "db" / "seed" / "kcad"
DEFAULT_SUPPL_DIR = Path(__file__).resolve().parents[1].parent / "suppl_data"
DEFAULT_CHEM_MAP = KCAD_SEED_DIR / "monograph_chem_map.json"
DEFAULT_AGENTS_FILE = KCAD_SEED_DIR / "agents.json"
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "exports" / "kcad"


def kcad_paper_reference() -> dict:
    """Canonical Reference row for the KCAD publication (idempotent seed)."""
    return {
        "id": KCAD_PAPER_REF_ID,
        "year": 2025,
        "authors": "Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT",
        "title": (
            "Mapping assays to the key characteristics of carcinogens "
            "to support decision-making"
        ),
        "journal": "Database (Oxford)",
        "vol": "2025",
        "doi": KCAD_PAPER_DOI,
        "pmid": None,
        "citations": None,
        "source": "kcad-paper",
        "article_id": "baaf026",
        "url": KCAD_PAPER_URL,
    }

log = logging.getLogger("import_kcad")


# ─── helpers ──────────────────────────────────────────────────────────────────

_NA_VALUES = {"", "-NA-", "—", "-", "NA", "nan", "NaN", "N/A"}


def _clean(v: object) -> str | None:
    """Treat KCAD '-NA-' sentinels, empty strings and pandas NaN as None."""
    if v is None:
        return None
    if isinstance(v, float):
        # NaN check without importing math.
        return None if v != v else str(v)
    if not isinstance(v, str):
        return v  # type: ignore[return-value]
    s = v.strip()
    if s in _NA_VALUES:
        return None
    return s


def _slugify(s: str, *, maxlen: int = 72) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen] or "unknown"


def _categorise_throughput(name: str) -> str:
    n = name.lower()
    if any(
        t in n
        for t in (
            "high-throughput",
            "hts",
            "tox21",
            "toxcast",
            "rna-seq",
            "next-generation sequencing",
            "microarray",
            "chip-seq",
            "atac-seq",
            "whole-genome",
            "metabolomic",
            "proteomic",
            "single-cell",
        )
    ):
        return "high"
    if any(
        t in n
        for t in ("reporter", "elisa", "luciferase", "flow", "qpcr", "rt-pcr", "western", "fluorescence")
    ):
        return "medium"
    return "low"


def _assay_type(formats: Iterable[str | None], targets: Iterable[str | None]) -> str:
    fmt_blob = " ".join((f or "").lower() for f in formats)
    tgt_blob = " ".join((t or "").lower() for t in targets)
    if "in silico" in fmt_blob or "in silico" in tgt_blob:
        return "in silico"
    if "in vivo" in fmt_blob:
        return "in vivo"
    if "ex vivo" in fmt_blob:
        return "ex vivo"
    if any(k in fmt_blob for k in ("in vitro",)) or any(
        k in tgt_blob for k in ("cell line", "primary", "cell-free")
    ):
        return "in vitro"
    return "other"


_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_PMID_RE = re.compile(r"^\d{1,9}$")


def _parse_citation(citation: str | None) -> tuple[str, int | None]:
    """Best-effort split of "Author 1992" / "Smith MT et al. 2016" into (authors, year)."""
    if not citation:
        return "—", None
    m = _YEAR_RE.search(citation)
    year = int(m.group()) if m else None
    if m:
        authors = (citation[: m.start()] + citation[m.end() :]).strip(" ,;")
    else:
        authors = citation.strip()
    return authors or "—", year


def _short_hash(s: str, n: int = 6) -> str:
    return hashlib.blake2b(s.encode("utf-8"), digest_size=n // 2 + 1).hexdigest()[:n]


def _ref_id(*, doi: str | None, pmid: str | None, citation: str | None) -> str | None:
    """Stable, collision-resistant Reference.id from the best identifier available.

    Slug-truncation at 80 chars + an always-appended 6-char hash of the full
    identifier guarantees uniqueness even when two distinct citations share a
    common prefix (e.g. "Smith 1992" rows from different journals).
    """
    if doi:
        return f"kcad-doi-{_slugify(doi, maxlen=80)}-{_short_hash(doi)}"
    if pmid:
        return f"kcad-pmid-{pmid}"
    if citation:
        return f"kcad-{_slugify(citation, maxlen=80)}-{_short_hash(citation)}"
    return None


# ─── load ─────────────────────────────────────────────────────────────────────


def load_pivot(path: Path) -> pd.DataFrame:
    """549 rows × 11 cols: Method, KC1..KC10 (clean headers, no offset)."""
    df = pd.read_csv(path)
    expected = {"Method", *(f"KC{k}" for k in KC_RANGE)}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"pivot_table.csv missing expected columns: {sorted(missing)}")
    df = df[df["Method"].notna()].copy()
    df["Method"] = df["Method"].map(_clean)
    df = df[df["Method"].notna()].reset_index(drop=True)
    for k in KC_RANGE:
        col = f"KC{k}"
        df[col] = df[col].map(lambda v: bool(_clean(v)) and _clean(v).strip() == "+")
    return df


def load_filtered(path: Path) -> pd.DataFrame:
    """~20k rows × 30 cols. Read natively — no HEADER_FIX needed."""
    df = pd.read_csv(path, dtype=str, low_memory=False)
    for c in df.columns:
        df[c] = df[c].map(_clean)
    return df


def load_chem_map(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return dict(raw.get("map", {}))


def load_agent_seed(path: Path) -> list[dict]:
    """Load `agents.json` (rows that should be `db.merge`-d before linking)."""
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw.get("agents", []))


def seed_kcad_agents(db: Session, agents: list[dict]) -> int:
    """Idempotent insert/update of KCAD-derived Agent rows.

    Existing agents are *not* overwritten — the importer never claims authority
    over curator-curated names/sites/groups. We only fill in missing rows.

    All newly-seeded agents are anchored to ``KCAD_PAPER_REF_ID`` via
    ``Agent.source_ref_id``; existing agents keep their provenance untouched.
    """
    existing = {aid for (aid,) in db.execute(select(Agent.id)).all()}
    n_added = 0
    for row in agents:
        if row["id"] in existing:
            continue
        cas = row.get("cas")
        cas = None if cas in (None, "—", "-", "") else cas
        group = row.get("iarc_group")
        group = None if group in (None, "—", "-", "") else group
        eval_year = row.get("evaluation_year")
        try:
            eval_year_int = int(eval_year) if eval_year is not None else None
        except (TypeError, ValueError):
            eval_year_int = None
        db.add(
            Agent(
                id=row["id"],
                name=row["name"],
                cas=cas,
                iarc_group=group,
                agent_type=row.get("agent_type", "Industrial chemical"),
                summary=row.get("summary", ""),
                last_review=datetime.now(UTC),
                monograph_volume=row.get("monograph_volume"),
                monograph_pub_year=row.get("monograph_pub_year"),
                evaluation_year=eval_year_int,
                source_ref_id=KCAD_PAPER_REF_ID,
            )
        )
        sites = row.get("sites") or []
        for s in sites:
            db.add(AgentSite(agent_id=row["id"], site=s))
        n_added += 1
    if n_added:
        db.flush()
    return n_added


# ─── transform ────────────────────────────────────────────────────────────────


@dataclass
class KCADBundle:
    assays: list[dict] = field(default_factory=list)
    assay_kccs: list[dict] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)
    annotations: list[dict] = field(default_factory=list)
    agent_references: list[dict] = field(default_factory=list)
    report: dict = field(default_factory=dict)


def build_bundle(
    pivot: pd.DataFrame,
    filtered: pd.DataFrame,
    chem_map: dict[str, str],
) -> KCADBundle:
    bundle = KCADBundle()

    def _row_identifiers(row: pd.Series) -> tuple[str | None, str | None, str | None]:
        doi = _clean(row.get("DOI"))
        pmid = _clean(row.get("PMID"))
        if pmid and not _PMID_RE.fullmatch(pmid):
            pmid = None  # source occasionally puts a DOI in the PMID column
        cite = _clean(row.get("Citation"))
        return doi, pmid, cite

    # Build references first (so we know reference_id when emitting annotations).
    refs_by_key: dict[str, dict] = {}
    for _, row in filtered.iterrows():
        doi, pmid, cite = _row_identifiers(row)
        if not any((doi, pmid, cite)):
            continue
        key = doi or pmid or cite
        if key in refs_by_key:
            continue
        rid = _ref_id(doi=doi, pmid=pmid, citation=cite)
        if not rid:
            continue
        authors, year = _parse_citation(cite)
        refs_by_key[key] = {
            "id": rid,
            "year": year,
            "authors": authors,
            "title": cite or "—",
            "journal": "—",
            "vol": None,
            "doi": doi,
            "pmid": pmid,
            "citations": None,
            "source": KCAD_SOURCE_TAG,
        }
    bundle.references = list(refs_by_key.values())

    def _row_ref_id(row: pd.Series) -> str | None:
        doi, pmid, cite = _row_identifiers(row)
        return _ref_id(doi=doi, pmid=pmid, citation=cite)

    # Group filtered rows by Method for assay metadata aggregation.
    by_method: dict[str, list[pd.Series]] = defaultdict(list)
    for _, row in filtered.iterrows():
        m = row.get("Method") or row.get("Method2")
        if m:
            by_method[m].append(row)

    seen_ids: set[str] = set()
    assays_index: dict[str, str] = {}  # method_name → assay_id

    for _, prow in pivot.iterrows():
        name = prow["Method"].strip()
        slug = _slugify(name)
        aid = f"kcad-{slug}"
        n = 2
        while aid in seen_ids:
            aid = f"kcad-{slug}-{n}"
            n += 1
        seen_ids.add(aid)
        assays_index[name] = aid

        kc_hits = [k for k in KC_RANGE if prow[f"KC{k}"]]

        meta = by_method.get(name, [])
        formats = sorted({m for m in (_clean(r.get("Cell_format")) for r in meta) if m})
        targets = sorted({m for m in (_clean(r.get("Target_cell")) for r in meta) if m})
        organisms = sorted({m for m in (_clean(r.get("Organism")) for r in meta) if m})
        tissues = sorted({m for m in (_clean(r.get("Tissue")) for r in meta) if m})
        oecd_tgs = sorted({m for m in (_clean(r.get("OECD")) for r in meta) if m})

        target_endpoint: str | None = None
        for r in meta:
            for k in ("Assay_endpoint3", "Assay_endpoint2", "Assay_endpoint"):
                v = _clean(r.get(k))
                if v:
                    target_endpoint = v
                    break
            if target_endpoint:
                break

        # "category" vs "assay": single short word with no digits is a coarse label.
        granularity = (
            "category"
            if len(name) < 25 and not any(c.isdigit() for c in name) and " " not in name
            else "assay"
        )

        bundle.assays.append(
            {
                "id": aid,
                "name": name,
                "type": _assay_type(formats, targets),
                "target": (target_endpoint or "—")[:128],
                "throughput": _categorise_throughput(name),
                "oecd_tg": "; ".join(oecd_tgs)[:64] if oecd_tgs else None,
                "notes": (
                    f"Imported from KCAD (Rigutto et al. 2025). "
                    f"Mapped to KC{', KC'.join(str(k) for k in kc_hits) or '?'} "
                    f"across {len(meta)} study annotations from IARC Monographs Vols 107–128."
                ),
                "source": KCAD_SOURCE_TAG,
                "granularity": granularity,
                "source_ref_id": KCAD_PAPER_REF_ID,
                "_kc_hits": kc_hits,
                "_organisms": organisms,
                "_tissues": tissues,
            }
        )

        for k in kc_hits:
            bundle.assay_kccs.append({"assay_id": aid, "kcc_id": f"kcc-{k:02d}"})

    # Annotations: one row per filtered_table row that we can attach to an assay.
    annotation_count = 0
    for _, row in filtered.iterrows():
        name = row.get("Method") or row.get("Method2")
        if not name or name not in assays_index:
            continue
        kc_num = _clean(row.get("KC"))
        if not kc_num:
            continue
        try:
            kc_int = int(kc_num)
        except ValueError:
            continue
        if kc_int not in KC_RANGE:
            continue
        sec_kc_raw = _clean(row.get("Secondary KC"))
        sec_kcc_id: str | None = None
        if sec_kc_raw:
            m = re.search(r"\b([1-9]|10)\b", sec_kc_raw)
            if m:
                n2 = int(m.group(1))
                if n2 in KC_RANGE:
                    sec_kcc_id = f"kcc-{n2:02d}"

        chem = _clean(row.get("Monograph_chem"))
        agent_id = chem_map.get(chem) if chem else None

        bundle.annotations.append(
            {
                "assay_id": assays_index[name],
                "kcc_id": f"kcc-{kc_int:02d}",
                "secondary_kcc_id": sec_kcc_id,
                "secondary_kc_raw": sec_kc_raw,
                "reference_id": _row_ref_id(row),
                "agent_id": agent_id,
                # KC classification
                "kc_subgroup": _clean(row.get("KC_Subgroup")),
                "kc_subgroup2": _clean(row.get("KC_subgroup2")),
                "effect": _clean(row.get("Effect")),
                # Assay endpoints / method
                "assay_endpoint": _clean(row.get("Assay_endpoint")),
                "assay_endpoint2": _clean(row.get("Assay_endpoint2")),
                "assay_endpoint3": _clean(row.get("Assay_endpoint3")),
                "biomarker": _clean(row.get("Biomarker")),
                "method2": _clean(row.get("Method2")),
                "stimulant_activation_agent": _clean(row.get("Stimulant_activation_agent")),
                "target_cell": _clean(row.get("Target_cell")),
                # Biology
                "organism": _clean(row.get("Organism")),
                "species": _clean(row.get("Species")),
                "mammalian": _clean(row.get("Mammalian")),
                "tissue": _clean(row.get("Tissue")),
                "tissue2": _clean(row.get("Tissue2")),
                "cell_type": _clean(row.get("Cell_type")),
                "immortalized": _clean(row.get("Immortalized")),
                # Study design
                "cell_format": _clean(row.get("Cell_format")),
                "design": _clean(row.get("Design")),
                "design_transgenic": _clean(row.get("Design_transgenic")),
                # Provenance
                "monograph_num": _clean(row.get("Monograph_num")),
                "monograph_chem": chem,
                "oecd_tg": _clean(row.get("OECD")),
                "cebp_ref_idx": _clean(row.get("CEBP")),
                "source": KCAD_SOURCE_TAG,
                "source_ref_id": KCAD_PAPER_REF_ID,
            }
        )
        annotation_count += 1

    # Agent ↔ Reference links derived from filtered_table chem column.
    seen_agent_ref: set[tuple[str, str]] = set()
    for ann in bundle.annotations:
        agent_id = ann["agent_id"]
        ref_id = ann["reference_id"]
        if not agent_id or not ref_id:
            continue
        if (agent_id, ref_id) in seen_agent_ref:
            continue
        seen_agent_ref.add((agent_id, ref_id))
        bundle.agent_references.append(
            {"agent_id": agent_id, "reference_id": ref_id, "source": KCAD_SOURCE_TAG}
        )

    # Report.
    by_kc = defaultdict(int)
    for link in bundle.assay_kccs:
        by_kc[link["kcc_id"]] += 1
    bundle.report = {
        "n_assays": len(bundle.assays),
        "n_assay_kcc_links": len(bundle.assay_kccs),
        "n_references": len(bundle.references),
        "n_annotations": annotation_count,
        "n_agent_references": len(bundle.agent_references),
        "assays_per_kc": dict(sorted(by_kc.items())),
        "n_mapped_chems": sum(1 for ann in bundle.annotations if ann["agent_id"]),
        "n_unmapped_chems": sum(
            1
            for ann in bundle.annotations
            if ann["monograph_chem"] and not ann["agent_id"]
        ),
    }
    return bundle


# ─── load into DB ─────────────────────────────────────────────────────────────


def _upsert(db: Session, model, rows: list[dict], pk_cols: list[str]) -> None:
    """Portable upsert that works on Postgres and SQLite.

    Uses ON CONFLICT DO UPDATE on Postgres for speed, falls back to merge() on
    SQLite (used by tests).
    """
    if not rows:
        return
    dialect = db.bind.dialect.name if db.bind is not None else ""
    if dialect == "postgresql":
        # Drop synthetic underscore-prefixed fields (only used by JSON dumps).
        cleaned = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
        stmt = pg_insert(model.__table__).values(cleaned)
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in model.__table__.columns
            if c.name not in pk_cols
        }
        stmt = stmt.on_conflict_do_update(index_elements=pk_cols, set_=update_cols)
        db.execute(stmt)
    else:
        for r in rows:
            payload = {k: v for k, v in r.items() if not k.startswith("_")}
            db.merge(model(**payload))


def link_evidence_citations(db: Session) -> dict[str, int]:
    """Attach KCAD references to existing `evidence` rows via `evidence_citations`.

    Strictly **non-destructive**:
    - We never modify ``Evidence.score`` — curator-curated scores stay authoritative.
    - We never create new ``Evidence`` rows — only enrich citation links on rows
      that already exist.
    - We never remove existing ``EvidenceCitation`` rows — only insert missing ones.

    For each ``(agent_id, kcc_id, reference_id)`` triple in ``assay_annotations``
    where an ``Evidence`` row exists, an ``EvidenceCitation`` link is added (or
    left alone if already present). ``Evidence.n_refs`` is recomputed to reflect
    the current citation count.

    Returns counters: ``n_evidence_rows_touched``, ``n_citations_added``.
    """
    triples = db.execute(
        select(
            AssayAnnotation.agent_id,
            AssayAnnotation.kcc_id,
            AssayAnnotation.reference_id,
        ).where(
            AssayAnnotation.agent_id.is_not(None),
            AssayAnnotation.reference_id.is_not(None),
        )
    ).all()

    evidence_by_pair: dict[tuple[str, str], Evidence] = {
        (ev.agent_id, ev.kcc_id): ev for ev in db.scalars(select(Evidence)).all()
    }
    existing_citations: set[tuple[int, str]] = {
        (ec.evidence_id, ec.reference_id) for ec in db.scalars(select(EvidenceCitation)).all()
    }

    touched: set[int] = set()
    added = 0
    for agent_id, kcc_id, ref_id in triples:
        ev = evidence_by_pair.get((agent_id, kcc_id))
        if ev is None:
            continue
        key = (ev.id, ref_id)
        if key in existing_citations:
            touched.add(ev.id)
            continue
        db.add(EvidenceCitation(evidence_id=ev.id, reference_id=ref_id))
        existing_citations.add(key)
        touched.add(ev.id)
        added += 1

    if added:
        db.flush()

    # Refresh n_refs for every touched evidence row.
    for ev_id in touched:
        n = db.scalar(
            select(func.count())
            .select_from(EvidenceCitation)
            .where(EvidenceCitation.evidence_id == ev_id)
        )
        db.execute(Evidence.__table__.update().where(Evidence.id == ev_id).values(n_refs=n))

    return {"n_evidence_rows_touched": len(touched), "n_citations_added": added}


def reset_kcad_rows(db: Session) -> None:
    """Clear all `source='kcad'` rows so re-imports are idempotent.

    Cleared:
      - `assay_annotations` (source='kcad')
      - `agent_references` (source='kcad')
      - `evidence_citations` rows whose `reference_id` is KCAD-sourced
      - `assays` with source='kcad' + their `assay_kccs`
      - `references` with source='kcad' + their tags/kcc-links

    Recomputes `Evidence.n_refs` so curator scores stay self-consistent.
    Curator-authored `Evidence` rows are preserved.
    """
    db.execute(delete(AssayAnnotation).where(AssayAnnotation.source == KCAD_SOURCE_TAG))
    db.execute(delete(AgentReference).where(AgentReference.source == KCAD_SOURCE_TAG))

    kcad_ref_ids = [
        rid for (rid,) in db.execute(select(Reference.id).where(Reference.source == KCAD_SOURCE_TAG))
    ]
    # Evidence rows that had KCAD citations need their n_refs recomputed *after*
    # we drop those citations.
    affected_evidence_ids: set[int] = set()
    if kcad_ref_ids:
        affected_evidence_ids = {
            ev_id
            for (ev_id,) in db.execute(
                select(EvidenceCitation.evidence_id).where(
                    EvidenceCitation.reference_id.in_(kcad_ref_ids)
                )
            )
        }
        db.execute(
            delete(EvidenceCitation).where(EvidenceCitation.reference_id.in_(kcad_ref_ids))
        )

    kcad_assay_ids = [
        aid for (aid,) in db.execute(select(Assay.id).where(Assay.source == KCAD_SOURCE_TAG))
    ]
    if kcad_assay_ids:
        db.execute(delete(AssayKCC).where(AssayKCC.assay_id.in_(kcad_assay_ids)))
        db.execute(delete(Assay).where(Assay.id.in_(kcad_assay_ids)))
    if kcad_ref_ids:
        db.execute(delete(ReferenceKCC).where(ReferenceKCC.reference_id.in_(kcad_ref_ids)))
        db.execute(delete(ReferenceTag).where(ReferenceTag.reference_id.in_(kcad_ref_ids)))
        db.execute(delete(Reference).where(Reference.id.in_(kcad_ref_ids)))

    for ev_id in affected_evidence_ids:
        n = db.scalar(
            select(func.count())
            .select_from(EvidenceCitation)
            .where(EvidenceCitation.evidence_id == ev_id)
        )
        db.execute(Evidence.__table__.update().where(Evidence.id == ev_id).values(n_refs=n))

    db.commit()


def load_bundle(
    db: Session,
    bundle: KCADBundle,
    *,
    reset: bool = False,
    agent_seed: list[dict] | None = None,
) -> None:
    if reset:
        reset_kcad_rows(db)

    # 0a. Seed the KCAD source publication FIRST so every downstream FK
    #     (agents.source_ref_id, assays.source_ref_id, assay_annotations.source_ref_id)
    #     can resolve to a real row.
    _upsert(db, Reference, [kcad_paper_reference()], pk_cols=["id"])
    db.flush()

    # 0b. Seed any missing agents declared by db/seed/kcad/agents.json BEFORE
    #     linking references — the FK on agent_references requires the row.
    if agent_seed:
        n_new_agents = seed_kcad_agents(db, agent_seed)
        log.info("Seeded %d new agents from agents.json", n_new_agents)

    # 1. References (no FKs).
    _upsert(db, Reference, bundle.references, pk_cols=["id"])
    # Tag every imported ref with 'kcad'.
    ref_tags = [{"reference_id": r["id"], "tag": KCAD_REF_TAG} for r in bundle.references]
    _upsert(db, ReferenceTag, ref_tags, pk_cols=["reference_id", "tag"])
    db.flush()

    # 2. Assays.
    _upsert(db, Assay, bundle.assays, pk_cols=["id"])
    db.flush()

    # 3. AssayKCC junctions.
    _upsert(db, AssayKCC, bundle.assay_kccs, pk_cols=["assay_id", "kcc_id"])

    # 4. Agent ↔ Reference (only links agents that exist in DB).
    existing_agents = {aid for (aid,) in db.execute(select(Agent.id))}
    ar_rows = [r for r in bundle.agent_references if r["agent_id"] in existing_agents]
    _upsert(db, AgentReference, ar_rows, pk_cols=["agent_id", "reference_id"])

    # 5. Annotations (bulk insert — append-only).
    if bundle.annotations:
        # Drop agent_id if the agent doesn't exist (FK SET NULL fallback).
        clean_anns = []
        for a in bundle.annotations:
            if a["agent_id"] and a["agent_id"] not in existing_agents:
                a = {**a, "agent_id": None}
            clean_anns.append(a)
        db.execute(AssayAnnotation.__table__.insert(), clean_anns)

    # 6. Cell-level evidence ↔ KCAD reference linkage. Strictly non-destructive:
    #    only inserts citation rows on existing (agent_id, kcc_id) Evidence cells,
    #    never modifies scores. See `link_evidence_citations` for the contract.
    citation_stats = link_evidence_citations(db)
    bundle.report.update(citation_stats)
    log.info("Evidence-citation linkage: %s", citation_stats)

    # 7. Dataset release marker.
    db.merge(
        DatasetRelease(
            tag=KCAD_RELEASE_TAG,
            notes=(
                f"KCAD import from suppl_data: "
                f"{bundle.report['n_assays']} assays, "
                f"{bundle.report['n_assay_kcc_links']} assay-KC links, "
                f"{bundle.report['n_references']} references, "
                f"{bundle.report['n_annotations']} annotations, "
                f"{citation_stats['n_citations_added']} evidence-citations added."
            ),
        )
    )
    db.commit()


# ─── orchestration ────────────────────────────────────────────────────────────


def write_json_dump(bundle: KCADBundle, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "assays.json").write_text(json.dumps(bundle.assays, indent=2, ensure_ascii=False))
    (out_dir / "assay_kccs.json").write_text(
        json.dumps(bundle.assay_kccs, indent=2, ensure_ascii=False)
    )
    (out_dir / "references.json").write_text(
        json.dumps(bundle.references, indent=2, ensure_ascii=False)
    )
    (out_dir / "annotations.json").write_text(
        json.dumps(bundle.annotations, indent=2, ensure_ascii=False)
    )
    (out_dir / "agent_references.json").write_text(
        json.dumps(bundle.agent_references, indent=2, ensure_ascii=False)
    )
    (out_dir / "import_report.json").write_text(json.dumps(bundle.report, indent=2))


def run(
    *,
    suppl_dir: Path = DEFAULT_SUPPL_DIR,
    chem_map_path: Path = DEFAULT_CHEM_MAP,
    agents_path: Path = DEFAULT_AGENTS_FILE,
    out_dir: Path | None = None,
    dry_run: bool = False,
    reset: bool = False,
    db: Session | None = None,
    include_supplementary: bool = False,
) -> KCADBundle:
    """Import KCAD data into hKCC.

    Args:
        include_supplementary: If True, also run :func:`pipelines.import_kcad_supplementary.run`
            on the same session/suppl_dir, importing the five XLSX files
            (STable1 agents, STable2 column dictionary, STable3 abbreviations,
            STable4/5 subgroups + study designs) immediately after the CSVs.
    """
    pivot = load_pivot(suppl_dir / "pivot_table.csv")
    filtered = load_filtered(suppl_dir / "filtered_table.csv")
    chem_map = load_chem_map(chem_map_path)
    agent_seed = load_agent_seed(agents_path)
    log.info(
        "Loaded pivot=%d rows, filtered=%d rows, chem_map=%d entries, agent_seed=%d rows",
        len(pivot),
        len(filtered),
        len(chem_map),
        len(agent_seed),
    )

    bundle = build_bundle(pivot, filtered, chem_map)
    log.info("Built bundle: %s", bundle.report)

    if out_dir is not None:
        write_json_dump(bundle, out_dir)
        log.info("Wrote JSON dump to %s", out_dir)

    if not dry_run:
        own_db = db is None
        if own_db:
            db = SessionLocal()
        try:
            load_bundle(db, bundle, reset=reset, agent_seed=agent_seed)
            if include_supplementary:
                # Import deferred to runtime to avoid a hard circular import.
                from pipelines import import_kcad_supplementary

                supp_report = import_kcad_supplementary.run(
                    suppl_dir=suppl_dir, db=db
                )
                bundle.report["supplementary"] = supp_report
                log.info("Supplementary import: %s", supp_report)
        finally:
            if own_db:
                db.close()
    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import KCAD supplementary data into hKCC")
    parser.add_argument("--suppl-dir", type=Path, default=DEFAULT_SUPPL_DIR)
    parser.add_argument("--chem-map", type=Path, default=DEFAULT_CHEM_MAP)
    parser.add_argument("--agents", type=Path, default=DEFAULT_AGENTS_FILE)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="If set, write JSON staging dump here (e.g. exports/kcad/).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip the DB write, only build/JSON-dump.")
    parser.add_argument(
        "--reset-kcad",
        action="store_true",
        help="Delete existing source='kcad' rows before import.",
    )
    parser.add_argument(
        "--with-supplementary",
        action="store_true",
        help=(
            "Also import the 5 XLSX supplementary tables (STable1-5). "
            "Equivalent to running `python -m pipelines.import_kcad_supplementary` "
            "immediately after the CSV import."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    bundle = run(
        suppl_dir=args.suppl_dir,
        chem_map_path=args.chem_map,
        agents_path=args.agents,
        out_dir=args.out_dir,
        dry_run=args.dry_run,
        reset=args.reset_kcad,
        include_supplementary=args.with_supplementary,
    )
    print(json.dumps(bundle.report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
