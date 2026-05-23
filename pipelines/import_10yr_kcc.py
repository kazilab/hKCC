"""Import the IARC 10-year retrospective KCC evidence matrix.

Source publication
------------------

  Rusyn I, Wright FA, Smith MT, et al.
  "Ten years of using key characteristics of human carcinogens to organize
  and evaluate mechanistic evidence in IARC Monographs Volumes 112-130:
  impact and lessons learned."
  Toxicological Sciences 198(1):141-154 (2024). doi:10.1093/toxsci/kfad134

Source files (under ``references/kcc-10yr/kfad134_Supplementary_Data/``)
-----------------------------------------------------------------------

* ``toxsci-23-0374-File012.xlsx``   one sheet per IARC Monograph volume
  (112-130), each containing Agent × Model-system × 10 KCs cells with
  values in {Yes, No, Equivocal, Protective}. Parsed into
  ``iarc_monograph_kc_calls``.
* ``toxsci-23-0374-File014.xlsx``   Supp Table 4: 73 agents × 10 KCs with
  standardized strength labels {Strong, Moderate, Weak} + per-agent
  ``Mechanistic data role`` {Supportive, Upgrade, Not used}. Parsed into
  ``iarc_monograph_kc_strength``.

The importer also (a) loads/upserts the ``rusyn2024-tenyears`` Reference row
itself (and other foundational references from ``db/seed/refs/foundational.json``)
and (b) aggregates per-(agent, KC) calls into ``Evidence.score`` using the
documented rule in ``docs/KCC_EVIDENCE_RULES.md``.

Scope:

* KC1..KC10 only — the 10-yr retrospective predates the extended hKCC KCs
  (11-14), which get no rows from this source.
* Idempotent: re-running clears prior ``source_ref_id=rusyn2024-tenyears``
  rows in the two new tables and re-inserts. Evidence rows produced by this
  importer carry ``source='10yr-iarc'`` so they can be reset selectively
  without touching curator scores.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from db.models import (
    Agent,
    Evidence,
    EvidenceCitation,
    IarcMonographKcCall,
    IarcMonographKcStrength,
    Reference,
    ReferenceTag,
)
from db.session import SessionLocal

log = logging.getLogger("import_10yr_kcc")

REPO_ROOT = Path(__file__).resolve().parents[2]
REFS_DIR = REPO_ROOT / "references"
KCC10YR_DIR = REFS_DIR / "kcc-10yr" / "kfad134_Supplementary_Data"

DEFAULT_FILE012 = KCC10YR_DIR / "toxsci-23-0374-File012.xlsx"
DEFAULT_FILE014 = KCC10YR_DIR / "toxsci-23-0374-File014.xlsx"

SEED_REFS_FILE = (
    Path(__file__).resolve().parents[1] / "db" / "seed" / "refs" / "foundational.json"
)

# Reference id anchoring every 10-yr-retrospective row.
KCC10YR_REF_ID = "rusyn2024-tenyears"
KCC10YR_DOI = "10.1093/toxsci/kfad134"
KCC10YR_SOURCE_TAG = "10yr-iarc"

# Eight model-system row types appear in each File012 agent block, in this order:
PRIMARY_MODEL_SYSTEMS: tuple[str, ...] = (
    "Exposed Humans",
    "Human cells in vitro",
    "Mammalian in vivo",
)
SUPPLEMENTARY_MODEL_SYSTEMS: tuple[str, ...] = (
    "Mammalian in vitro",
    "Other in vivo",
    "Other in vitro",
    "ToxCast data",
    "ToxRefDB data",
)
MODEL_SYSTEMS: tuple[str, ...] = PRIMARY_MODEL_SYSTEMS + SUPPLEMENTARY_MODEL_SYSTEMS
MODEL_SYSTEM_SET: frozenset[str] = frozenset(MODEL_SYSTEMS)

# The terminator row of every agent block — paper-aggregate strength per KC for
# that volume. Captured separately into iarc_monograph_kc_strength (per-volume
# rows) with strength_label ∈ {Strong, Moderate, Suggestive, Weak}.
OVERALL_STRENGTH_LABEL = "Overall strength"
ALLOWED_OVERALL_STRENGTH: frozenset[str] = frozenset(
    {"Strong", "Moderate", "Suggestive", "Weak"}
)

ALLOWED_CALLS: frozenset[str] = frozenset({"Yes", "No", "Equivocal", "Protective"})
# Per-paper synonyms for "Protective" (agent actively suppresses the KC).
PROTECTIVE_SYNONYMS: frozenset[str] = frozenset({"Protective", "Antioxidant", "Antiinflammatory"})
ALLOWED_STRENGTH: frozenset[str] = frozenset({"Strong", "Moderate", "Weak"})

# Metadata labels seen in the Agent column on non-first rows of an agent block.
# They tag the row's *cohort-level* IARC working-group judgement, not a new agent.
_IARC_GROUP_RE = re.compile(r"^\s*([1-4][A-C]?(?:\s*\(.+?\))?(?:\s*\d+\s*\(.+?\))?)\s*$")
_HUMAN_EVIDENCE_RE = re.compile(r"^\s*H-[A-Za-z]", re.IGNORECASE)
_ANIMAL_EVIDENCE_RE = re.compile(r"^\s*A-[A-Za-z]", re.IGNORECASE)
_MECH_ROLE_RE = re.compile(r"^\s*M-[A-Za-z]", re.IGNORECASE)

KC_NUM_RE = re.compile(r"^\s*(\d{1,2})[\.\s]")
VOLUME_NUM_RE = re.compile(r"\b(?:Vol[a-z]*\s*)?(\d{2,3})\b")
YEAR_RE = re.compile(r"\((\d{4})\)")


# ─── helpers ─────────────────────────────────────────────────────────────────


def _slugify(s: str, *, maxlen: int = 64) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen] or "unknown"


def _agent_id(name: str) -> str:
    return _slugify(name)


def _parse_sheet_meta(sheet_name: str) -> tuple[str | None, int | None]:
    """Extract (volume_number, year) from a sheet name like 'Volume 120 (2017)'.

    Handles the typo "Volune 121 (2018)" in the source file.
    """
    vol_m = VOLUME_NUM_RE.search(sheet_name)
    year_m = YEAR_RE.search(sheet_name)
    return (
        vol_m.group(1) if vol_m else None,
        int(year_m.group(1)) if year_m else None,
    )


def _kc_num(col_name: str) -> int | None:
    m = KC_NUM_RE.match(col_name)
    return int(m.group(1)) if m else None


def _norm_call(raw: str) -> tuple[str | None, str | None]:
    """Map a cell to (canonical_call, raw_call).

    Returns (None, None) for empty / unrecognised cells.
    """
    s = (raw or "").strip()
    if not s:
        return None, None
    if s in PROTECTIVE_SYNONYMS:
        return "Protective", s
    if s in ALLOWED_CALLS:
        return s, s
    return None, s


# ─── seed: foundational refs ─────────────────────────────────────────────────


def load_foundational_refs(path: Path = SEED_REFS_FILE) -> list[dict]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw.get("references", []))


def _upsert(db: Session, model, rows: list[dict], pk_cols: list[str]) -> None:
    if not rows:
        return
    dialect = db.bind.dialect.name if db.bind is not None else ""
    if dialect == "postgresql":
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


def seed_foundational_references(db: Session, refs: list[dict]) -> tuple[int, int]:
    """Idempotent upsert of foundational reference rows + their tags.

    Returns ``(n_refs_seeded, n_tags_seeded)``. Existing rows are merged
    field-by-field — callers can safely re-run.
    """
    if not refs:
        return 0, 0
    ref_rows: list[dict] = []
    tag_rows: list[dict] = []
    for r in refs:
        ref_rows.append(
            {
                "id": r["id"],
                "year": r.get("year"),
                "authors": r.get("authors", "—"),
                "title": r.get("title", "—"),
                "journal": r.get("journal", "—"),
                "vol": r.get("vol"),
                "doi": r.get("doi"),
                "pmid": r.get("pmid"),
                "citations": r.get("citations"),
                "source": r.get("source", "foundational"),
                "article_id": r.get("article_id"),
                "url": r.get("url"),
                "pdf_path": r.get("pdf_path"),
            }
        )
        for tag in r.get("tags", []) or []:
            tag_rows.append({"reference_id": r["id"], "tag": tag})

    _upsert(db, Reference, ref_rows, pk_cols=["id"])
    db.flush()
    if tag_rows:
        _upsert(db, ReferenceTag, tag_rows, pk_cols=["reference_id", "tag"])
        db.flush()
    return len(ref_rows), len(tag_rows)


# ─── parse: File012 (Yes/No/Equivocal/Protective matrix per volume) ───────────


@dataclass
class TenYrBundle:
    calls: list[dict] = field(default_factory=list)
    volume_strengths: list[dict] = field(default_factory=list)
    strengths: list[dict] = field(default_factory=list)
    agents_seen: dict[str, dict] = field(default_factory=dict)
    report: dict = field(default_factory=dict)


def _is_metadata_label(cell: str) -> bool:
    """True if the Agent-column cell holds an IARC cohort label, not an agent name.

    Inside each agent block, the Agent column on rows 3-6 carries
    paper-internal annotations that should NOT be interpreted as new agents:

    * IARC working-group conclusion (``2A``, ``1``, ``2A (red) 1(processed)``)
    * Strength of evidence in **humans**  (``H-Limited`` / ``H-Sufficient`` / …)
    * Strength of evidence in **animals** (``A-Sufficient`` / ``A-Limited`` / …)
    * **Mechanistic** data role          (``M-Supportive`` / ``M-Upgrade`` / …)
    """
    s = cell.strip()
    if not s:
        return False
    if _HUMAN_EVIDENCE_RE.match(s) or _ANIMAL_EVIDENCE_RE.match(s) or _MECH_ROLE_RE.match(s):
        return True
    if _IARC_GROUP_RE.match(s) and len(s) <= 32:
        return True
    return False


def _extract_iarc_group(cell: str) -> str | None:
    """Return the IARC group label if the cell looks like one, else None."""
    s = cell.strip()
    if not s:
        return None
    m = _IARC_GROUP_RE.match(s)
    if not m or len(s) > 32:
        return None
    # Filter out things that match the group regex but are obviously chemical
    # names with a trailing digit (none observed in this corpus, but guard).
    if any(ch.isalpha() and ch.upper() != ch for ch in s):
        return None
    return s


def parse_file012(path: Path = DEFAULT_FILE012) -> tuple[list[dict], list[dict], dict[str, dict]]:
    """Parse all volume sheets of File012 into call rows + per-volume strength rows.

    Returns ``(call_rows, volume_strength_rows, agent_meta)`` where:

    * ``call_rows`` items have keys ``agent_name``, ``kc_num``,
      ``monograph_volume``, ``monograph_year``, ``model_system``, ``call``,
      ``raw_call``. ``model_system`` covers all 8 paper categories
      (3 primary + 5 supplementary).
    * ``volume_strength_rows`` items have ``agent_name``, ``kc_num``,
      ``monograph_volume``, ``monograph_year``, ``strength_label``
      ∈ {Strong, Moderate, Suggestive, Weak}. Sourced from the
      ``Overall strength`` row at the bottom of each agent block.
    * ``agent_meta[agent_name]`` carries ``iarc_group`` (from the row 3
      ``Mammalian in vivo`` cell of the Agent column), plus the first
      monograph volume in which the agent appears.

    The parser walks rows linearly, treating the per-block layout
    deterministically: a fresh agent begins on the next ``Exposed Humans``
    row after a separator; metadata labels in the Agent column on subsequent
    rows are tagged and not interpreted as agents.
    """
    if not path.is_file():
        raise FileNotFoundError(path)
    xls = pd.ExcelFile(path)
    call_rows: list[dict] = []
    volume_strength_rows: list[dict] = []
    agent_meta: dict[str, dict] = {}

    for sheet in xls.sheet_names:
        vol, year = _parse_sheet_meta(sheet)
        if vol is None:
            log.warning("Could not extract volume number from sheet %r — skipping", sheet)
            continue

        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        first_cell = str(raw.iloc[0, 0]) if not raw.empty else ""
        has_monograph_col = "Monograph" in first_cell

        df = pd.read_excel(path, sheet_name=sheet, header=0)
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty:
            continue

        agent_col = df.columns[1] if has_monograph_col else df.columns[0]
        ms_idx = list(df.columns).index(agent_col) + 1
        if ms_idx >= len(df.columns):
            continue
        model_col = df.columns[ms_idx]
        kc_cols = list(df.columns[ms_idx + 1:])

        # Walk row by row. The current agent persists until we hit a separator
        # row (blank model_system + blank agent) and the next block begins.
        current_agent: str | None = None
        for _, row in df.iterrows():
            agent_cell = row[agent_col]
            ms_cell = row[model_col]
            agent_str = "" if pd.isna(agent_cell) else str(agent_cell).strip()
            ms_str = "" if pd.isna(ms_cell) else str(ms_cell).strip()

            # Blank row → reset current_agent (end of block).
            if not agent_str and not ms_str:
                current_agent = None
                continue

            # A row with a "fresh" non-empty Agent cell that is NOT a metadata
            # label starts a new agent block. We use the row's model_system
            # ("Exposed Humans") as additional confirmation.
            if agent_str and not _is_metadata_label(agent_str) and ms_str == "Exposed Humans":
                current_agent = agent_str
                meta = agent_meta.setdefault(current_agent, {})
                meta.setdefault("first_volume", vol)
                meta.setdefault("first_year", year)
            else:
                # Continuation row: capture annotation labels if present.
                if current_agent and agent_str:
                    group = _extract_iarc_group(agent_str)
                    if group:
                        agent_meta.setdefault(current_agent, {}).setdefault(
                            "iarc_group", group
                        )

            if current_agent is None:
                continue

            # Overall strength row: emit volume_strength_rows; not a call.
            if ms_str == OVERALL_STRENGTH_LABEL:
                for col in kc_cols:
                    kc_n = _kc_num(col)
                    if kc_n is None or not (1 <= kc_n <= 10):
                        continue
                    cell = row[col]
                    if pd.isna(cell):
                        continue
                    label = str(cell).strip()
                    if label not in ALLOWED_OVERALL_STRENGTH:
                        continue
                    volume_strength_rows.append(
                        {
                            "agent_name": current_agent,
                            "kc_num": kc_n,
                            "monograph_volume": vol,
                            "monograph_year": year,
                            "strength_label": label,
                        }
                    )
                continue

            if ms_str not in MODEL_SYSTEM_SET:
                continue

            for col in kc_cols:
                kc_n = _kc_num(col)
                if kc_n is None or not (1 <= kc_n <= 10):
                    continue
                cell = row[col]
                call, raw_call = _norm_call("" if pd.isna(cell) else str(cell))
                if call is None:
                    continue
                call_rows.append(
                    {
                        "agent_name": current_agent,
                        "kc_num": kc_n,
                        "monograph_volume": vol,
                        "monograph_year": year,
                        "model_system": ms_str,
                        "call": call,
                        "raw_call": raw_call,
                    }
                )

    return call_rows, volume_strength_rows, agent_meta


# ─── parse: File014 (standardized strength + data role) ──────────────────────


def parse_file014(path: Path = DEFAULT_FILE014) -> list[dict]:
    """Parse Supp Table 4 into a flat list of strength rows.

    Each item has ``agent_name``, ``iarc_group``, ``data_role``, ``kc_num``,
    ``strength_label``.
    """
    if not path.is_file():
        raise FileNotFoundError(path)
    df = pd.read_excel(path, sheet_name=0, header=1)
    df.columns = [str(c).strip() for c in df.columns]
    out: list[dict] = []
    for _, row in df.iterrows():
        agent_name = str(row.get("Agent", "")).strip()
        if not agent_name or agent_name == "nan":
            continue
        group = row.get("Group")
        group = str(group).strip() if pd.notna(group) else None
        data_role = row.get("Mechanistic data role")
        data_role = str(data_role).strip() if pd.notna(data_role) else None
        for kc_n in range(1, 11):
            col = f"KC{kc_n}"
            if col not in df.columns:
                continue
            val = row[col]
            if pd.isna(val):
                continue
            s = str(val).strip()
            if s not in ALLOWED_STRENGTH:
                continue
            out.append(
                {
                    "agent_name": agent_name,
                    "iarc_group": group,
                    "data_role": data_role,
                    "kc_num": kc_n,
                    "strength_label": s,
                }
            )
    return out


# ─── agent resolution ─────────────────────────────────────────────────────────


_NAME_FOLD_RE = re.compile(r"[^a-z0-9]+")


def _fold(name: str) -> str:
    """Aggressively normalise an agent name for cross-source matching.

    Strips accents, lower-cases, and collapses non-alphanumeric runs. Used as
    the lookup key when matching paper-verbatim agent strings against the
    Agent table (which may already hold a curator-friendly form).
    """
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return _NAME_FOLD_RE.sub("", s)


def _build_agent_index(db: Session) -> dict[str, str]:
    """Folded-name → Agent.id index for fuzzy resolution."""
    rows = db.execute(select(Agent.id, Agent.name)).all()
    idx: dict[str, str] = {}
    for aid, name in rows:
        idx.setdefault(_fold(name), aid)
        idx.setdefault(_fold(aid), aid)
    return idx


def _resolve_or_insert_agent(
    db: Session,
    agent_name: str,
    *,
    iarc_group: str | None,
    monograph_volume: str | None,
    monograph_year: int | None,
    name_index: dict[str, str],
) -> str:
    """Return the Agent.id for ``agent_name``, inserting a stub if absent.

    Stub rows carry ``source_ref_id=KCC10YR_REF_ID`` and a minimal placeholder
    summary so the importer never silently drops authoritative paper data.
    """
    key = _fold(agent_name)
    if key in name_index:
        return name_index[key]

    aid = _agent_id(agent_name)
    # Disambiguate against the (folded) id space.
    if _fold(aid) in name_index:
        # Distinct paper name collides with existing id — keep paper-faithful slug.
        suffix = 2
        while _fold(f"{aid}-{suffix}") in name_index:
            suffix += 1
        aid = f"{aid}-{suffix}"

    db.add(
        Agent(
            id=aid,
            name=agent_name,
            cas=None,
            iarc_group=iarc_group,
            agent_type="Industrial chemical",
            summary=(
                f"Imported from IARC Monograph Vol {monograph_volume or '?'} "
                f"({monograph_year or '?'}) via Rusyn et al. 2024 "
                "(10-year KCC retrospective). Curator review pending."
            ),
            last_review=datetime.now(UTC),
            monograph_volume=str(monograph_volume) if monograph_volume else None,
            monograph_pub_year=str(monograph_year) if monograph_year else None,
            evaluation_year=monograph_year,
            source_ref_id=KCC10YR_REF_ID,
        )
    )
    db.flush()
    name_index[_fold(agent_name)] = aid
    name_index[_fold(aid)] = aid
    return aid


# ─── score aggregator ─────────────────────────────────────────────────────────


_STRENGTH_TO_SCORE = {"Strong": 4, "Moderate": 3, "Weak": 2}


def aggregate_evidence(
    call_rows: list[dict],
    strength_rows: list[dict],
    agent_index: dict[str, str],
) -> list[dict]:
    """Build Evidence rows from File012 calls + File014 paper-aggregate strengths.

    The score for each (agent, KC) follows the documented dual-track rule
    (see :doc:`KCC_EVIDENCE_RULES`):

    **Primary (when File014 covers the pair):**

    +---------------------+----------------+
    | File014 strength    | Evidence.score |
    +=====================+================+
    | ``Strong``          | 4 (Convincing) |
    | ``Moderate``        | 3 (Strong)     |
    | ``Weak``            | 2 (Moderate)   |
    +---------------------+----------------+

    **Fallback (no File014 row — counts Yes across the 3 primary model
    systems only: Exposed Humans / Human cells in vitro / Mammalian in vivo):**

    +---------------------------------+----------------+
    | Primary-system ``Yes`` count    | Evidence.score |
    +=================================+================+
    | ≥3 (all 3 systems converge)     | 4              |
    | 2                               | 3              |
    | 1                               | 2              |
    | 0, ≥1 ``Equivocal``             | 1              |
    | 0, only ``No`` / ``Protective`` | 0              |
    +---------------------------------+----------------+

    The five supplementary systems (``Mammalian in vitro``, ``Other in vivo``,
    ``Other in vitro``, ``ToxCast data``, ``ToxRefDB data``) are preserved
    in ``iarc_monograph_kc_calls`` but do not contribute to the headline score
    when File014 is silent — this mirrors how the IARC working groups treat
    them as supportive context rather than primary evidence.

    Every produced ``curator_notes`` starts with the sentinel ``[10yr-iarc]``
    so an idempotent re-import can locate and refresh just these rows without
    touching curator-authored Evidence.
    """
    # Index File014 strengths by (agent_name, kc_num).
    strength_by_pair: dict[tuple[str, int], dict] = {
        (s["agent_name"], s["kc_num"]): s for s in strength_rows
    }

    # Bucket calls per (agent, KC).
    by_pair: dict[tuple[str, int], dict] = defaultdict(
        lambda: {
            "yes_primary": 0,
            "no_primary": 0,
            "equiv_primary": 0,
            "protective_primary": 0,
            "yes_supp": 0,
            "no_supp": 0,
            "equiv_supp": 0,
            "protective_supp": 0,
            "volumes": set(),
        }
    )
    for c in call_rows:
        key = (c["agent_name"], c["kc_num"])
        bucket = by_pair[key]
        bucket["volumes"].add(c["monograph_volume"])
        is_primary = c["model_system"] in PRIMARY_MODEL_SYSTEMS
        suffix = "primary" if is_primary else "supp"
        if c["call"] == "Yes":
            bucket[f"yes_{suffix}"] += 1
        elif c["call"] == "No":
            bucket[f"no_{suffix}"] += 1
        elif c["call"] == "Equivocal":
            bucket[f"equiv_{suffix}"] += 1
        elif c["call"] == "Protective":
            bucket[f"protective_{suffix}"] += 1

    # Union of all pairs that have either calls or strengths.
    all_pairs = set(by_pair.keys()) | set(strength_by_pair.keys())
    out: list[dict] = []
    for agent_name, kc_n in sorted(all_pairs):
        aid = agent_index.get(_fold(agent_name))
        if not aid:
            continue
        b = by_pair.get((agent_name, kc_n))
        strength = strength_by_pair.get((agent_name, kc_n))

        if strength is not None:
            score = _STRENGTH_TO_SCORE.get(strength["strength_label"], 2)
            rationale = (
                f"File014 standardized strength = {strength['strength_label']}"
                + (f"; role = {strength['data_role']}" if strength.get("data_role") else "")
            )
        elif b is not None:
            if b["yes_primary"] >= 3:
                score = 4
            elif b["yes_primary"] == 2:
                score = 3
            elif b["yes_primary"] == 1:
                score = 2
            elif b["equiv_primary"] >= 1:
                score = 1
            else:
                score = 0
            bits: list[str] = []
            if b["yes_primary"]:
                bits.append(f"Yes×{b['yes_primary']} (primary)")
            if b["equiv_primary"]:
                bits.append(f"Equivocal×{b['equiv_primary']} (primary)")
            if b["no_primary"]:
                bits.append(f"No×{b['no_primary']} (primary)")
            if b["protective_primary"]:
                bits.append(f"Protective×{b['protective_primary']} (primary)")
            supp_bits: list[str] = []
            if b["yes_supp"]:
                supp_bits.append(f"Yes×{b['yes_supp']}")
            if b["no_supp"]:
                supp_bits.append(f"No×{b['no_supp']}")
            if b["equiv_supp"] or b["protective_supp"]:
                if b["equiv_supp"]:
                    supp_bits.append(f"Equivocal×{b['equiv_supp']}")
                if b["protective_supp"]:
                    supp_bits.append(f"Protective×{b['protective_supp']}")
            if supp_bits:
                bits.append(f"supplementary: {', '.join(supp_bits)}")
            rationale = "; ".join(bits) or "no calls"
        else:
            continue

        vols = ", ".join(sorted((b or {}).get("volumes", set())))
        out.append(
            {
                "agent_id": aid,
                "kcc_id": f"kcc-{kc_n:02d}",
                "score": score,
                "n_refs": 1,
                "curator_notes": (
                    "[10yr-iarc] Rusyn 2024"
                    + (f", IARC Monograph Vol(s) {vols}" if vols else "")
                    + f": {rationale}."
                ),
            }
        )
    return out


# ─── DB load ─────────────────────────────────────────────────────────────────


def reset_10yr_rows(db: Session) -> None:
    """Idempotent reset: drop all rows produced by previous 10-yr-retrospective runs.

    Curator-authored Evidence rows are preserved (only rows whose
    ``curator_notes`` start with the ``[10yr-iarc]`` prefix are touched).
    """
    db.execute(delete(IarcMonographKcCall).where(IarcMonographKcCall.source_ref_id == KCC10YR_REF_ID))
    db.execute(delete(IarcMonographKcStrength).where(IarcMonographKcStrength.source_ref_id == KCC10YR_REF_ID))

    # Drop the citation links + n_refs decrement, then drop any 10yr-only
    # Evidence rows (curator rows have a non-[10yr-iarc] curator_notes prefix).
    ev_ids = [
        ev_id
        for (ev_id,) in db.execute(
            select(Evidence.id).where(Evidence.curator_notes.like("[10yr-iarc]%"))
        )
    ]
    if ev_ids:
        db.execute(delete(EvidenceCitation).where(EvidenceCitation.evidence_id.in_(ev_ids)))
        db.execute(delete(Evidence).where(Evidence.id.in_(ev_ids)))
    db.flush()


def load_bundle(
    db: Session,
    bundle: TenYrBundle,
    *,
    reset: bool = True,
) -> dict:
    """Persist a TenYrBundle to the DB and link to the Rusyn 2024 reference.

    Returns the bundle's report dict, augmented with DB counters.
    """
    if reset:
        reset_10yr_rows(db)

    # Ensure the Rusyn 2024 ref exists and has the canonical tag.
    refs = load_foundational_refs()
    n_refs, n_tags = seed_foundational_references(db, refs)
    log.info("Seeded foundational refs: %d rows, %d tags", n_refs, n_tags)

    # Build agent index with whatever is in DB now.
    name_index = _build_agent_index(db)

    # Resolve / insert agent stubs for paper-only names.
    n_agents_new = 0
    for name, meta in bundle.agents_seen.items():
        before = len(name_index)
        _resolve_or_insert_agent(
            db,
            name,
            iarc_group=meta.get("iarc_group"),
            monograph_volume=meta.get("first_volume"),
            monograph_year=meta.get("first_year"),
            name_index=name_index,
        )
        if len(name_index) > before:
            n_agents_new += 1
    db.flush()

    # Insert call rows. Overall-strength rows (per-volume Strong/Moderate/...) ride
    # along as model_system='Overall strength' so the per-volume label stays
    # query-able without a sibling table.
    call_rows = [
        {
            "agent_id": name_index[_fold(c["agent_name"])],
            "kcc_id": f"kcc-{c['kc_num']:02d}",
            "monograph_volume": c["monograph_volume"],
            "monograph_year": c["monograph_year"],
            "model_system": c["model_system"],
            "call": c["call"],
            "raw_call": c["raw_call"],
            "source_ref_id": KCC10YR_REF_ID,
        }
        for c in bundle.calls
        if _fold(c["agent_name"]) in name_index
    ]
    vol_strength_rows = [
        {
            "agent_id": name_index[_fold(s["agent_name"])],
            "kcc_id": f"kcc-{s['kc_num']:02d}",
            "monograph_volume": s["monograph_volume"],
            "monograph_year": s["monograph_year"],
            "model_system": OVERALL_STRENGTH_LABEL,
            "call": s["strength_label"],
            "raw_call": s["strength_label"],
            "source_ref_id": KCC10YR_REF_ID,
        }
        for s in bundle.volume_strengths
        if _fold(s["agent_name"]) in name_index
    ]
    insert_rows = call_rows + vol_strength_rows
    if insert_rows:
        db.execute(IarcMonographKcCall.__table__.insert(), insert_rows)

    # Insert strength rows.
    strength_rows = [
        {
            "agent_id": name_index[_fold(s["agent_name"])],
            "kcc_id": f"kcc-{s['kc_num']:02d}",
            "strength_label": s["strength_label"],
            "data_role": s.get("data_role"),
            "iarc_group": s.get("iarc_group"),
            "source_ref_id": KCC10YR_REF_ID,
        }
        for s in bundle.strengths
        if _fold(s["agent_name"]) in name_index
    ]
    _upsert(db, IarcMonographKcStrength, strength_rows, pk_cols=["agent_id", "kcc_id"])

    # Aggregate Evidence — only for pairs that don't already have a curator row.
    existing_pairs = {
        (a, k) for (a, k) in db.execute(select(Evidence.agent_id, Evidence.kcc_id))
    }
    ev_rows = aggregate_evidence(bundle.calls, bundle.strengths, name_index)
    new_evidence = [r for r in ev_rows if (r["agent_id"], r["kcc_id"]) not in existing_pairs]
    if new_evidence:
        db.execute(Evidence.__table__.insert(), new_evidence)
    db.flush()

    # Link each new Evidence row to the Rusyn 2024 ref as a citation.
    ev_ids = db.execute(
        select(Evidence.id, Evidence.agent_id, Evidence.kcc_id).where(
            Evidence.curator_notes.like("[10yr-iarc]%")
        )
    ).all()
    citations = [
        {"evidence_id": ev_id, "reference_id": KCC10YR_REF_ID}
        for ev_id, _, _ in ev_ids
    ]
    # Use upsert to avoid duplicates if rerun.
    _upsert(db, EvidenceCitation, citations, pk_cols=["evidence_id", "reference_id"])

    db.commit()

    report = {
        **bundle.report,
        "n_agents_inserted": n_agents_new,
        "n_calls_loaded": len(call_rows),
        "n_volume_strengths_loaded": len(vol_strength_rows),
        "n_strengths_loaded": len(strength_rows),
        "n_evidence_inserted": len(new_evidence),
        "n_evidence_skipped_existing": len(ev_rows) - len(new_evidence),
        "n_citations_linked": len(citations),
    }
    return report


# ─── orchestration ───────────────────────────────────────────────────────────


def build_bundle(
    *,
    file012: Path = DEFAULT_FILE012,
    file014: Path = DEFAULT_FILE014,
) -> TenYrBundle:
    calls, volume_strengths, agent_meta = parse_file012(file012)
    strengths = parse_file014(file014) if file014.is_file() else []
    for s in strengths:
        meta = agent_meta.setdefault(s["agent_name"], {})
        if not meta.get("iarc_group") and s.get("iarc_group"):
            meta["iarc_group"] = s["iarc_group"]

    calls_per_kc: dict[int, int] = defaultdict(int)
    for c in calls:
        calls_per_kc[c["kc_num"]] += 1
    calls_per_ms: dict[str, int] = defaultdict(int)
    for c in calls:
        calls_per_ms[c["model_system"]] += 1
    report = {
        "n_call_cells": len(calls),
        "n_volume_strength_cells": len(volume_strengths),
        "n_paper_strength_cells": len(strengths),
        "n_unique_agents": len(agent_meta),
        "calls_per_kc": dict(sorted(calls_per_kc.items())),
        "calls_per_model_system": dict(sorted(calls_per_ms.items())),
        "volumes": sorted({c["monograph_volume"] for c in calls}),
    }
    return TenYrBundle(
        calls=calls,
        volume_strengths=volume_strengths,
        strengths=strengths,
        agents_seen=agent_meta,
        report=report,
    )


def run(
    *,
    file012: Path = DEFAULT_FILE012,
    file014: Path = DEFAULT_FILE014,
    dry_run: bool = False,
    reset: bool = True,
    db: Session | None = None,
) -> dict:
    bundle = build_bundle(file012=file012, file014=file014)
    log.info("Built 10-yr bundle: %s", bundle.report)
    if dry_run:
        return bundle.report

    own_db = db is None
    if own_db:
        db = SessionLocal()
    try:
        report = load_bundle(db, bundle, reset=reset)
        log.info("Loaded 10-yr bundle: %s", report)
        return report
    finally:
        if own_db:
            db.close()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import the IARC 10-year retrospective KCC matrix "
            "(Rusyn et al. 2024) into hKCC."
        )
    )
    parser.add_argument("--file012", type=Path, default=DEFAULT_FILE012)
    parser.add_argument("--file014", type=Path, default=DEFAULT_FILE014)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Skip clearing prior rusyn2024 rows before insert (default: reset).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    report = run(
        file012=args.file012,
        file014=args.file014,
        dry_run=args.dry_run,
        reset=not args.no_reset,
    )
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
