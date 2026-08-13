"""Claims the product makes about itself must match the database.

Six ways the shipped app or its exports disagreed with the data behind them:

* About said "Four cross-cutting candidate domains" while the database held
  five — the paper's EMD1-4 plus CD5, which carries its own provenance.
* The KCC tiles counted any cell with ``score > 0`` as an agent with evidence,
  including negative, equivocal and unspecified directions: KC2 read 152 where
  129 agents have positive evidence at "limited" or better.
* Every release bundle shipped Layer 1 only, so a downloaded dataset could not
  reconstruct the two-layer annotation model the project documents.
* The KCAD data dictionary carried Supplementary Table 2 verbatim, including
  two definitions that are transposed and one that repeats another column's
  text — so ``Monograph_num`` was documented as "Monograph chemical agent"
  while holding volume numbers.
* Two derivation behaviours were undocumented: Track A overriding File12's
  volume-level "Suggestive", and mixed primary calls resolving to positive.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from hkcc.app import data_client
from hkcc.db.models import KCC, CandidateDomain, Evidence, IarcMonographKcCall, KcadColumnDefinition
from hkcc.db.session import SessionLocal

ROOT = Path(__file__).resolve().parents[1]
ABOUT = ROOT / "hkcc" / "app" / "pages" / "9_About.py"
DETAIL = ROOT / "hkcc" / "app" / "pages" / "4_Agent_Detail.py"
RULES = ROOT / "docs" / "KCC_EVIDENCE_RULES.md"
PRIMARY_SYSTEMS = ("Exposed Humans", "Human cells in vitro", "Mammalian in vivo")


@pytest.fixture(autouse=True)
def _db_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


# ── 5: candidate-domain count ────────────────────────────────────────────────


def test_about_states_the_real_number_of_candidate_domains():
    db = SessionLocal()
    try:
        n_domains = db.scalar(select(func.count()).select_from(CandidateDomain))
    finally:
        db.close()
    assert n_domains == 5, "fixture assumes EMD1-4 plus CD5"

    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(ABOUT), default_timeout=120)
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    scope = next(m.value for m in app.markdown if "candidate domains" in m.value)
    assert f"{n_domains} in total" in scope
    assert "CD5" in scope, "the non-paper domain must be named, not folded in silently"


def test_the_domain_count_is_not_hard_coded():
    source = ABOUT.read_text(encoding="utf-8")
    assert "Four cross-cutting" not in source
    assert "list_candidate_domains" in source


# ── 6 / 7: undocumented derivation behaviour ─────────────────────────────────


def test_the_file014_override_is_documented_with_the_right_count():
    """39 pairs where File12 says Suggestive and File014 says Moderate/Strong."""
    db = SessionLocal()
    try:
        overall: dict[tuple[str, str], set[str]] = {}
        for call in db.scalars(select(IarcMonographKcCall)):
            if call.model_system == "Overall strength":
                overall.setdefault((call.agent_id, call.kcc_id), set()).add(call.call)
        from hkcc.db.models import IarcMonographKcStrength

        labels = {(s.agent_id, s.kcc_id): s.strength_label for s in db.scalars(select(IarcMonographKcStrength))}
    finally:
        db.close()
    upgraded = [
        key for key, calls in overall.items() if "Suggestive" in calls and labels.get(key) in ("Moderate", "Strong")
    ]
    assert len(upgraded) == 39, f"the documented count is stale: {len(upgraded)}"
    text = RULES.read_text(encoding="utf-8")
    assert "39 (agent, KC) pairs" in text
    assert "systematic upward shift" in text


def test_mixed_primary_calls_are_documented_and_surfaced():
    db = SessionLocal()
    try:
        by_pair: dict[tuple[str, str], set[str]] = {}
        for call in db.scalars(select(IarcMonographKcCall)):
            if call.model_system in PRIMARY_SYSTEMS:
                by_pair.setdefault((call.agent_id, call.kcc_id), set()).add(call.call)
    finally:
        db.close()
    mixed = {k: v for k, v in by_pair.items() if len(v & {"Yes", "No", "Protective"}) > 1}
    assert mixed, "no conflicting primary calls — test would be vacuous"

    text = RULES.read_text(encoding="utf-8")
    assert "Mixed primary calls are resolved in favour of the positive" in text
    # The UI must say so where the conflicting calls are visible.
    assert "The primary systems disagree" in DETAIL.read_text(encoding="utf-8")


def test_the_yes_plus_protective_pair_warns_in_the_ui():
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(DETAIL), default_timeout=180)
    app.session_state["agent_id"] = "drinking-mate-and-very-hot-beverages"
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    warnings = "\n".join(w.value for w in app.warning)
    assert "Protective, Yes" in warnings, "the mixed Yes/Protective cell is not flagged"


# ── 8: KCC tile counts ───────────────────────────────────────────────────────


def test_kcc_tiles_count_only_positive_evidence():
    stats = data_client.kcc_stats()
    db = SessionLocal()
    try:
        for kcc_id in [k for (k,) in db.execute(select(KCC.id))]:
            expected = db.scalar(
                select(func.count())
                .select_from(Evidence)
                .where(
                    Evidence.kcc_id == kcc_id,
                    Evidence.score >= 2,
                    Evidence.direction == "positive",
                )
            )
            assert stats[kcc_id]["carc_count"] == expected, f"{kcc_id} tile disagrees with the data"
    finally:
        db.close()


def test_the_tile_count_is_lower_than_the_old_score_above_zero_count():
    """Guards against a silent revert: the two differ by 23 on KC2 alone."""
    db = SessionLocal()
    try:
        loose = db.scalar(
            select(func.count()).select_from(Evidence).where(Evidence.kcc_id == "kcc-02", Evidence.score > 0)
        )
    finally:
        db.close()
    assert data_client.kcc_stats()["kcc-02"]["carc_count"] < loose


# ── 9: Layer 2 in the release bundle ─────────────────────────────────────────


def test_release_bundle_exports_layer_two():
    source = (ROOT / "hkcc" / "pipelines" / "export_release.py").read_text(encoding="utf-8")
    for table in (
        "candidate_domains",
        "candidate_domain_kccs",
        "candidate_domain_assays",
        "candidate_domain_references",
    ):
        assert f'"{table}"' in source, f"{table} missing from the release bundle"


def test_the_exported_layer_two_is_not_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HKCC_EXPORT_DIR", str(tmp_path))
    from hkcc.pipelines.export_release import export_release

    out = export_release("test-export")
    db = SessionLocal()
    try:
        n_domains = db.scalar(select(func.count()).select_from(CandidateDomain))
    finally:
        db.close()
    rows = (out / "candidate_domains.csv").read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) - 1 == n_domains, "exported domain count does not match the database"
    for table in ("candidate_domain_kccs", "candidate_domain_assays", "candidate_domain_references"):
        assert (out / f"{table}.csv").exists()


# ── 10: KCAD data dictionary ─────────────────────────────────────────────────


def test_the_misleading_definitions_carry_a_correction():
    db = SessionLocal()
    try:
        defs = {d.column_name: d for d in db.scalars(select(KcadColumnDefinition))}
    finally:
        db.close()
    for column in ("Monograph_num", "Monograph_chem", "Biomarker"):
        assert defs[column].hkcc_note, f"{column} has no corrected operational meaning"
        assert "hKCC" in defs[column].hkcc_note


def test_the_published_definitions_are_left_verbatim():
    """The source text is the record; corrections sit beside it, never replace it."""
    db = SessionLocal()
    try:
        defs = {d.column_name: d.definition for d in db.scalars(select(KcadColumnDefinition))}
    finally:
        db.close()
    # Including the source's own typo — evidence these are transcriptions.
    assert defs["Monograph_num"] == "Monograph chemical agent"
    assert "acitvation" in defs["Biomarker"]


def test_only_the_wrong_definitions_are_annotated():
    db = SessionLocal()
    try:
        annotated = {d.column_name for d in db.scalars(select(KcadColumnDefinition)) if d.hkcc_note}
    finally:
        db.close()
    assert annotated == {"Monograph_num", "Monograph_chem", "Biomarker"}


def test_the_correction_reaches_the_methodology_page():
    testing = pytest.importorskip("streamlit.testing.v1")
    page = ROOT / "hkcc" / "app" / "pages" / "9a_Methodology.py"
    app = testing.AppTest.from_file(str(page), default_timeout=180)
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    warnings = "\n".join(w.value for w in app.warning)
    assert "What this column holds in hKCC" in warnings
    assert "volume number" in warnings


def test_both_data_paths_expose_the_note():
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as real:
        api = {d["column_name"]: d for d in real.get("/api/v1/methodology/columns").json()}
    local = {d["column_name"]: d for d in data_client.list_column_definitions()}
    assert api["Monograph_num"]["hkcc_note"], "API drops the correction"
    assert local["Monograph_num"]["hkcc_note"], "database path drops the correction"


# ── 11 / 12 / 14 / 15 / 17: UX honesty ───────────────────────────────────────


def test_unscored_agents_are_badged_in_the_list():
    """A blank fingerprint reads as "investigated and empty" without a label."""
    from hkcc.app.components.agent_table import agent_table_html
    from hkcc.app.theme import apply_theme

    apply_theme(inject=False)
    scored = {
        "id": "a",
        "name": "A",
        "cas": "1",
        "agent_type": "x",
        "iarc_group": "1",
        "scores": [3],
        "evidence": {"kcc-01": 3},
    }
    unscored = {**scored, "id": "b", "name": "B", "evidence": {}, "scores": [None]}
    assert "no scored evidence" in agent_table_html([unscored])
    assert "no scored evidence" not in agent_table_html([scored])


def test_every_unscored_agent_would_be_badged():
    agents, _ = data_client.agents_with_evidence()
    unscored = [a for a in agents if not a.get("evidence")]
    assert len(unscored) == 13, f"the unscored set changed: {len(unscored)}"
    assert "pcb" in {a["id"] for a in unscored}, "PCBs are the headline case"


def test_the_volume_gap_is_stated_in_app():
    """Documented in the README; a reader in the app never saw it."""
    overview = (ROOT / "hkcc" / "app" / "pages" / "1_Overview.py").read_text(encoding="utf-8")
    methodology = (ROOT / "hkcc" / "app" / "pages" / "9a_Methodology.py").read_text(encoding="utf-8")
    assert "107–111" in overview
    assert "107–111" in methodology


def test_the_label_offset_appears_beyond_the_methodology_page():
    """The single easiest number in the product to misread against the paper."""
    from hkcc.db.evidence_rules import LABEL_OFFSET_SHORT

    assert "one rung up" in LABEL_OFFSET_SHORT
    pages = ["3_Carcinogens.py", "4_Agent_Detail.py", "5_Evidence_Matrix.py"]
    for name in pages:
        source = (ROOT / "hkcc" / "app" / "pages" / name).read_text(encoding="utf-8")
        assert "LABEL_OFFSET_SHORT" in source, f"{name} does not surface the label offset"


def test_the_matrix_page_warns_on_cross_track_sorting():
    """Carcinogens warned; the matrix sorted the same way in silence."""
    source = (ROOT / "hkcc" / "app" / "pages" / "5_Evidence_Matrix.py").read_text(encoding="utf-8")
    assert "Sorting across both sources" in source


def test_both_ranked_pages_default_to_alphabetical():
    """A cross-track ranking must not be what a first-time visitor lands on."""
    for name in ("3_Carcinogens.py", "5_Evidence_Matrix.py"):
        source = (ROOT / "hkcc" / "app" / "pages" / name).read_text(encoding="utf-8")
        assert '["name", "coverage", "substantial"]' in source, (
            f"{name}: 'name' must stay the first (default) sort option"
        )


def test_contribute_rejects_unassessed_pairs_and_says_so():
    """v0 revises existing scores only — 866 pairs cannot receive proposals."""
    from fastapi.testclient import TestClient

    from hkcc.api.main import app
    from hkcc.db.models import Evidence as E

    db = SessionLocal()
    try:
        scored = {(e.agent_id, e.kcc_id) for e in db.scalars(select(E))}
        kcc_ids = [k for (k,) in db.execute(select(KCC.id))]
    finally:
        db.close()
    # Any real unassessed pair: benzene has all ten assessed, so keying on it
    # made this test skip silently rather than exercise the 404.
    from hkcc.db.models import Agent

    db = SessionLocal()
    try:
        agent_ids = [a for (a,) in db.execute(select(Agent.id))]
    finally:
        db.close()
    agent_id, unassessed = next((a, k) for a in agent_ids for k in kcc_ids if (a, k) not in scored)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/contribute",
            json={
                "agent_id": agent_id,
                "kcc_id": unassessed,
                "proposed_score": 3,
                "rationale": "x" * 40,
                "submitter_name": "Test",
            },
        )
    assert response.status_code == 404, "an unassessed pair should be rejected, not queued"

    from hkcc.api.routers.contribute import submit_contribution

    assert "existing" in (submit_contribution.__doc__ or "").lower()
    samples = (ROOT / "hkcc" / "app" / "data" / "api_samples.py").read_text(encoding="utf-8")
    assert "revises existing scores only" in samples.lower() or "Revisions only" in samples


# ── technical notes: silent gaps that must stay stated ───────────────────────


def test_domain_only_assays_are_accounted_for_not_orphaned():
    """8 assays carry no KCC link because they attach to Layer 2 instead.

    They are not "unmapped": each links to a candidate domain. The Assays page
    said the catalogue was "mapped to one or more KCCs", which was untrue for
    these and left them invisible under any KCC filter with no explanation.
    """
    from hkcc.db.models import Assay, AssayKCC, CandidateDomainAssay

    db = SessionLocal()
    try:
        linked = {a for (a,) in db.execute(select(AssayKCC.assay_id).distinct())}
        domain_linked = {a for (a,) in db.execute(select(CandidateDomainAssay.assay_id).distinct())}
        assays = [a.id for a in db.scalars(select(Assay))]
    finally:
        db.close()
    orphans = [a for a in assays if a not in linked and a not in domain_linked]
    assert not orphans, f"assays attached to neither layer: {orphans}"

    unmapped = [a for a in assays if a not in linked]
    assert unmapped, "no domain-only assays — test would be vacuous"
    page = (ROOT / "hkcc" / "app" / "pages" / "6_Assays.py").read_text(encoding="utf-8")
    assert "Layer 2 candidate domains rather than a KCC" in page


def test_agent_level_kcad_counts_exclude_the_method_catalogue():
    """81% of annotations have no agent; they are methods, not agent evidence."""
    from hkcc.db.models import AssayAnnotation

    db = SessionLocal()
    try:
        total = db.scalar(select(func.count()).select_from(AssayAnnotation))
        without_agent = db.scalar(
            select(func.count()).select_from(AssayAnnotation).where(AssayAnnotation.agent_id.is_(None))
        )
    finally:
        db.close()
    assert without_agent / total > 0.5, "the catalogue is no longer mostly agent-free"
    # Anything shown as an agent's KCAD coverage must come from agent-linked rows.
    for agent_id in ("benzene-iarc", "aniline"):
        refs = data_client.references_for_agent(agent_id)
        assert len(refs) < total, "agent reference count leaks the whole catalogue"


def test_the_score_derivation_verification_still_covers_every_cell():
    """Importers are not shipped, so these tests are the only regeneration record.

    If a track ever falls out of the verified set, the shipped scores become
    unreproducible with nothing failing to say so.
    """
    from hkcc.db.models import Evidence as E

    db = SessionLocal()
    try:
        tracks = {t for (t,) in db.execute(select(E.source_track).distinct())}
        total = db.scalar(select(func.count()).select_from(E))
    finally:
        db.close()
    assert tracks == {"10yr-iarc", "vol100-kc"}, f"an unverified track appeared: {tracks}"

    rules_tests = (ROOT / "tests" / "test_evidence_rules.py").read_text(encoding="utf-8")
    assert "test_every_score_matches_the_documented_rules" in rules_tests
    assert "test_volume_100_track_uses_the_documented_mapping" in rules_tests
    assert total == 844, "cell count changed; re-verify both tracks against the rules"
