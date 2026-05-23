"""Import KCAD supplementary tables (XLSX) from ``suppl_data/``.

Companion to :mod:`pipelines.import_kcad` (which handles the two CSVs).
This module ingests the five XLSX files distributed with the paper:

* ``KCManuscript_STable1.xlsx``     — 24-row IARC agents catalog (CAS, group,
  monograph volume, publication year, evaluation year).
* ``KCManuscript_STable2.xlsx``     — 28-row column data dictionary for
  ``filtered_table.csv``.
* ``KCManuscript_STable3.xlsx``     — 49-row abbreviation glossary.
* ``KCManuscript_STables4A-J.xlsx`` — 10 sheets: per-KC assay catalog grouped
  by subgroup × {in vivo, ex vivo}.
* ``KCManuscript_STables5A-J.xlsx`` — 10 sheets: per-KC assay catalog grouped
  by subgroup × {in vitro, in silico}.

Source: Rigutto et al. 2025, ``10.1093/database/baaf026``. Every row written
by this module carries ``source_ref_id = KCAD_PAPER_REF_ID``.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db.models import (
    Agent,
    Assay,
    AssayKCC,
    AssayKcSubgroup,
    AssayStudyDesign,
    KcadAbbreviation,
    KcadColumnDefinition,
    Reference,
)
from db.session import SessionLocal
from pipelines.import_kcad import (
    KCAD_PAPER_REF_ID,
    KC_RANGE,
    _upsert,
    kcad_paper_reference,
)

log = logging.getLogger("import_kcad_supp")

KCAD_SEED_DIR = Path(__file__).resolve().parents[1] / "db" / "seed" / "kcad"
DEFAULT_SUPPL_DIR = Path(__file__).resolve().parents[1].parent / "suppl_data"

STABLE1_FILE = "KCManuscript_STable1.xlsx"
STABLE2_FILE = "KCManuscript_STable2.xlsx"
STABLE3_FILE = "KCManuscript_STable3.xlsx"
STABLE4_FILE = "KCManuscript_STables4A-J.xlsx"
STABLE5_FILE = "KCManuscript_STables5A-J.xlsx"

DESIGN_LABELS = {
    "in vivo": "in_vivo",
    "ex vivo": "ex_vivo",
    "in vitro": "in_vitro",
    "in silico": "in_silico",
}
CHECK_MARKS = {"✓", "✔", "x", "X", "yes", "Yes", "Y", "y", "1", "+"}

_NA_VALUES = {"", "-NA-", "—", "-", "NA", "nan", "NaN", "N/A", "—"}


# ─── helpers ────────────────────────────────────────────────────────────────


def _clean(v: object) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and v != v:
        return None
    s = str(v).strip()
    if s in _NA_VALUES:
        return None
    return s


def _norm_name(s: str) -> str:
    """Canonical form for assay-name matching across CSV / STable spellings.

    - Lowercase, NFKD, ASCII fold (drops curly quotes/diacritics).
    - Collapse all non-alphanumerics to a single space, trim, squish whitespace.
    """
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _slugify(s: str, *, maxlen: int = 72) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s[:maxlen] or "unknown"


def _is_check(v: object) -> bool:
    if v is None:
        return False
    if isinstance(v, float) and v != v:
        return False
    s = str(v).strip()
    if not s or s in _NA_VALUES:
        return False
    return s in CHECK_MARKS or len(s) == 1


# ─── STable1: IARC agents catalog ───────────────────────────────────────────


def load_iarc_agents(seed_path: Path | None = None) -> list[dict]:
    """Load the IARC agent seed JSON generated from ``KCManuscript_STable1``."""
    path = seed_path or (KCAD_SEED_DIR / "iarc_agents.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw.get("agents", []))


def upsert_iarc_agents(db: Session, rows: list[dict]) -> dict[str, int]:
    """Merge STable1 metadata into ``agents``.

    Match strategy (in order):
      1. Existing agent with the same CAS → fill missing IARC metadata only.
      2. Existing agent with the same canonical id → likewise fill missing.
      3. Otherwise: insert a new row with ``source_ref_id = KCAD_PAPER_REF_ID``.

    Curator-set fields are never overwritten — STable1 only fills *missing*
    cells on pre-existing agents.
    """
    by_cas: dict[str, Agent] = {}
    by_id: dict[str, Agent] = {}
    for a in db.scalars(select(Agent)).all():
        if a.cas:
            by_cas[a.cas.strip()] = a
        by_id[a.id] = a

    n_updated = 0
    n_inserted = 0
    for row in rows:
        cas = row.get("cas")
        target: Agent | None = None
        if cas:
            target = by_cas.get(cas)
        if target is None:
            target = by_id.get(row["id"])

        if target is not None:
            changed = False
            if not target.iarc_group and row.get("iarc_group"):
                target.iarc_group = row["iarc_group"]
                changed = True
            if not target.cas and row.get("cas"):
                target.cas = row["cas"]
                changed = True
            if not target.monograph_volume and row.get("monograph_volume"):
                target.monograph_volume = row["monograph_volume"]
                changed = True
            if not target.monograph_pub_year and row.get("monograph_pub_year"):
                target.monograph_pub_year = row["monograph_pub_year"]
                changed = True
            if not target.evaluation_year and row.get("evaluation_year"):
                try:
                    target.evaluation_year = int(row["evaluation_year"])
                    changed = True
                except (TypeError, ValueError):
                    pass
            if changed:
                n_updated += 1
            continue

        db.add(
            Agent(
                id=row["id"],
                name=row["name"],
                cas=row.get("cas"),
                iarc_group=row.get("iarc_group"),
                agent_type=row.get("agent_type", "Industrial chemical"),
                summary=row.get(
                    "summary",
                    f"IARC Monograph Volume {row.get('monograph_volume', '?')}, "
                    f"Group {row.get('iarc_group', '?')}.",
                ),
                monograph_volume=row.get("monograph_volume"),
                monograph_pub_year=row.get("monograph_pub_year"),
                evaluation_year=row.get("evaluation_year"),
                source_ref_id=KCAD_PAPER_REF_ID,
            )
        )
        n_inserted += 1

    if n_inserted or n_updated:
        db.flush()

    return {"updated": n_updated, "inserted": n_inserted}


# ─── STable2: column dictionary ─────────────────────────────────────────────


def load_column_definitions(seed_path: Path | None = None) -> list[dict]:
    path = seed_path or (KCAD_SEED_DIR / "column_definitions.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw.get("definitions", []))


def upsert_column_definitions(db: Session, rows: list[dict]) -> int:
    cleaned = [
        {
            "column_name": r["column_name"],
            "definition": r["definition"],
            "source_ref_id": KCAD_PAPER_REF_ID,
        }
        for r in rows
        if r.get("column_name") and r.get("definition")
    ]
    _upsert(db, KcadColumnDefinition, cleaned, pk_cols=["column_name"])
    return len(cleaned)


# ─── STable3: abbreviations ─────────────────────────────────────────────────


def load_abbreviations(seed_path: Path | None = None) -> list[dict]:
    path = seed_path or (KCAD_SEED_DIR / "abbreviations.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw.get("abbreviations", []))


def upsert_abbreviations(db: Session, rows: list[dict]) -> int:
    cleaned = [
        {
            "abbreviation": r["abbreviation"],
            "expansion": r["expansion"],
            "source_ref_id": KCAD_PAPER_REF_ID,
        }
        for r in rows
        if r.get("abbreviation") and r.get("expansion")
    ]
    _upsert(db, KcadAbbreviation, cleaned, pk_cols=["abbreviation"])
    return len(cleaned)


# ─── STable4 + STable5: subgroups + study designs ───────────────────────────


@dataclass
class SubgroupTriple:
    """One (assay, KC, design) row sourced from STable4/5."""

    assay_name: str
    kcc_id: str
    subgroup: str
    design: str
    source: str  # "stable4" or "stable5"


@dataclass
class STable45Bundle:
    triples: list[SubgroupTriple] = field(default_factory=list)
    # Distinct assay names appearing in STable4/5, even if no ✓ was found, so
    # callers can reconcile against the existing ``assays`` table.
    seen_assay_names: set[str] = field(default_factory=set)


_KC_RE = re.compile(r"KC(\d{1,2})", re.IGNORECASE)


def _sheet_kc(sheet_name: str) -> str | None:
    m = _KC_RE.search(sheet_name)
    if not m:
        return None
    n = int(m.group(1))
    if n not in KC_RANGE:
        return None
    return f"kcc-{n:02d}"


def parse_stable45(path: Path, source_tag: str) -> STable45Bundle:
    """Parse a STable4 or STable5 workbook into per-cell triples.

    Layout (per sheet):
      - row 0: merged title (``Supplementary Table 4(A). …``)
      - row 1: blank cell, then study-design headers in cols 1-2/1
      - row 2..: subgroup-header rows (col0 populated, study-design cols empty)
        and assay rows (col0 = assay name, study-design cols = ✓ for support).
    """
    bundle = STable45Bundle()
    xls = pd.ExcelFile(path)
    for sheet in xls.sheet_names:
        kcc_id = _sheet_kc(sheet)
        if kcc_id is None:
            log.warning("Skipping unrecognised sheet %s in %s", sheet, path.name)
            continue
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        # Locate the row that contains the study-design headers (the row whose
        # cells include 'in vivo'/'ex vivo'/'in vitro'/'in silico'). Usually row 1.
        header_row: int | None = None
        design_cols: dict[int, str] = {}
        for i in range(min(5, len(df))):
            row_vals = [(_clean(v) or "").lower() for v in df.iloc[i].tolist()]
            for col_idx, val in enumerate(row_vals):
                if val in DESIGN_LABELS:
                    design_cols[col_idx] = DESIGN_LABELS[val]
            if design_cols:
                header_row = i
                break
        if header_row is None or not design_cols:
            log.warning(
                "No design headers in %s :: %s — skipping", path.name, sheet
            )
            continue

        current_subgroup: str | None = None
        n_cols = df.shape[1]
        for i in range(header_row + 1, len(df)):
            row = df.iloc[i].tolist()
            col0 = _clean(row[0]) if n_cols > 0 else None
            checks: dict[str, bool] = {
                design: _is_check(row[col_idx])
                for col_idx, design in design_cols.items()
                if col_idx < n_cols
            }
            any_check = any(checks.values())

            if col0 and not any_check:
                # Subgroup header row.
                current_subgroup = col0
                continue

            if not col0:
                continue

            assay_name = col0
            bundle.seen_assay_names.add(assay_name)
            if current_subgroup is None:
                # Defensive: a check appeared before any subgroup header.
                current_subgroup = "—"
            for design, present in checks.items():
                if not present:
                    continue
                bundle.triples.append(
                    SubgroupTriple(
                        assay_name=assay_name,
                        kcc_id=kcc_id,
                        subgroup=current_subgroup,
                        design=design,
                        source=source_tag,
                    )
                )
    return bundle


def _build_assay_index(db: Session) -> dict[str, str]:
    """``normalised assay name → assay_id`` index over existing rows.

    Indexes both ``name`` and ``name_alt`` (the latter is set by the rename pass
    on subsequent runs).
    """
    index: dict[str, str] = {}
    for a in db.scalars(select(Assay)).all():
        index.setdefault(_norm_name(a.name), a.id)
        if a.name_alt:
            index.setdefault(_norm_name(a.name_alt), a.id)
    return index


def load_stable45_into_db(
    db: Session,
    *,
    bundle4: STable45Bundle,
    bundle5: STable45Bundle,
    reset: bool = True,
) -> dict[str, int]:
    """Persist subgroup + study-design rows; also insert any new assays.

    Idempotency: when ``reset=True`` (default), all existing
    ``assay_kc_subgroups`` and ``assay_study_designs`` rows linked to the
    KCAD paper are deleted before re-inserting.
    """
    if reset:
        db.execute(
            delete(AssayKcSubgroup).where(
                AssayKcSubgroup.source_ref_id == KCAD_PAPER_REF_ID
            )
        )
        db.execute(
            delete(AssayStudyDesign).where(
                AssayStudyDesign.source_ref_id == KCAD_PAPER_REF_ID
            )
        )
        db.flush()

    assay_index = _build_assay_index(db)

    # 1. Insert any new assays that appear only in STable4/5.
    n_new_assays = 0
    all_names = bundle4.seen_assay_names | bundle5.seen_assay_names
    for name in sorted(all_names):
        if _norm_name(name) in assay_index:
            continue
        aid = f"kcad-{_slugify(name)}"
        # Disambiguate slug collisions deterministically.
        base = aid
        n = 2
        while db.get(Assay, aid) is not None:
            aid = f"{base}-{n}"
            n += 1
        db.add(
            Assay(
                id=aid,
                name=name,
                type="other",
                target="—",
                throughput="low",
                oecd_tg=None,
                notes=(
                    "Imported from KCAD supplementary tables (Rigutto et al. 2025)."
                ),
                source="kcad-stable45",
                granularity="assay",
                source_ref_id=KCAD_PAPER_REF_ID,
            )
        )
        assay_index[_norm_name(name)] = aid
        n_new_assays += 1
    if n_new_assays:
        db.flush()

    # 2. Reconcile canonical names: STable4/5 have the correctly punctuated
    #    forms (commas, curly quotes) that pivot_table.csv mangled. For each
    #    name we see in STables, find the matching assay (by normalised key)
    #    and overwrite its ``name``, stashing the previous spelling on
    #    ``name_alt`` if it differs.
    rename_index: dict[str, str] = {}  # assay_id → canonical name
    for name in sorted(all_names, key=len, reverse=True):
        key = _norm_name(name)
        aid = assay_index.get(key)
        if aid is None:
            continue
        rename_index.setdefault(aid, name)
    n_renamed = 0
    for aid, canonical in rename_index.items():
        assay = db.get(Assay, aid)
        if assay is None:
            continue
        if assay.name == canonical:
            continue
        # Only stash old name on ``name_alt`` if not already set, so curator
        # overrides survive subsequent re-runs.
        if not assay.name_alt:
            assay.name_alt = assay.name
        assay.name = canonical
        n_renamed += 1
    if n_renamed:
        db.flush()

    # 3. Subgroup rows: single subgroup per (assay_id, kcc_id). Last-write-wins
    #    when STable4 and STable5 disagree (rare); STable4 wins because we
    #    process it first.
    subgroup_rows: dict[tuple[str, str], dict] = {}
    design_rows: dict[tuple[str, str, str], dict] = {}

    for bundle in (bundle4, bundle5):
        for t in bundle.triples:
            aid = assay_index.get(_norm_name(t.assay_name))
            if aid is None:
                continue
            sg_key = (aid, t.kcc_id)
            if sg_key not in subgroup_rows:
                subgroup_rows[sg_key] = {
                    "assay_id": aid,
                    "kcc_id": t.kcc_id,
                    "subgroup": t.subgroup,
                    "source_ref_id": KCAD_PAPER_REF_ID,
                }
            d_key = (aid, t.kcc_id, t.design)
            design_rows.setdefault(
                d_key,
                {
                    "assay_id": aid,
                    "kcc_id": t.kcc_id,
                    "design": t.design,
                    "source": t.source,
                    "source_ref_id": KCAD_PAPER_REF_ID,
                },
            )

    _upsert(
        db,
        AssayKcSubgroup,
        list(subgroup_rows.values()),
        pk_cols=["assay_id", "kcc_id"],
    )
    _upsert(
        db,
        AssayStudyDesign,
        list(design_rows.values()),
        pk_cols=["assay_id", "kcc_id", "design"],
    )

    # 4. STable4/5 also implicitly declares which KCs an assay supports. If
    #    we just inserted a brand-new assay (kcad-stable45), make sure its
    #    AssayKCC link exists.
    if n_new_assays:
        existing_links = {
            (aid, kid)
            for (aid, kid) in db.execute(select(AssayKCC.assay_id, AssayKCC.kcc_id))
        }
        new_links: list[dict] = []
        for (aid, kid) in {(r["assay_id"], r["kcc_id"]) for r in subgroup_rows.values()}:
            if (aid, kid) not in existing_links:
                new_links.append({"assay_id": aid, "kcc_id": kid})
        if new_links:
            _upsert(db, AssayKCC, new_links, pk_cols=["assay_id", "kcc_id"])

    return {
        "n_subgroups": len(subgroup_rows),
        "n_study_designs": len(design_rows),
        "n_new_assays": n_new_assays,
        "n_renamed_assays": n_renamed,
        "n_assay_names_in_stables": len(all_names),
    }


# ─── orchestration ──────────────────────────────────────────────────────────


def run(
    *,
    suppl_dir: Path = DEFAULT_SUPPL_DIR,
    seed_dir: Path = KCAD_SEED_DIR,
    db: Session | None = None,
    skip_agents: bool = False,
    skip_columns: bool = False,
    skip_abbrevs: bool = False,
    skip_stables45: bool = False,
) -> dict:
    """Run the full XLSX-based supplementary import.

    Idempotent: every operation upserts or deletes by ``source_ref_id`` first.
    """
    own_db = db is None
    if own_db:
        db = SessionLocal()

    try:
        # 0. Guarantee the publication row exists (it is the FK target for
        #    every row this importer writes).
        _upsert(db, Reference, [kcad_paper_reference()], pk_cols=["id"])
        db.flush()

        report: dict = {}

        if not skip_agents:
            agents = load_iarc_agents(seed_dir / "iarc_agents.json")
            report["stable1_agents"] = upsert_iarc_agents(db, agents)

        if not skip_columns:
            defs = load_column_definitions(seed_dir / "column_definitions.json")
            report["stable2_columns"] = upsert_column_definitions(db, defs)

        if not skip_abbrevs:
            abbrevs = load_abbreviations(seed_dir / "abbreviations.json")
            report["stable3_abbreviations"] = upsert_abbreviations(db, abbrevs)

        if not skip_stables45:
            bundle4 = parse_stable45(suppl_dir / STABLE4_FILE, source_tag="stable4")
            bundle5 = parse_stable45(suppl_dir / STABLE5_FILE, source_tag="stable5")
            report["stable45"] = load_stable45_into_db(
                db, bundle4=bundle4, bundle5=bundle5
            )

        db.commit()
        return report
    finally:
        if own_db:
            db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import KCAD XLSX supplementary tables (Rigutto et al. 2025)"
    )
    parser.add_argument("--suppl-dir", type=Path, default=DEFAULT_SUPPL_DIR)
    parser.add_argument("--seed-dir", type=Path, default=KCAD_SEED_DIR)
    parser.add_argument("--skip-agents", action="store_true")
    parser.add_argument("--skip-columns", action="store_true")
    parser.add_argument("--skip-abbrevs", action="store_true")
    parser.add_argument("--skip-stables45", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    report = run(
        suppl_dir=args.suppl_dir,
        seed_dir=args.seed_dir,
        skip_agents=args.skip_agents,
        skip_columns=args.skip_columns,
        skip_abbrevs=args.skip_abbrevs,
        skip_stables45=args.skip_stables45,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
