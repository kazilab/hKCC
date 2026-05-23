"""Tests for the KCAD supplementary-tables importer (XLSX → DB).

Synthetic-data unit tests run on every CI invocation; the full-data smoke test
that exercises ``suppl_data/KCManuscript_STables*.xlsx`` is gated behind
``KCAD_REAL_DATA=1`` to keep CI fast.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.models import (
    KCC,
    Agent,
    Assay,
    AssayKCC,
    AssayKcSubgroup,
    AssayStudyDesign,
    Base,
    KcadAbbreviation,
    KcadColumnDefinition,
    Reference,
)
from pipelines import import_kcad_supplementary as supp
from pipelines.import_kcad import KCAD_PAPER_REF_ID

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_SUPPL_DIR = REPO_ROOT.parent / "suppl_data"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add_all(
        [
            KCC(
                id=f"kcc-{i:02d}",
                n=i,
                title=f"KCC {i}",
                short=f"KC{i}",
                description="",
                mechanism="",
                icon="circle",
                is_extended=(i > 10),
            )
            for i in range(1, 15)
        ]
    )
    session.add(
        Agent(
            id="benzene",
            name="Benzene",
            cas="71-43-2",
            iarc_group="1",
            agent_type="Industrial chemical",
            summary="curator-summary",
        )
    )
    # Pre-existing assay matching what STable4 will reference.
    session.add(
        Assay(
            id="kcad-32p-postlabeling-techniques",
            name="[32P]-Postlabeling techniques",
            type="in vitro",
            target="DNA",
            throughput="medium",
            oecd_tg=None,
            notes="",
            source="kcad",
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seed_dir(tmp_path: Path) -> Path:
    """Tiny synthetic versions of the three JSON seed files."""
    (tmp_path / "iarc_agents.json").write_text(
        json.dumps(
            {
                "agents": [
                    {
                        "id": "benzene",
                        "name": "Benzene",
                        "cas": "71-43-2",
                        "iarc_group": "1",
                        "monograph_volume": "100F",
                        "monograph_pub_year": "2012",
                        "evaluation_year": 2009,
                    },
                    {
                        "id": "2-mercaptobenzothiazole",
                        "name": "2-Mercaptobenzothiazole",
                        "cas": "149-30-4",
                        "iarc_group": "2A",
                        "monograph_volume": "115",
                        "monograph_pub_year": "2018",
                        "evaluation_year": 2016,
                    },
                ]
            }
        )
    )
    (tmp_path / "column_definitions.json").write_text(
        json.dumps(
            {
                "definitions": [
                    {"column_name": "KC", "definition": "Primary key characteristic of carcinogens"},
                    {"column_name": "Secondary_KC", "definition": "Other associated key characteristic"},
                ]
            }
        )
    )
    (tmp_path / "abbreviations.json").write_text(
        json.dumps(
            {
                "abbreviations": [
                    {"abbreviation": "8-OHdG", "expansion": "8-hydroxy-2'-deoxyguanosine"},
                    {"abbreviation": "ROS", "expansion": "reactive oxygen species"},
                ]
            }
        )
    )
    return tmp_path


@pytest.fixture()
def stable_xlsx_dir(tmp_path: Path) -> Path:
    """Tiny synthetic STable4 + STable5 workbooks with the real layout."""
    # STable4: KC1 + KC2 sheets, in vivo / ex vivo cols
    p4 = tmp_path / "stables45_kc4.xlsx"
    with pd.ExcelWriter(p4, engine="openpyxl") as w:
        # Sheet STable4A.KC1 — in vivo / ex vivo
        df = pd.DataFrame(
            [
                ["Supplementary Table 4(A).", None, None],
                [None, "in vivo", "ex vivo"],
                ["DNA adducts", None, None],
                ["[32P]-Postlabeling techniques", "✓", "✓"],
                ["DNA adductomics", "✓", None],
                ["Protein Adducts", None, None],
                ["Mass spectrometry", "✓", None],
            ]
        )
        df.to_excel(w, sheet_name="STable4A.KC1", header=False, index=False)
        # Sheet STable4B.KC2 — single row
        df2 = pd.DataFrame(
            [
                ["Supplementary Table 4(B).", None, None],
                [None, "in vivo", "ex vivo"],
                ["Chromosome damage", None, None],
                ["Comet assay", "✓", None],
            ]
        )
        df2.to_excel(w, sheet_name="STable4B.KC2", header=False, index=False)

    p5 = tmp_path / "stables45_kc5.xlsx"
    with pd.ExcelWriter(p5, engine="openpyxl") as w:
        df = pd.DataFrame(
            [
                ["Supplementary Table 5(A).", None, None],
                [None, "in vitro", "in silico"],
                ["DNA adducts", None, None],
                ["[32P]-Postlabeling techniques", "✓", None],
                ["In silico prediction", None, "✓"],
            ]
        )
        df.to_excel(w, sheet_name="STable5A.KC1", header=False, index=False)
    return tmp_path


# ─── helpers ────────────────────────────────────────────────────────────────


def test_norm_name_collapses_punctuation():
    a = supp._norm_name("2,2-diphenyl-1-picryl-hydrazyl (DPPH) reduction assay")
    b = supp._norm_name("2 2-diphenyl-1-picryl-hydrazyl (DPPH) reduction assay")
    c = supp._norm_name("2,2′-diphenyl-1-picryl-hydrazyl (DPPH) reduction assay")
    assert a == b == c


def test_is_check_recognises_marks():
    assert supp._is_check("✓") is True
    assert supp._is_check("x") is True
    assert supp._is_check("+") is True
    assert supp._is_check("") is False
    assert supp._is_check("-NA-") is False
    assert supp._is_check(None) is False


# ─── STable1 ────────────────────────────────────────────────────────────────


def test_stable1_fills_missing_iarc_metadata(db, seed_dir):
    # benzene already exists with iarc_group=1 but no monograph_volume etc.
    rows = supp.load_iarc_agents(seed_dir / "iarc_agents.json")
    report = supp.upsert_iarc_agents(db, rows)
    db.commit()

    benzene = db.get(Agent, "benzene")
    # Existing iarc_group preserved.
    assert benzene.iarc_group == "1"
    # Missing IARC metadata filled in.
    assert benzene.monograph_volume == "100F"
    assert benzene.evaluation_year == 2009
    # benzene's curator-set summary is preserved.
    assert benzene.summary == "curator-summary"

    # New agent inserted with paper anchor.
    mbt = db.get(Agent, "2-mercaptobenzothiazole")
    assert mbt is not None
    assert mbt.source_ref_id == KCAD_PAPER_REF_ID
    assert mbt.evaluation_year == 2016
    assert report["inserted"] == 1


def test_stable1_matches_on_cas_when_id_differs(db, seed_dir):
    # Rename one row in the seed so its id != existing agent's id, but CAS matches.
    raw = json.loads((seed_dir / "iarc_agents.json").read_text())
    raw["agents"][0]["id"] = "benzene-iarc"  # CAS still matches the existing benzene row
    (seed_dir / "iarc_agents.json").write_text(json.dumps(raw))
    rows = supp.load_iarc_agents(seed_dir / "iarc_agents.json")

    supp.upsert_iarc_agents(db, rows)
    db.commit()

    # Should match by CAS and not create a duplicate row.
    assert db.get(Agent, "benzene-iarc") is None
    benzene = db.get(Agent, "benzene")
    assert benzene.monograph_volume == "100F"


# ─── STable2 / STable3 ──────────────────────────────────────────────────────


def test_stable2_upserts_column_definitions(db, seed_dir):
    rows = supp.load_column_definitions(seed_dir / "column_definitions.json")
    n = supp.upsert_column_definitions(db, rows)
    db.commit()
    assert n == 2
    kc_def = db.get(KcadColumnDefinition, "KC")
    assert kc_def is not None
    assert "Primary key characteristic" in kc_def.definition
    assert kc_def.source_ref_id == KCAD_PAPER_REF_ID

    # Idempotent re-run with edited definition.
    rows[0]["definition"] = "Updated definition"
    supp.upsert_column_definitions(db, rows)
    db.commit()
    assert db.get(KcadColumnDefinition, "KC").definition == "Updated definition"


def test_stable3_upserts_abbreviations(db, seed_dir):
    rows = supp.load_abbreviations(seed_dir / "abbreviations.json")
    n = supp.upsert_abbreviations(db, rows)
    db.commit()
    assert n == 2
    a = db.get(KcadAbbreviation, "8-OHdG")
    assert a is not None
    assert a.expansion.startswith("8-hydroxy")
    assert a.source_ref_id == KCAD_PAPER_REF_ID


# ─── STable4 / STable5 ──────────────────────────────────────────────────────


def test_parse_stable45_extracts_triples(stable_xlsx_dir):
    bundle = supp.parse_stable45(
        stable_xlsx_dir / "stables45_kc4.xlsx", source_tag="stable4"
    )
    # KC1: 3 ✓s (postlab in vivo+ex vivo, DNA adductomics in vivo, mass spec in vivo) + KC2: 1
    designs_kc1 = {
        (t.assay_name, t.design, t.subgroup)
        for t in bundle.triples
        if t.kcc_id == "kcc-01"
    }
    assert ("[32P]-Postlabeling techniques", "in_vivo", "DNA adducts") in designs_kc1
    assert ("[32P]-Postlabeling techniques", "ex_vivo", "DNA adducts") in designs_kc1
    assert ("Mass spectrometry", "in_vivo", "Protein Adducts") in designs_kc1

    designs_kc2 = {(t.assay_name, t.design) for t in bundle.triples if t.kcc_id == "kcc-02"}
    assert ("Comet assay", "in_vivo") in designs_kc2


def test_load_stable45_persists_subgroups_and_designs(db, stable_xlsx_dir):
    bundle4 = supp.parse_stable45(
        stable_xlsx_dir / "stables45_kc4.xlsx", source_tag="stable4"
    )
    bundle5 = supp.parse_stable45(
        stable_xlsx_dir / "stables45_kc5.xlsx", source_tag="stable5"
    )
    # Need the paper reference to exist for FK.
    db.merge(Reference(id=KCAD_PAPER_REF_ID, year=2025, authors="Rigutto", title="x", journal="Database", source="kcad-paper"))
    db.flush()

    report = supp.load_stable45_into_db(db, bundle4=bundle4, bundle5=bundle5)
    db.commit()

    # Existing postlabeling assay got subgroup + designs on KC1.
    sg = db.get(AssayKcSubgroup, ("kcad-32p-postlabeling-techniques", "kcc-01"))
    assert sg is not None
    assert sg.subgroup == "DNA adducts"

    designs = db.scalars(
        select(AssayStudyDesign).where(
            AssayStudyDesign.assay_id == "kcad-32p-postlabeling-techniques",
            AssayStudyDesign.kcc_id == "kcc-01",
        )
    ).all()
    design_set = {d.design for d in designs}
    assert design_set == {"in_vivo", "ex_vivo", "in_vitro"}

    # Brand-new assays inserted for names not in DB.
    n_assays = db.scalar(select(func.count()).select_from(Assay))
    assert n_assays >= 5  # original + DNA adductomics + Mass spectrometry + Comet assay + In silico prediction
    assert report["n_new_assays"] >= 4

    # Every newly-created assay carries the paper anchor.
    new_assays = db.scalars(
        select(Assay).where(Assay.source == "kcad-stable45")
    ).all()
    assert new_assays
    assert all(a.source_ref_id == KCAD_PAPER_REF_ID for a in new_assays)

    # AssayKCC links also created for those new assays.
    n_links = db.scalar(select(func.count()).select_from(AssayKCC))
    assert n_links >= 4


def test_stable45_is_idempotent(db, stable_xlsx_dir):
    db.merge(Reference(id=KCAD_PAPER_REF_ID, year=2025, authors="Rigutto", title="x", journal="Database", source="kcad-paper"))
    db.flush()
    bundle4 = supp.parse_stable45(stable_xlsx_dir / "stables45_kc4.xlsx", source_tag="stable4")
    bundle5 = supp.parse_stable45(stable_xlsx_dir / "stables45_kc5.xlsx", source_tag="stable5")

    supp.load_stable45_into_db(db, bundle4=bundle4, bundle5=bundle5)
    db.commit()
    n_sg_before = db.scalar(select(func.count()).select_from(AssayKcSubgroup))
    n_sd_before = db.scalar(select(func.count()).select_from(AssayStudyDesign))

    # Second run should give the same counts (reset+upsert path).
    supp.load_stable45_into_db(db, bundle4=bundle4, bundle5=bundle5)
    db.commit()
    assert db.scalar(select(func.count()).select_from(AssayKcSubgroup)) == n_sg_before
    assert db.scalar(select(func.count()).select_from(AssayStudyDesign)) == n_sd_before


# ─── full pipeline ──────────────────────────────────────────────────────────


def test_run_full_pipeline_writes_paper_reference(db, seed_dir, stable_xlsx_dir):
    # Provide the synthetic STable4/5 files in a directory the runner expects.
    (stable_xlsx_dir / supp.STABLE4_FILE).write_bytes(
        (stable_xlsx_dir / "stables45_kc4.xlsx").read_bytes()
    )
    (stable_xlsx_dir / supp.STABLE5_FILE).write_bytes(
        (stable_xlsx_dir / "stables45_kc5.xlsx").read_bytes()
    )
    supp.run(suppl_dir=stable_xlsx_dir, seed_dir=seed_dir, db=db)
    db.commit()

    paper = db.get(Reference, KCAD_PAPER_REF_ID)
    assert paper is not None
    assert paper.doi == "10.1093/database/baaf026"
    assert paper.article_id == "baaf026"


# ─── full real-data smoke ──────────────────────────────────────────────────


@pytest.mark.skipif(
    not REAL_SUPPL_DIR.exists() or os.environ.get("KCAD_REAL_DATA") != "1",
    reason="Set KCAD_REAL_DATA=1 to run the full-XLSX smoke test",
)
def test_real_data_stable4_5_coverage(db):
    """Every ✓ in STable4/5 must reach the DB as a study-design row."""
    # Seed paper + base KCAD CSV import first so assay rows exist.
    from pipelines import import_kcad

    import_kcad.run(suppl_dir=REAL_SUPPL_DIR, db=db)
    report = supp.run(suppl_dir=REAL_SUPPL_DIR, db=db)

    # Sanity: STable1 produced 24 IARC-derived rows.
    assert report["stable1_agents"]["inserted"] + report["stable1_agents"]["updated"] > 0
    # STable2: 28 column definitions persisted.
    n_defs = db.scalar(select(func.count()).select_from(KcadColumnDefinition))
    assert n_defs >= 25
    # STable3: 49 abbreviations.
    n_abbrevs = db.scalar(select(func.count()).select_from(KcadAbbreviation))
    assert n_abbrevs >= 45
    # STable4/5: at least 700 study-design rows across KC1-10.
    n_sd = db.scalar(select(func.count()).select_from(AssayStudyDesign))
    assert n_sd > 500
    # And every one of them anchored to the paper.
    n_anchored = db.scalar(
        select(func.count()).where(
            AssayStudyDesign.source_ref_id == KCAD_PAPER_REF_ID
        )
    )
    assert n_anchored == n_sd
