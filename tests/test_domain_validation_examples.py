"""Simulation-derived validation examples are guidance, never evidence.

The four EMD systems models produce statements about what a measurement cannot
settle and what would settle it. Those are useful to an annotator and dangerous
to a weight-of-evidence count: the observations used to constrain a model are
already scored on Layer 1, so counting the model's output again would
double-count them. The separation is structural — no ``score`` column, no
foreign key from ``evidence`` — and these tests are what keep it structural.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect

from hkcc.db.models import (
    VALIDATION_EVIDENTIARY_STATUS,
    CandidateDomain,
    CandidateDomainKCC,
    CandidateDomainValidationExample,
    Evidence,
)
from hkcc.db.session import SessionLocal
from hkcc.pipelines.migrate_domain_validation_examples import (
    EXAMPLES,
    SOURCE_REF,
    default_db,
    diff,
    validate,
)

TABLE = "candidate_domain_validation_examples"


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


# --------------------------------------------------------------- schema -----

def test_table_ships_in_the_database(db):
    assert TABLE in sa_inspect(db.bind).get_table_names()


def test_no_score_anywhere_in_the_feature(db):
    """The whole point. A score here would make a model result a positive."""
    columns = {c["name"] for c in sa_inspect(db.bind).get_columns(TABLE)}
    assert "score" not in columns
    assert not {c for c in columns if "score" in c}, f"score-like column: {columns}"

    from hkcc.api.schemas import DomainValidationExampleOut

    assert "score" not in DomainValidationExampleOut.model_fields
    assert "score" not in {c.key for c in sa_inspect(CandidateDomainValidationExample).columns}


def test_evidence_has_no_link_to_validation_examples(db):
    """A foreign key here would be the back door the missing score column closes."""
    fks = sa_inspect(db.bind).get_foreign_keys("evidence")
    assert not [fk for fk in fks if fk["referred_table"] == TABLE]


# ------------------------------------------------------------- integrity ----

def test_every_emd_has_examples_and_cd5_has_none(db):
    """Per-domain counts, deliberately not an exact total.

    A hard total ("exactly 13") turns every future example into a failing test
    in an unrelated file. What must hold is that the four manuscript domains are
    covered and CD5 — outside the simulation paper's scope — carries nothing
    fabricated.
    """
    counts = dict(
        db.execute(
            select(CandidateDomainValidationExample.domain_id, func.count())
            .group_by(CandidateDomainValidationExample.domain_id)
        ).all()
    )
    for code in ("emd1", "emd2", "emd3", "emd4"):
        assert counts.get(code, 0) >= 1, f"{code} has no validation examples"
    assert counts.get("cd5", 0) == 0, "CD5 has no simulation; examples for it would be invented"


def test_every_example_annotates_an_existing_domain_kcc_link(db):
    """An example annotates a relation; it must not imply a new one."""
    links = {(d, k) for d, k in db.execute(select(CandidateDomainKCC.domain_id, CandidateDomainKCC.kcc_id))}
    orphans = [
        (v.id, v.domain_id, v.kcc_id)
        for v in db.scalars(select(CandidateDomainValidationExample))
        if v.kcc_id is not None and (v.domain_id, v.kcc_id) not in links
    ]
    assert not orphans, f"examples pointing at non-existent domain/KCC links: {orphans}"


def test_domain_ids_and_kcc_ids_resolve(db):
    domains = {d.id for d in db.scalars(select(CandidateDomain))}
    from hkcc.db.models import KCC

    kccs = {k.id for k in db.scalars(select(KCC))}
    for v in db.scalars(select(CandidateDomainValidationExample)):
        assert v.domain_id in domains, f"{v.id}: unknown domain {v.domain_id}"
        assert v.kcc_id is None or v.kcc_id in kccs, f"{v.id}: unknown KCC {v.kcc_id}"


def test_sort_order_is_unique_and_positive_within_a_domain(db):
    seen: dict[tuple[str, int], str] = {}
    for v in db.scalars(select(CandidateDomainValidationExample)):
        assert v.sort_order > 0, f"{v.id}: sort_order must be positive"
        key = (v.domain_id, v.sort_order)
        assert key not in seen, f"{v.id} collides with {seen[key]} on {key}"
        seen[key] = v.id


def test_evidentiary_status_is_a_closed_vocabulary(db):
    """Free text would make the 'not a strength scale' rule unenforceable."""
    bad = [
        (v.id, v.evidentiary_status)
        for v in db.scalars(select(CandidateDomainValidationExample))
        if v.evidentiary_status not in VALIDATION_EVIDENTIARY_STATUS
    ]
    assert not bad, f"statuses outside the vocabulary: {bad}"


def test_provenance_is_the_simulation_paper_not_the_framework_paper(db):
    """`kazi2026-emd` proposes the domains; a different paper tests them."""
    from hkcc.db.models import Reference

    refs = {v.source_ref_id for v in db.scalars(select(CandidateDomainValidationExample))}
    assert refs == {SOURCE_REF["id"]}, f"unexpected sources: {refs}"

    ref = db.get(Reference, SOURCE_REF["id"])
    assert ref is not None, "the simulation-paper reference is missing"
    assert ref.doi is None and ref.pmid is None, "a manuscript record must not carry an invented id"
    assert ref.journal == "Manuscript"


def test_every_example_says_what_would_settle_the_question(db):
    """An example without a discriminator is an objection, not guidance."""
    for v in db.scalars(select(CandidateDomainValidationExample)):
        for field in ("alternative_explanation", "insufficient_measurement",
                      "discriminating_measurement", "simulation_finding",
                      "annotation_implication"):
            assert (getattr(v, field) or "").strip(), f"{v.id}: empty {field}"


# --------------------------------------------------- scientific guardrails --

def test_emd4_kcc9_stays_contrastive(db):
    """The example defending this polarity is worthless if the link drifts."""
    rel = db.scalar(
        select(CandidateDomainKCC.relation).where(
            CandidateDomainKCC.domain_id == "emd4", CandidateDomainKCC.kcc_id == "kcc-09"
        )
    )
    assert rel == "contrastive"


def test_emd3_kcc9_is_not_a_home(db):
    """The EMD3 simulation is why: immortal reachability is zero in every arm.

    `home` means "the KCC an observation files under, in essentially every
    instance of the domain". For EMD3-KCC9 the model says no instance — the
    immortal basin moves with exposure while reachability does not. `downstream`
    keeps the link (stem-like transitions can reach KCC9 with their own readout)
    without filing stem markers there by default. It is deliberately not
    `contrastive`: that is opposing polarity, which is EMD4's relation, not this.
    """
    rel = db.scalar(
        select(CandidateDomainKCC.relation).where(
            CandidateDomainKCC.domain_id == "emd3", CandidateDomainKCC.kcc_id == "kcc-09"
        )
    )
    assert rel == "downstream", f"EMD3-KCC9 is {rel!r}; see emd3-val-04 and EMD3 checks V3/V15"


def test_the_kcc9_examples_are_present_and_say_opposite_things(db):
    """EMD3 and EMD4 both touch KCC9 for different reasons; both are recorded."""
    by_id = {v.id: v for v in db.scalars(select(CandidateDomainValidationExample))}
    assert by_id["emd3-val-04"].kcc_id == "kcc-09"
    assert by_id["emd4-val-03"].kcc_id == "kcc-09"


def test_migration_does_not_touch_evidence(db):
    """Run the seed against a copy and prove `evidence` is byte-identical."""
    import shutil
    import tempfile
    from pathlib import Path

    from hkcc.pipelines.migrate_domain_validation_examples import migrate

    src = default_db()
    if not src.exists():
        pytest.skip("shipped database not present")
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "hkcc.db"
        shutil.copy(src, copy)
        con = sqlite3.connect(copy)
        before = con.execute("SELECT COUNT(*), COALESCE(SUM(score), 0) FROM evidence").fetchone()
        rows_before = con.execute("SELECT id, agent_id, kcc_id, score, direction FROM evidence ORDER BY id").fetchall()
        migrate(con)
        after = con.execute("SELECT COUNT(*), COALESCE(SUM(score), 0) FROM evidence").fetchone()
        rows_after = con.execute("SELECT id, agent_id, kcc_id, score, direction FROM evidence ORDER BY id").fetchall()
        con.close()
    assert before == after, "the migration changed evidence counts or scores"
    assert rows_before == rows_after, "the migration modified evidence rows"


def test_examples_never_enter_a_positive_evidence_count(db):
    """The count of positive cells must not move when examples exist."""
    positives = db.scalar(
        select(func.count()).select_from(Evidence).where(Evidence.score > 0)
    )
    n_examples = db.scalar(select(func.count()).select_from(CandidateDomainValidationExample))
    assert n_examples > 0, "no examples seeded — the rest of this test proves nothing"
    # The two are unrelated by construction: there is no join path between them.
    assert not [
        fk for fk in sa_inspect(db.bind).get_foreign_keys(TABLE)
        if fk["referred_table"] == "evidence"
    ]
    assert positives == db.scalar(
        select(func.count()).select_from(Evidence).where(Evidence.score > 0)
    )


# --------------------------------------------------------------- migration --

def test_seed_validates_against_the_shipped_database():
    if not default_db().exists():
        pytest.skip("shipped database not present")
    con = sqlite3.connect(default_db())
    try:
        assert validate(con) == []
    finally:
        con.close()


def test_migration_is_idempotent():
    """A second --apply must be a no-op, not a duplicate or an error."""
    import shutil
    import tempfile
    from pathlib import Path

    from hkcc.pipelines.migrate_domain_validation_examples import migrate

    src = default_db()
    if not src.exists():
        pytest.skip("shipped database not present")
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "hkcc.db"
        shutil.copy(src, copy)
        con = sqlite3.connect(copy)
        migrate(con)
        first = con.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
        migrate(con)
        second = con.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
        assert first == second == len(EXAMPLES)
        assert diff(con) == {"added": [], "updated": [], "unchanged": [e["id"] for e in EXAMPLES]}
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        con.close()


def test_dry_run_writes_nothing():
    """`diff` reports; only `migrate` writes."""
    import shutil
    import tempfile
    from pathlib import Path

    src = default_db()
    if not src.exists():
        pytest.skip("shipped database not present")
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "hkcc.db"
        shutil.copy(src, copy)
        con = sqlite3.connect(copy)
        con.execute(f"DELETE FROM {TABLE}")
        con.commit()
        diff(con)
        validate(con)
        assert con.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] == 0
        con.close()


# --------------------------------------------------------------------- API --

def test_domains_list_exposes_validation_examples():
    """Against the shipped database.

    Deliberately does not take the conftest ``client`` fixture: that one serves
    an empty in-memory database through a dependency override, so every domain
    would come back missing and the assertion would pass for the wrong reason.
    """
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as live:
        rows = live.get("/api/v1/domains").json()
    by_code = {d["code"]: d for d in rows}
    assert by_code["EMD3"]["validation_examples"], "EMD3 returned no validation examples"
    assert by_code["CD5"]["validation_examples"] == []


def test_domain_detail_returns_examples_in_sort_order():
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as live:
        d = live.get("/api/v1/domains/emd3").json()
    orders = [v["sort_order"] for v in d["validation_examples"]]
    assert orders == sorted(orders)
    assert "score" not in d["validation_examples"][0]


def test_api_and_sqlite_agree_on_validation_examples(monkeypatch):
    """Both data paths, key by key — the drift this project has been bitten by."""
    from fastapi.testclient import TestClient

    from hkcc.api.main import app
    from hkcc.app import data_client

    monkeypatch.delenv("API_BASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for fn in (data_client._api_healthy, data_client._db_healthy, data_client.get_data_source):
        fn.cache_clear()
    # `_cached` is a no-op outside a Streamlit runtime, so there is nothing to
    # invalidate here - the bare function runs on every call under pytest.
    db_side = {d["code"]: d for d in data_client.list_candidate_domains()}

    with TestClient(app) as live:
        api_side = {d["code"]: d for d in live.get("/api/v1/domains").json()}

    for code, d in db_side.items():
        a = api_side[code]
        assert [v["id"] for v in d["validation_examples"]] == [v["id"] for v in a["validation_examples"]]
        for vd, va in zip(d["validation_examples"], a["validation_examples"]):
            assert set(vd) == set(va), f"{code}: field-set mismatch"
            assert vd == va, f"{code}/{vd['id']}: value mismatch"


def test_older_api_payload_without_examples_normalises_to_empty():
    """UI and API deploy separately; a version-skewed API must not crash a page."""
    from hkcc.app.data_client import _normalise_domain

    out = _normalise_domain({"id": "emd1", "primary_kcc_ids": ["kcc-04"], "secondary_kcc_ids": []})
    assert out["validation_examples"] == []


# ------------------------------------------------------------------ export --

def test_release_export_includes_the_table(tmp_path, monkeypatch):
    """A release that omits the rules for reading Layer 2 ships half the layer."""
    import pandas as pd

    from hkcc.pipelines import export_release as mod

    monkeypatch.setattr(mod, "export_dir", lambda: tmp_path)
    out = mod.export_release("test-tag")

    csv = out / f"{TABLE}.csv"
    assert csv.exists(), f"{TABLE} missing from the export: {sorted(p.name for p in out.glob('*.csv'))}"
    df = pd.read_csv(csv)
    assert "score" not in df.columns, "the exported table must not carry a score"
    assert len(df) == len(EXAMPLES)

    # And it has to reach the machine-readable bundle too, not just the CSVs.
    import json

    bundle = json.loads((out / "hkcc_full.json").read_text()) if (out / "hkcc_full.json").exists() else None
    if bundle is not None:
        assert TABLE in bundle, "the JSON bundle omits the validation examples"
        assert len(bundle[TABLE]) == len(EXAMPLES)


# ---------------------------------------------------------------------- UI --

#: AppTest resolves a relative path against the *calling* file, i.e. tests/.
BROWSE_PAGE = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages" / "2_Browse_KCCs.py"


def _browse_page():
    from streamlit.testing.v1 import AppTest

    from hkcc.app import data_client

    for fn in (data_client._api_healthy, data_client._db_healthy, data_client.get_data_source):
        fn.cache_clear()
    return AppTest.from_file(str(BROWSE_PAGE), default_timeout=120).run()


def test_browse_page_renders_the_examples_and_skips_cd5():
    """One expander per domain that has examples - and none for CD5.

    An empty panel would read as "not filled in yet" and invite someone to write
    simulation results for a domain that has no simulation.
    """
    at = _browse_page()
    assert not at.exception, at.exception
    labels = [e.label for e in at.expander if "validation examples" in e.label.lower()]
    counts = sorted(int(label.rsplit("(", 1)[1].rstrip(")")) for label in labels)
    assert len(labels) == 4, f"expected one expander per EMD, got {labels}"
    assert counts == [3, 3, 3, 4], counts


def test_the_page_says_they_are_not_evidence():
    """The disclaimer is the whole reason this may be shown next to the bars."""
    at = _browse_page()
    captions = " ".join(c.value for c in at.caption).lower()
    assert "model-derived" in captions
    assert "not" in captions and "independent positive" in captions


def test_the_page_does_not_rank_by_evidentiary_status():
    """Status is a kind, not a rank; the UI must not imply an ordering."""
    src = BROWSE_PAGE.read_text(encoding="utf-8")
    block = src.split("validation_examples", 1)[1]
    for banned in ("sorted(examples", "strength", "tier", "progress(", "metric("):
        assert banned not in block, f"the examples block uses {banned!r}, which implies a ranking"
