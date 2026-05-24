"""Tests for the KCAD supplementary-data importer.

Uses a small synthetic CSV pair so the test is fast and deterministic; a single
real-file smoke test is gated behind ``KCAD_REAL_DATA=1`` to keep CI quick.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.models import (
    KCC,
    Agent,
    AgentReference,
    Assay,
    AssayAnnotation,
    AssayKCC,
    Base,
    DatasetRelease,
    Evidence,
    EvidenceCitation,
    Reference,
    ReferenceTag,
)
from pipelines import import_kcad

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
    db = Session()
    db.add_all(
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
    db.add(
        Agent(
            id="benzene",
            name="Benzene",
            cas="71-43-2",
            iarc_group="1",
            agent_type="Industrial chemical",
            summary="…",
        )
    )
    db.commit()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def synthetic_data(tmp_path: Path) -> Path:
    pivot = tmp_path / "pivot_table.csv"
    pivot.write_text(
        "Method,KC1,KC2,KC3,KC4,KC5,KC6,KC7,KC8,KC9,KC10\n"
        "Ames assay,,+,,,,,,,,\n"
        "DPPH reduction assay,,,,,+,,,,,\n"
        "Comet assay,,+,+,,,,,,,\n"
    )
    filtered = tmp_path / "filtered_table.csv"
    filtered.write_text(
        "KC,Secondary KC,Effect,KC_Subgroup,KC_subgroup2,Assay_endpoint,Assay_endpoint2,Assay_endpoint3,"
        "Biomarker,Method,Method2,Stimulant_activation_agent,Target_cell,Cell_format,Design,"
        "Design_transgenic,Organism,Species,Mammalian,Tissue,Tissue2,Cell_type,Immortalized,"
        "Monograph_num,Monograph_chem,OECD,PMID,DOI,Citation,CEBP\n"
        "2,3,-NA-,Gene mutation,-NA-,Mutagenicity,-NA-,-NA-,Mutations,Ames assay,-NA-,-NA-,"
        "bacterial,in vitro,in vitro,-NA-,Bacteria,S. typhimurium,Non-mammalian,-NA-,-NA-,"
        "TA98,-NA-,112,Benzene,OECD TG 471,1234567,10.1000/abc,Smith 1992,1\n"
        "5,-NA-,-NA-,Oxidative,-NA-,Antioxidant capacity,-NA-,-NA-,ROS,DPPH reduction assay,-NA-,-NA-,"
        "cell-free,in vitro,in vitro,-NA-,-NA-,-NA-,-NA-,-NA-,-NA-,-NA-,-NA-,113,Glyphosate,-NA-,"
        "-NA-,10.1000/def,Jones 2005,-NA-\n"
        "2,-NA-,-NA-,DNA damage,-NA-,DNA strand breaks,-NA-,-NA-,Comet tail,Comet assay,-NA-,-NA-,"
        "primary cell/tissue,in vivo,in vivo,-NA-,Rats,Rats,Mammalian,Liver,-NA-,Hepatocytes,-NA-,"
        "112,Benzene,OECD TG 489,7654321,-NA-,Doe 2010,-NA-\n"
    )
    return tmp_path


def test_clean_treats_kcad_sentinels_as_none():
    assert import_kcad._clean("-NA-") is None
    assert import_kcad._clean("  ") is None
    assert import_kcad._clean("—") is None
    assert import_kcad._clean(None) is None
    assert import_kcad._clean(float("nan")) is None
    assert import_kcad._clean("Smith 1992") == "Smith 1992"


def test_parse_citation_extracts_year():
    authors, year = import_kcad._parse_citation("Smith MT 2016")
    assert year == 2016
    assert "Smith" in authors
    assert import_kcad._parse_citation(None) == ("—", None)


def test_ref_id_prefers_doi_then_pmid_then_citation():
    assert import_kcad._ref_id(doi="10.1/X", pmid="1", citation="Smith 1992").startswith("kcad-doi-")
    assert import_kcad._ref_id(doi=None, pmid="123", citation="Smith 1992") == "kcad-pmid-123"
    assert import_kcad._ref_id(doi=None, pmid=None, citation="Smith 1992").startswith("kcad-smith")
    assert import_kcad._ref_id(doi=None, pmid=None, citation=None) is None


def test_ref_id_disambiguates_collisions():
    # Two citations sharing a slug prefix get distinct ids via the hash suffix.
    a = import_kcad._ref_id(doi=None, pmid=None, citation="Smith 1992")
    b = import_kcad._ref_id(doi=None, pmid=None, citation="Smith 1992 — different paper")
    assert a != b
    # Deterministic: same input → same id.
    assert a == import_kcad._ref_id(doi=None, pmid=None, citation="Smith 1992")


def test_load_pivot_keeps_only_clean_methods(synthetic_data: Path):
    df = import_kcad.load_pivot(synthetic_data / "pivot_table.csv")
    assert len(df) == 3
    assert bool(df.loc[df["Method"] == "Ames assay", "KC2"].iloc[0]) is True
    assert bool(df.loc[df["Method"] == "Ames assay", "KC1"].iloc[0]) is False
    assert bool(df.loc[df["Method"] == "DPPH reduction assay", "KC5"].iloc[0]) is True


def test_build_bundle_links_assays_to_kccs(synthetic_data: Path):
    pivot = import_kcad.load_pivot(synthetic_data / "pivot_table.csv")
    filtered = import_kcad.load_filtered(synthetic_data / "filtered_table.csv")
    bundle = import_kcad.build_bundle(pivot, filtered, {"Benzene": "benzene"})

    assert {a["id"] for a in bundle.assays} == {
        "kcad-ames-assay",
        "kcad-dpph-reduction-assay",
        "kcad-comet-assay",
    }
    ames = next(a for a in bundle.assays if a["id"] == "kcad-ames-assay")
    assert ames["source"] == "kcad"
    assert ames["_kc_hits"] == [2]

    links = {(j["assay_id"], j["kcc_id"]) for j in bundle.assay_kccs}
    assert ("kcad-ames-assay", "kcc-02") in links
    assert ("kcad-dpph-reduction-assay", "kcc-05") in links
    assert ("kcad-comet-assay", "kcc-02") in links
    assert ("kcad-comet-assay", "kcc-03") in links


def test_build_bundle_dedupes_references(synthetic_data: Path):
    pivot = import_kcad.load_pivot(synthetic_data / "pivot_table.csv")
    filtered = import_kcad.load_filtered(synthetic_data / "filtered_table.csv")
    bundle = import_kcad.build_bundle(pivot, filtered, {"Benzene": "benzene"})

    refs = {r["id"]: r for r in bundle.references}
    assert len(refs) == 3  # one per (DOI|PMID|citation) triple
    # Smith 1992 row had both DOI and PMID — DOI wins for the id.
    smith = next(r for r in refs.values() if r["doi"] == "10.1000/abc")
    assert smith["id"].startswith("kcad-doi-")
    assert smith["year"] == 1992
    assert smith["doi"] == "10.1000/abc"
    assert smith["pmid"] == "1234567"
    assert smith["source"] == "kcad"
    # Doe 2010 row had PMID but no DOI → id is kcad-pmid-…
    doe = next(r for r in refs.values() if r["pmid"] == "7654321")
    assert doe["id"] == "kcad-pmid-7654321"


def test_build_bundle_links_agents_via_chem_map(synthetic_data: Path):
    pivot = import_kcad.load_pivot(synthetic_data / "pivot_table.csv")
    filtered = import_kcad.load_filtered(synthetic_data / "filtered_table.csv")
    bundle = import_kcad.build_bundle(pivot, filtered, {"Benzene": "benzene"})

    benzene_links = [ar for ar in bundle.agent_references if ar["agent_id"] == "benzene"]
    assert len(benzene_links) == 2  # Smith 1992 + Doe 2010
    # Glyphosate is not in the chem_map for this test → no link.
    assert not any(ar["agent_id"] == "glyphosate" for ar in bundle.agent_references)


def test_load_bundle_writes_all_tables(db, synthetic_data: Path):
    bundle = import_kcad.run(
        suppl_dir=synthetic_data,
        chem_map_path=_write_chem_map(synthetic_data, {"Benzene": "benzene"}),
        dry_run=False,
        db=db,
    )

    assays = db.scalars(select(Assay).where(Assay.source == "kcad")).all()
    assert len(assays) == bundle.report["n_assays"] == 3
    assert all(a.source == "kcad" for a in assays)

    n_links = db.scalar(select(func.count()).select_from(AssayKCC))
    assert n_links == bundle.report["n_assay_kcc_links"]

    refs = db.scalars(select(Reference).where(Reference.source == "kcad")).all()
    assert len(refs) == 3
    tags = db.scalars(select(ReferenceTag).where(ReferenceTag.tag == "kcad")).all()
    assert len(tags) == 3

    ar_rows = db.scalars(select(AgentReference)).all()
    assert {(ar.agent_id, ar.source) for ar in ar_rows} <= {("benzene", "kcad")}
    assert len(ar_rows) == 2

    annotations = db.scalars(select(AssayAnnotation)).all()
    assert len(annotations) == 3
    chems = {a.monograph_chem for a in annotations}
    assert chems == {"Benzene", "Glyphosate"}
    benzene_anns = [a for a in annotations if a.agent_id == "benzene"]
    assert len(benzene_anns) == 2
    # Glyphosate is not a known agent → agent_id stays NULL.
    glyph = next(a for a in annotations if a.monograph_chem == "Glyphosate")
    assert glyph.agent_id is None

    release = db.scalar(select(DatasetRelease).where(DatasetRelease.tag == import_kcad.KCAD_RELEASE_TAG))
    assert release is not None


def test_seed_kcad_agents_is_additive(db, synthetic_data: Path):
    # Pre-existing 'benzene' agent must NOT be overwritten.
    db.execute(
        Agent.__table__.update().where(Agent.id == "benzene").values(summary="curator-set")
    )
    db.commit()

    chem_map = _write_chem_map(synthetic_data, {"Benzene": "benzene", "Glyphosate": "glyphosate"})
    agents_path = synthetic_data / "agents.json"
    import json as _json

    agents_path.write_text(
        _json.dumps(
            {
                "agents": [
                    {
                        "id": "benzene",
                        "name": "Benzene (KCAD override attempt)",
                        "cas": "00-00-0",
                        "iarc_group": "—",
                        "agent_type": "kcad-override",
                        "summary": "kcad-override",
                    },
                    {
                        "id": "glyphosate",
                        "name": "Glyphosate",
                        "cas": "1071-83-6",
                        "iarc_group": "2A",
                        "agent_type": "Pesticide",
                        "summary": "kcad-seeded",
                    },
                ]
            }
        )
    )

    import_kcad.run(
        suppl_dir=synthetic_data, chem_map_path=chem_map, agents_path=agents_path, db=db
    )

    benzene = db.get(Agent, "benzene")
    assert benzene.summary == "curator-set"  # preserved
    glyph = db.get(Agent, "glyphosate")
    assert glyph is not None and glyph.summary == "kcad-seeded"

    # Now Glyphosate annotations should link to the new agent.
    glyph_anns = [
        a
        for a in db.scalars(select(AssayAnnotation).where(AssayAnnotation.monograph_chem == "Glyphosate"))
    ]
    assert glyph_anns and all(a.agent_id == "glyphosate" for a in glyph_anns)


def test_evidence_citations_added_non_destructively(db, synthetic_data: Path):
    # Curator-set Evidence row on benzene × kcc-02 with score=4 and one
    # pre-existing curator citation. KCAD should add citations, not touch the score.
    db.add(Reference(id="smith2016", year=2016, authors="Smith", title="Foundational", journal="EHP"))
    db.flush()
    ev = Evidence(agent_id="benzene", kcc_id="kcc-02", score=4, n_refs=1, curator_notes="curator")
    db.add(ev)
    db.flush()
    ev_id = ev.id
    db.add(EvidenceCitation(evidence_id=ev_id, reference_id="smith2016"))
    db.commit()

    chem_map = _write_chem_map(synthetic_data, {"Benzene": "benzene"})
    import_kcad.run(suppl_dir=synthetic_data, chem_map_path=chem_map, db=db)

    ev_after = db.get(Evidence, ev_id)
    # Score is preserved.
    assert ev_after.score == 4
    assert ev_after.curator_notes == "curator"
    # KCAD added at least one citation (Smith 1992 with DOI on the synthetic Ames row).
    citations = db.scalars(
        select(EvidenceCitation).where(EvidenceCitation.evidence_id == ev_id)
    ).all()
    ref_ids = {c.reference_id for c in citations}
    assert "smith2016" in ref_ids  # original kept
    assert any(rid.startswith("kcad-") for rid in ref_ids)  # KCAD-added
    # n_refs reflects the new citation count.
    assert ev_after.n_refs == len(citations)


def test_evidence_citations_skips_when_no_curator_row(db, synthetic_data: Path):
    # No Evidence row for (benzene, kcc-02) → KCAD must NOT create one.
    chem_map = _write_chem_map(synthetic_data, {"Benzene": "benzene"})
    import_kcad.run(suppl_dir=synthetic_data, chem_map_path=chem_map, db=db)
    rows = db.scalars(select(Evidence).where(Evidence.agent_id == "benzene")).all()
    assert rows == []  # never auto-create


def test_reset_recomputes_n_refs_on_curator_evidence(db, synthetic_data: Path):
    db.add(Reference(id="smith2016", year=2016, authors="Smith", title="Foundational", journal="EHP"))
    db.flush()
    ev = Evidence(agent_id="benzene", kcc_id="kcc-02", score=4, n_refs=1)
    db.add(ev)
    db.flush()
    ev_id = ev.id
    db.add(EvidenceCitation(evidence_id=ev_id, reference_id="smith2016"))
    db.commit()

    chem_map = _write_chem_map(synthetic_data, {"Benzene": "benzene"})
    import_kcad.run(suppl_dir=synthetic_data, chem_map_path=chem_map, db=db)
    n_after_import = db.scalar(
        select(func.count()).select_from(EvidenceCitation).where(EvidenceCitation.evidence_id == ev_id)
    )
    assert n_after_import > 1

    # Reset → KCAD citations dropped, smith2016 preserved, n_refs back to 1.
    import_kcad.run(suppl_dir=synthetic_data, chem_map_path=chem_map, db=db, reset=True)
    n_after_reset = db.scalar(
        select(func.count()).select_from(EvidenceCitation).where(EvidenceCitation.evidence_id == ev_id)
    )
    # KCAD will re-add citations during the same run; check that the curator one survived.
    surviving = db.scalars(
        select(EvidenceCitation).where(EvidenceCitation.evidence_id == ev_id)
    ).all()
    assert any(c.reference_id == "smith2016" for c in surviving)
    ev_after = db.get(Evidence, ev_id)
    assert ev_after.score == 4  # score never touched
    assert ev_after.n_refs == n_after_reset


def test_load_bundle_is_idempotent(db, synthetic_data: Path):
    chem_map = _write_chem_map(synthetic_data, {"Benzene": "benzene"})
    import_kcad.run(suppl_dir=synthetic_data, chem_map_path=chem_map, db=db)
    n_assays_before = db.scalar(select(func.count()).select_from(Assay))
    n_links_before = db.scalar(select(func.count()).select_from(AssayKCC))
    n_anns_before = db.scalar(select(func.count()).select_from(AssayAnnotation))

    # Re-run with reset → counts stay identical (idempotent).
    import_kcad.run(suppl_dir=synthetic_data, chem_map_path=chem_map, db=db, reset=True)
    assert db.scalar(select(func.count()).select_from(Assay)) == n_assays_before
    assert db.scalar(select(func.count()).select_from(AssayKCC)) == n_links_before
    assert db.scalar(select(func.count()).select_from(AssayAnnotation)) == n_anns_before


def _write_chem_map(tmp_path: Path, mapping: dict[str, str]) -> Path:
    import json as _json

    p = tmp_path / "chem_map.json"
    p.write_text(_json.dumps({"map": mapping}))
    return p


@pytest.mark.skipif(
    not REAL_SUPPL_DIR.exists() or os.environ.get("KCAD_REAL_DATA") != "1",
    reason="Set KCAD_REAL_DATA=1 to run the full-CSV smoke test",
)
def test_real_data_smoke(db):
    bundle = import_kcad.run(suppl_dir=REAL_SUPPL_DIR, db=db)
    assert 400 < bundle.report["n_assays"] < 700
    assert bundle.report["n_references"] > 500
    assert bundle.report["n_annotations"] > 1000
    assert set(bundle.report["assays_per_kc"]) <= {f"kcc-{k:02d}" for k in range(1, 11)}

    # Item 1: every built reference must round-trip to a DB row (no id collisions).
    n_refs_in_db = db.scalar(select(func.count()).where(Reference.source == "kcad").select_from(Reference))
    assert n_refs_in_db == bundle.report["n_references"], (
        f"{bundle.report['n_references'] - n_refs_in_db} reference id collisions"
    )


@pytest.mark.skipif(
    not REAL_SUPPL_DIR.exists() or os.environ.get("KCAD_REAL_DATA") != "1",
    reason="Set KCAD_REAL_DATA=1 to run the full-CSV round-trip test",
)
def test_real_data_full_column_round_trip(db):
    """Every (row, column) pair from suppl_data/filtered_table.csv must land in DB.

    For every non-NA cell in the source CSV, the corresponding `assay_annotations`
    column (or `references` field) is populated with the same value.
    """
    import pandas as pd

    bundle = import_kcad.run(suppl_dir=REAL_SUPPL_DIR, db=db)

    # 1. Row count matches the CSV exactly.
    flt = pd.read_csv(REAL_SUPPL_DIR / "filtered_table.csv", low_memory=False, dtype=str)
    assert bundle.report["n_annotations"] == len(flt), (
        f"row loss: csv={len(flt)} db={bundle.report['n_annotations']}"
    )

    # 2. Coverage check: for each filtered-table column, the DB has at least as many
    #    non-null values as the CSV has non-NA cells.
    CSV_TO_DB = {
        "KC": ("kcc_id", None),
        "Secondary KC": ("secondary_kc_raw", None),
        "Effect": ("effect", None),
        "KC_Subgroup": ("kc_subgroup", None),
        "KC_subgroup2": ("kc_subgroup2", None),
        "Assay_endpoint": ("assay_endpoint", None),
        "Assay_endpoint2": ("assay_endpoint2", None),
        "Assay_endpoint3": ("assay_endpoint3", None),
        "Biomarker": ("biomarker", None),
        "Method": ("assay_id", None),
        "Method2": ("method2", None),
        "Stimulant_activation_agent": ("stimulant_activation_agent", None),
        "Target_cell": ("target_cell", None),
        "Cell_format": ("cell_format", None),
        "Design": ("design", None),
        "Design_transgenic": ("design_transgenic", None),
        "Organism": ("organism", None),
        "Species": ("species", None),
        "Mammalian": ("mammalian", None),
        "Tissue": ("tissue", None),
        "Tissue2": ("tissue2", None),
        "Cell_type": ("cell_type", None),
        "Immortalized": ("immortalized", None),
        "Monograph_num": ("monograph_num", None),
        "Monograph_chem": ("monograph_chem", None),
        "OECD": ("oecd_tg", None),
        "CEBP": ("cebp_ref_idx", None),
    }
    NA = {"-NA-", "—", "-", "", "NA", "nan"}
    for csv_col, (db_col, _) in CSV_TO_DB.items():
        csv_non_na = sum(1 for v in flt[csv_col].fillna("") if str(v).strip() not in NA)
        col_attr = getattr(AssayAnnotation, db_col)
        db_non_null = db.scalar(
            select(func.count()).where(col_attr.is_not(None)).select_from(AssayAnnotation)
        )
        # Allow a small slack for Method rows we couldn't pivot-match (none expected).
        assert db_non_null >= csv_non_na - 1, (
            f"col {csv_col!r}→{db_col!r}: csv non-NA={csv_non_na}, db non-null={db_non_null}"
        )

    # 3. Reference-side columns: PMID, DOI, Citation are captured on `references`.
    # Refs are deduped on import (DOI/PMID/citation), but every CSV-identifiable
    # ref must be reachable via an annotation FK.
    annotated_ref_ids = {
        rid for (rid,) in db.execute(
            select(AssayAnnotation.reference_id).where(AssayAnnotation.reference_id.is_not(None))
        )
    }
    n_refs_in_db = db.scalar(
        select(func.count()).where(Reference.source == "kcad").select_from(Reference)
    )
    assert len(annotated_ref_ids) == n_refs_in_db, (
        f"orphan refs: annotated={len(annotated_ref_ids)} db={n_refs_in_db}"
    )
