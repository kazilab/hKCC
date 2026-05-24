"""Tests for the IARC 10-year retrospective KCC importer.

Two layers:

* Unit tests on small synthetic Excel files exercise the per-block parser,
  the metadata-label detector, and the dual-track aggregator.
* A single real-data smoke test (gated by ``KCC10YR_REAL_DATA=1``) verifies
  end-to-end parsing of the actual Rusyn 2024 supplementary files.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.models import (
    KCC,
    Agent,
    Base,
    Evidence,
    EvidenceCitation,
    IarcMonographKcCall,
    IarcMonographKcStrength,
    Reference,
    ReferenceTag,
)
from pipelines import import_10yr_kcc as p10

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_FILE012 = (
    REPO_ROOT
    / "references"
    / "kcc-10yr"
    / "kfad134_Supplementary_Data"
    / "toxsci-23-0374-File012.xlsx"
)
REAL_FILE014 = (
    REPO_ROOT
    / "references"
    / "kcc-10yr"
    / "kfad134_Supplementary_Data"
    / "toxsci-23-0374-File014.xlsx"
)

KC_COLS = [
    "1.Is electrophilic or can be metabolically activated",
    "2. Is genotoxic",
    "3.Alters DNA repair or causes genomic instability",
    "4.Induces epigenetic alterations",
    "5.Induces oxidative stress",
    "6.Induces chronic inflammation",
    "7.Is immunosuppressive",
    "8.Modulates receptor-mediated effects",
    "9.Causes immortalization",
    "10.Alters cell proliferation, cell death or nutrient supply",
]
MODEL_ROWS = [
    "Exposed Humans",
    "Human cells in vitro",
    "Mammalian in vivo",
    "Mammalian in vitro",
    "Other in vivo",
    "Other in vitro",
    "ToxCast data",
    "ToxRefDB data",
    "Overall strength",
]


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
    db.commit()
    yield db
    db.close()


# ─── helpers to build synthetic File012 / File014 fixtures ───────────────────


def _build_agent_block(agent: str, iarc_group: str, calls: dict[str, list[str]]):
    """Construct a list of [agent_col, model_col, KC1..KC10] rows for one agent.

    ``calls`` maps model_system label → 10-element list of cell strings (or "" for blank).
    The IARC group label is placed in the Agent column on the Mammalian in vivo row.
    """
    rows: list[list[str]] = []
    for i, ms in enumerate(MODEL_ROWS):
        if i == 0:
            agent_col_val = agent
        elif ms == "Mammalian in vivo":
            agent_col_val = iarc_group
        else:
            agent_col_val = ""
        kc_vals = calls.get(ms, [""] * 10)
        assert len(kc_vals) == 10
        rows.append([agent_col_val, ms, *kc_vals])
    rows.append(["", "", *[""] * 10])  # separator row
    return rows


def _write_synth_file012(path: Path) -> None:
    """Write a 2-sheet synthetic File012 with deterministic content for tests."""
    cols = ["Agent", "Model system", *KC_COLS]

    # Vol 120 (2017): one agent "Benzene" — convergent Yes across primary systems
    benzene_rows = _build_agent_block(
        agent="Benzene",
        iarc_group="1",
        calls={
            "Exposed Humans":       ["Yes", "Yes", "Yes", "Yes", "Yes", "", "Yes", "", "", ""],
            "Human cells in vitro": ["Yes", "Yes", "Yes", "Yes", "Yes", "", "Yes", "", "", ""],
            "Mammalian in vivo":    ["Yes", "Yes", "Yes", "", "Yes", "", "Yes", "", "", ""],
            "Mammalian in vitro":   ["",    "Yes", "",    "",    "Yes", "", "",    "", "", ""],
            "Other in vivo":        ["",    "",    "",    "",    "",    "", "",    "", "", ""],
            "Other in vitro":       ["",    "",    "",    "",    "",    "", "",    "", "", ""],
            "ToxCast data":         ["",    "",    "",    "",    "",    "", "",    "", "", ""],
            "ToxRefDB data":        ["",    "",    "",    "",    "",    "", "",    "", "", ""],
            "Overall strength":     ["Strong", "Strong", "Strong", "", "Strong", "", "Strong", "", "", ""],
        },
    )

    # Vol 116 (2016): "Drinking Coffee" — Protective for KC5/KC6, mostly Equivocal otherwise
    coffee_rows = _build_agent_block(
        agent="Drinking Coffee",
        iarc_group="3",
        calls={
            "Exposed Humans":       ["", "Equivocal", "", "", "Protective", "", "", "", "", ""],
            "Human cells in vitro": ["", "Equivocal", "", "Yes", "Protective", "Protective", "", "", "", ""],
            "Mammalian in vivo":    ["", "Equivocal", "Yes", "Yes", "", "", "", "", "", ""],
            "Mammalian in vitro":   ["", "Equivocal", "", "", "", "", "", "", "", ""],
            "Other in vivo":        ["", "", "", "", "", "", "", "", "", ""],
            "Other in vitro":       ["", "", "", "", "", "", "", "", "", ""],
            "ToxCast data":         ["", "Equivocal", "", "", "", "", "", "", "", ""],
            "ToxRefDB data":        ["", "", "", "", "", "", "", "", "", ""],
            "Overall strength":     ["", "Weak", "", "", "Weak", "", "", "", "", ""],
        },
    )

    df_vol120 = pd.DataFrame(benzene_rows, columns=cols)
    df_vol116 = pd.DataFrame(coffee_rows, columns=cols)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_vol120.to_excel(writer, sheet_name="Volume 120 (2017)", index=False)
        df_vol116.to_excel(writer, sheet_name="Volume 116 (2016)", index=False)


def _write_synth_file014(path: Path) -> None:
    """Write Supp Table 4 with a few rows of standardized strength data."""
    cols = ["Agent", "Group", "Mechanistic data role", *[f"KC{i}" for i in range(1, 11)]]
    # First row of the real file is a title row before the actual headers.
    title_row = ["Supplemental Table 4. Standardized terms", *([""] * (len(cols) - 1))]
    rows = [
        title_row,
        cols,
        ["Benzene", "1", "Supportive", "Strong", "Strong", "Strong", "", "Strong", "", "Strong", "", "", ""],
        ["Drinking Coffee", "3", "Not used", "", "Weak", "", "", "Weak", "Weak", "", "", "", ""],
    ]
    df = pd.DataFrame(rows)
    df.to_excel(path, header=False, index=False)


# ─── unit tests ──────────────────────────────────────────────────────────────


def test_metadata_label_detection():
    """The Agent-column metadata-label detector must not eat real agent names."""
    assert p10._is_metadata_label("2A") is True
    assert p10._is_metadata_label("1") is True
    assert p10._is_metadata_label("H-Limited") is True
    assert p10._is_metadata_label("A-Sufficient") is True
    assert p10._is_metadata_label("M-Supportive") is True
    assert p10._is_metadata_label("M-not used") is True
    # Real agent names (uppercase abbreviations or proper names) must pass through.
    assert p10._is_metadata_label("Benzene") is False
    assert p10._is_metadata_label("Drinking Coffee") is False
    assert p10._is_metadata_label("DDT") is False
    assert p10._is_metadata_label("1,1,1-Trichloroethane") is False


def test_norm_call_recognises_protective_synonyms():
    assert p10._norm_call("Yes") == ("Yes", "Yes")
    assert p10._norm_call("No") == ("No", "No")
    assert p10._norm_call("Equivocal") == ("Equivocal", "Equivocal")
    assert p10._norm_call("Protective") == ("Protective", "Protective")
    # Synonyms collapse to "Protective" but keep raw label.
    assert p10._norm_call("Antioxidant") == ("Protective", "Antioxidant")
    assert p10._norm_call("Antiinflammatory") == ("Protective", "Antiinflammatory")
    # Blank / unknown.
    assert p10._norm_call("")[0] is None
    assert p10._norm_call("Maybe")[0] is None


def test_parse_sheet_meta_handles_typo():
    """The source file has 'Volune 121 (2018)' — must still extract 121/2018."""
    assert p10._parse_sheet_meta("Volume 120 (2017)") == ("120", 2017)
    assert p10._parse_sheet_meta("Volune 121 (2018)") == ("121", 2018)


def test_parse_file012_synthetic(tmp_path: Path):
    path = tmp_path / "synth_file012.xlsx"
    _write_synth_file012(path)

    calls, vol_strengths, agent_meta = p10.parse_file012(path)

    # Two agents, both reach the parser with correct IARC group.
    assert set(agent_meta) == {"Benzene", "Drinking Coffee"}
    assert agent_meta["Benzene"]["iarc_group"] == "1"
    assert agent_meta["Drinking Coffee"]["iarc_group"] == "3"

    # Benzene KC1 has 3 Yes calls across primary systems → drives score 4.
    benzene_kc1_primary = [
        c for c in calls
        if c["agent_name"] == "Benzene"
        and c["kc_num"] == 1
        and c["model_system"] in p10.PRIMARY_MODEL_SYSTEMS
    ]
    yes_count = sum(1 for c in benzene_kc1_primary if c["call"] == "Yes")
    assert yes_count == 3

    # Drinking Coffee KC5 has Protective calls across systems.
    coffee_kc5 = [c for c in calls if c["agent_name"] == "Drinking Coffee" and c["kc_num"] == 5]
    assert all(c["call"] == "Protective" for c in coffee_kc5)

    # Overall-strength rows surface.
    vs_benzene_kc1 = [
        v for v in vol_strengths if v["agent_name"] == "Benzene" and v["kc_num"] == 1
    ]
    assert len(vs_benzene_kc1) == 1
    assert vs_benzene_kc1[0]["strength_label"] == "Strong"
    assert vs_benzene_kc1[0]["monograph_volume"] == "120"


def test_parse_file014_synthetic(tmp_path: Path):
    path = tmp_path / "synth_file014.xlsx"
    _write_synth_file014(path)
    rows = p10.parse_file014(path)
    by_pair = {(r["agent_name"], r["kc_num"]): r for r in rows}
    assert by_pair[("Benzene", 1)]["strength_label"] == "Strong"
    assert by_pair[("Benzene", 1)]["data_role"] == "Supportive"
    assert by_pair[("Drinking Coffee", 5)]["strength_label"] == "Weak"
    assert by_pair[("Drinking Coffee", 5)]["data_role"] == "Not used"


def test_aggregate_evidence_primary_track(tmp_path: Path):
    """File014 strengths must dominate calls when both are present."""
    file012 = tmp_path / "f12.xlsx"
    file014 = tmp_path / "f14.xlsx"
    _write_synth_file012(file012)
    _write_synth_file014(file014)

    calls, _, _ = p10.parse_file012(file012)
    strengths = p10.parse_file014(file014)

    # Both Benzene and Drinking Coffee exist in our fake DB
    agent_index = {p10._fold("Benzene"): "benzene", p10._fold("Drinking Coffee"): "drinking-coffee"}
    ev = p10.aggregate_evidence(calls, strengths, agent_index)
    by_key = {(r["agent_id"], r["kcc_id"]): r for r in ev}

    # Benzene KC1: File014 says Strong → score 4 (paper aggregate dominates)
    assert by_key[("benzene", "kcc-01")]["score"] == 4
    assert "File014 standardized strength = Strong" in by_key[("benzene", "kcc-01")]["curator_notes"]

    # Drinking Coffee KC5: File014 says Weak → score 2 (NOT 0 from Protective calls)
    assert by_key[("drinking-coffee", "kcc-05")]["score"] == 2
    assert "File014 standardized strength = Weak" in by_key[("drinking-coffee", "kcc-05")]["curator_notes"]


def test_aggregate_evidence_fallback_track(tmp_path: Path):
    """Without File014, score derives from primary-system Yes counts."""
    file012 = tmp_path / "f12.xlsx"
    _write_synth_file012(file012)
    calls, _, _ = p10.parse_file012(file012)

    agent_index = {p10._fold("Benzene"): "benzene", p10._fold("Drinking Coffee"): "drinking-coffee"}
    ev = p10.aggregate_evidence(calls, [], agent_index)
    by_key = {(r["agent_id"], r["kcc_id"]): r for r in ev}

    # Benzene KC1 has 3 Yes across primary systems → score 4
    assert by_key[("benzene", "kcc-01")]["score"] == 4
    # Drinking Coffee KC4 has 2 Yes (Human cells + Mammalian in vivo) → score 3
    assert by_key[("drinking-coffee", "kcc-04")]["score"] == 3
    # Drinking Coffee KC5 has only Protective calls (no Yes/Equivocal) → score 0
    assert by_key[("drinking-coffee", "kcc-05")]["score"] == 0
    assert "Protective" in by_key[("drinking-coffee", "kcc-05")]["curator_notes"]
    # Drinking Coffee KC2 has only Equivocal calls → score 1
    assert by_key[("drinking-coffee", "kcc-02")]["score"] == 1


# ─── end-to-end DB load tests ────────────────────────────────────────────────


def test_full_load_into_db(tmp_path: Path, db, monkeypatch):
    """Full integration: build bundle, load into DB, verify rows + idempotency."""
    file012 = tmp_path / "f12.xlsx"
    file014 = tmp_path / "f14.xlsx"
    _write_synth_file012(file012)
    _write_synth_file014(file014)

    # Pre-seed Benzene only; Drinking Coffee should be auto-inserted as a stub.
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

    p10.run(file012=file012, file014=file014, dry_run=False, reset=True, db=db)
    db.expire_all()

    # 1. Rusyn 2024 reference seeded with pdf_path.
    rusyn = db.get(Reference, p10.KCC10YR_REF_ID)
    assert rusyn is not None
    assert rusyn.doi == p10.KCC10YR_DOI
    assert rusyn.pdf_path == "references/kcc-10yr/KCC-10yr.pdf"
    assert rusyn.url and "doi.org" in rusyn.url

    # 2. Reference tags applied (Retrospective / IARC-Monographs).
    tags = {
        t for (t,) in db.execute(
            select(ReferenceTag.tag).where(ReferenceTag.reference_id == p10.KCC10YR_REF_ID)
        )
    }
    assert "Retrospective" in tags
    assert "IARC-Monographs" in tags

    # 3. Drinking Coffee agent stub inserted with paper provenance.
    coffee = db.scalar(select(Agent).where(Agent.name == "Drinking Coffee"))
    assert coffee is not None
    assert coffee.source_ref_id == p10.KCC10YR_REF_ID
    assert coffee.iarc_group == "3"
    assert coffee.monograph_volume == "116"

    # 4. iarc_monograph_kc_calls populated with all 8 model systems + Overall strength.
    distinct_ms = {
        ms for (ms,) in db.execute(select(IarcMonographKcCall.model_system).distinct())
    }
    expected_ms = set(p10.MODEL_SYSTEMS) | {p10.OVERALL_STRENGTH_LABEL}
    # In this synthetic only some MSs have non-blank cells, but at least one of each
    # category should appear.
    assert distinct_ms <= expected_ms
    assert "Mammalian in vivo" in distinct_ms
    assert p10.OVERALL_STRENGTH_LABEL in distinct_ms

    # 5. Protective calls preserved verbatim in raw_call.
    coffee_prot = db.execute(
        select(IarcMonographKcCall).where(
            IarcMonographKcCall.agent_id == coffee.id,
            IarcMonographKcCall.call == "Protective",
        )
    ).scalars().all()
    assert coffee_prot
    assert all(r.raw_call == "Protective" for r in coffee_prot)

    # 6. iarc_monograph_kc_strength populated from File014 paper-aggregate.
    benzene_kc1_strength = db.execute(
        select(IarcMonographKcStrength).where(
            IarcMonographKcStrength.agent_id == "benzene",
            IarcMonographKcStrength.kcc_id == "kcc-01",
        )
    ).scalar_one()
    assert benzene_kc1_strength.strength_label == "Strong"
    assert benzene_kc1_strength.data_role == "Supportive"

    # 7. Evidence aggregator: Benzene KC1 → 4 (Strong); Coffee KC5 → 2 (Weak per File014).
    ev_benz = db.execute(
        select(Evidence).where(Evidence.agent_id == "benzene", Evidence.kcc_id == "kcc-01")
    ).scalar_one()
    assert ev_benz.score == 4
    assert ev_benz.curator_notes.startswith("[10yr-iarc]")

    ev_coffee_5 = db.execute(
        select(Evidence).where(Evidence.agent_id == coffee.id, Evidence.kcc_id == "kcc-05")
    ).scalar_one()
    assert ev_coffee_5.score == 2  # File014 = Weak

    # 8. EvidenceCitation links exist for every 10yr Evidence row.
    n_citations = db.scalar(
        select(EvidenceCitation).join(Evidence).where(Evidence.curator_notes.like("[10yr-iarc]%")).limit(1)
    )
    assert n_citations is not None

    # 9. Idempotent re-run: row counts must NOT double.
    p10.run(file012=file012, file014=file014, dry_run=False, reset=True, db=db)
    db.expire_all()
    calls_after_count = len(db.execute(select(IarcMonographKcCall)).scalars().all())
    n_synth_calls, n_synth_overall = _synthetic_count(file012)
    # After reset the row count should equal the synthetic call count, not 2× of it.
    assert calls_after_count == n_synth_calls + n_synth_overall


def _synthetic_count(path: Path) -> tuple[int, int]:
    """Return (n_call_cells, n_volume_strength_cells) the synthetic file holds."""
    calls, vs, _ = p10.parse_file012(path)
    return len(calls), len(vs)


def test_existing_curator_evidence_not_overwritten(tmp_path: Path, db):
    """A curator-scored Evidence row must survive a 10yr re-import."""
    file012 = tmp_path / "f12.xlsx"
    file014 = tmp_path / "f14.xlsx"
    _write_synth_file012(file012)
    _write_synth_file014(file014)

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
    # Curator-scored row sans [10yr-iarc] sentinel.
    db.add(
        Evidence(
            agent_id="benzene",
            kcc_id="kcc-01",
            score=2,
            n_refs=1,
            curator_notes="Curator override: only one in vivo system.",
        )
    )
    db.commit()

    p10.run(file012=file012, file014=file014, dry_run=False, reset=True, db=db)
    db.expire_all()

    ev = db.execute(
        select(Evidence).where(Evidence.agent_id == "benzene", Evidence.kcc_id == "kcc-01")
    ).scalar_one()
    assert ev.score == 2  # Curator value preserved
    assert ev.curator_notes.startswith("Curator override")


# ─── real-file smoke test ────────────────────────────────────────────────────


@pytest.mark.skipif(
    os.environ.get("KCC10YR_REAL_DATA") != "1" or not REAL_FILE012.is_file(),
    reason="Set KCC10YR_REAL_DATA=1 + ensure references/ exists to run the real-file smoke test.",
)
def test_smoke_real_files():
    bundle = p10.build_bundle(file012=REAL_FILE012, file014=REAL_FILE014)
    r = bundle.report
    # Numbers verified against the source files manually:
    assert r["n_unique_agents"] == 73
    assert r["n_call_cells"] >= 1000
    assert r["n_paper_strength_cells"] == 250
    assert set(r["volumes"]) >= {str(v) for v in range(112, 131)}
    assert set(r["calls_per_model_system"]) == set(p10.MODEL_SYSTEMS)
    # Both Benzene and Drinking Coffee must surface.
    assert "Benzene" in bundle.agents_seen
    assert "Drinking Coffee" in bundle.agents_seen
    assert bundle.agents_seen["Benzene"]["iarc_group"] == "1"
    # Coffee Protective cells must be preserved.
    coffee_prot = [
        c for c in bundle.calls
        if c["agent_name"] == "Drinking Coffee" and c["call"] == "Protective"
    ]
    assert coffee_prot, "expected Drinking Coffee Protective cells in Vol 116"
