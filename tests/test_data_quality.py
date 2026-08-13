"""Structural fields the UI advertises must be answerable from the data.

Three separate ways the interface promised more than the database holds:

* ``agent_sites`` has **no rows**, yet the agent table carried a "Tumour sites"
  column and Agent Detail a "Tumour sites" metric — a header above 171 em
  dashes, and a metric that read "—" for every agent.
* 13 agents carry dense KCAD literature and no scores at all (aniline: 96
  annotations, zero evidence). Their fingerprints render entirely blank, which
  reads as "investigated and found negative" rather than "outside the two IARC
  sources that produce scores".
* ``data_role`` was exposed on Agent Detail but nowhere in the matrix, so 147
  cells scoring 2-4 on data the IARC working group explicitly did **not** use
  looked exactly like cells it relied on.

Plus one lossy field: a KCAD "Secondary KC" cell reading "3  9" kept only its
first KC, so a filter on secondary KC undercounted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from hkcc.app import data_client
from hkcc.app.components.agent_table import agent_table_html
from hkcc.app.components.matrix import matrix_heatmap_html, to_matrix_row
from hkcc.app.theme import apply_theme
from hkcc.db.models import AgentSite, AssayAnnotation, Evidence
from hkcc.db.session import SessionLocal

apply_theme(inject=False)
DETAIL = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages" / "4_Agent_Detail.py"

ROW = {
    "id": "a",
    "name": "A",
    "cas": "1",
    "agent_type": "x",
    "iarc_group": "1",
    "scores": [1],
    "evidence": {"k": 1},
}


@pytest.fixture(autouse=True)
def _db_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


# ── 12a: tumour sites ────────────────────────────────────────────────────────


def test_the_shipped_dataset_really_has_no_sites():
    """Guards the tests below: if sites arrive, the column should come back."""
    db = SessionLocal()
    try:
        assert db.scalar(select(func.count()).select_from(AgentSite)) == 0
    finally:
        db.close()


def test_sites_column_is_absent_when_no_agent_has_sites():
    html = agent_table_html([{**ROW, "sites": []}])
    assert "Tumour sites" not in html
    assert html.count("<th") == html.count("<td"), "header and body columns disagree"


def test_sites_column_returns_as_soon_as_there_is_data():
    html = agent_table_html([{**ROW, "sites": ["Lung"]}])
    assert "Tumour sites" in html
    assert "Lung" in html
    assert html.count("<th") == html.count("<td")


# ── 12c/12d: KCAD-only and non-evaluable agents ──────────────────────────────


def test_kcad_only_agents_exist_and_are_explained():
    """aniline has 96 annotations and no scores; the page must say why."""
    db = SessionLocal()
    try:
        scored = {a for (a,) in db.execute(select(Evidence.agent_id).distinct())}
    finally:
        db.close()
    assert "aniline" not in scored, "test fixture assumes aniline is unscored"

    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(DETAIL), default_timeout=120)
    app.session_state["agent_id"] = "aniline"
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    notices = "\n".join(i.value for i in app.info)
    assert "No scored KCC evidence" in notices
    assert "KCAD contributes no evidence scores" in notices
    assert "not assessed" in notices, "must distinguish unassessed from negative"


def test_the_umbrella_agent_is_marked_non_evaluable():
    db = SessionLocal()
    try:
        ungrouped = [a["id"] for a in data_client.list_agents() if a.get("iarc_group") in (None, "—")]
    finally:
        db.close()
    assert ungrouped == ["nitroanisole"], f"unexpected ungrouped agents: {ungrouped}"

    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(DETAIL), default_timeout=120)
    app.session_state["agent_id"] = "nitroanisole"
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    warnings = "\n".join(w.value for w in app.warning)
    assert "Not an IARC evaluation unit" in warnings


def test_a_classified_agent_gets_neither_notice():
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(DETAIL), default_timeout=120)
    app.session_state["agent_id"] = "benzene-iarc"
    app.run()
    text = "\n".join([w.value for w in app.warning] + [i.value for i in app.info])
    assert "Not an IARC evaluation unit" not in text
    assert "No scored KCC evidence" not in text


# ── 13: data_role in the matrix ──────────────────────────────────────────────


def test_matrix_rows_carry_every_data_role_on_both_paths():
    """Every role, not only "Not used".

    Emitting the hazardous value alone made Supportive and Upgrade cells
    indistinguishable from cells with no role, so the matrix CSV exported 103 of
    them as blank while claiming to carry the role for every cell.
    """
    # Deliberately not the shared `client` fixture: it overrides get_db with an
    # empty in-memory database, which a TestClient built here would inherit.
    from collections import Counter

    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    def tally(rows):
        return Counter(v for r in rows for v in r.get("data_roles", {}).values())

    db_tally = tally(data_client.get_matrix()["rows"])
    with TestClient(app) as real:
        api_tally = tally(real.get("/api/v1/matrix").json()["rows"])

    db = SessionLocal()
    try:
        expected = Counter(
            role for (role,) in db.execute(select(Evidence.data_role).where(Evidence.data_role.isnot(None)))
        )
    finally:
        db.close()
    assert set(expected) == {"Not used", "Supportive", "Upgrade"}
    assert db_tally == expected, "database path drops roles from the matrix"
    assert api_tally == expected, "API drops roles from the matrix"


def test_every_not_used_cell_is_marked_in_the_rendered_matrix():
    """Including protective ones, which took an early return and showed nothing.

    Renders through ``to_matrix_row`` — the adapter the page itself uses. This
    hand-built its rows before, which exercised the component while the page was
    stripping the fields, so it stayed green against a visibly broken matrix.
    ``tests/test_evidence_matrix_page.py`` now checks the page's real output;
    this one covers the component.
    """
    rows = data_client.get_matrix()["rows"]
    # Only "Not used" is marked; Supportive and Upgrade travel in the payload
    # for export but carry no interpretive hazard, so they get no glyph.
    expected = sum(1 for r in rows for v in r.get("data_roles", {}).values() if v == "Not used")
    assert expected > 0

    html = matrix_heatmap_html(data_client.list_kccs(), [to_matrix_row(r) for r in rows])
    assert html.count("&#9633;") == expected, "marker count disagrees with the data"
    assert html.count("Not used (the working group") == expected, "tooltips missing"


def test_the_legend_explains_the_marker():
    from hkcc.app.utils.evidence import ev_legend_html

    legend = ev_legend_html()
    assert "&#9633;" in legend
    assert "did not use this data" in legend


# ── 15: multi-valued secondary KCs ───────────────────────────────────────────


def test_multi_valued_secondary_kcs_are_all_recovered():
    db = SessionLocal()
    try:
        anns = list(db.scalars(select(AssayAnnotation)))
    finally:
        db.close()

    multi = [a for a in anns if a.secondary_kc_raw and len(a.secondary_kc_raw.split()) > 1]
    assert multi, "no multi-valued secondary KC cells — test is vacuous"
    for a in multi:
        assert len(a.secondary_kcc_ids) > 1, f"{a.secondary_kc_raw!r} still collapses to one KC"
        assert a.secondary_kcc_ids[0] == a.secondary_kcc_id, "scalar must stay the first entry"


def test_a_secondary_kc_filter_no_longer_undercounts():
    db = SessionLocal()
    try:
        anns = list(db.scalars(select(AssayAnnotation)))
    finally:
        db.close()
    scalar_only = sum(1 for a in anns if a.secondary_kcc_id == "kcc-09")
    derived = sum(1 for a in anns if "kcc-09" in a.secondary_kcc_ids)
    assert derived > scalar_only, "the derived field recovers nothing"


def test_the_parser_handles_every_shipped_raw_value():
    db = SessionLocal()
    try:
        anns = list(db.scalars(select(AssayAnnotation)))
    finally:
        db.close()
    for a in anns:
        ids = a.secondary_kcc_ids
        assert len(ids) == len(set(ids)), f"duplicate KCs parsed from {a.secondary_kc_raw!r}"
        for kcc_id in ids:
            assert kcc_id.startswith("kcc-") and len(kcc_id) == 6, f"bad id from {a.secondary_kc_raw!r}"
        if not a.secondary_kc_raw and not a.secondary_kcc_id:
            assert ids == []


def test_uncertainty_marker_is_preserved_rather_than_parsed_away():
    """ "9?" is included as a mention, but the qualifier stays readable."""
    db = SessionLocal()
    try:
        row = next(a for a in db.scalars(select(AssayAnnotation)) if (a.secondary_kc_raw or "").endswith("?"))
    finally:
        db.close()
    assert "?" in row.secondary_kc_raw
    assert "kcc-09" in row.secondary_kcc_ids


# ── citation wording: derivation vs primary study ────────────────────────────


def test_most_cells_cite_only_their_derivation():
    """Guards the wording: if this stopped being true, the framing should change."""
    from sqlalchemy.orm import selectinload

    from hkcc.db.config import DERIVATION_REF_IDS
    from hkcc.db.models import Evidence as E

    db = SessionLocal()
    try:
        cells = list(db.scalars(select(E).options(selectinload(E.citations))))
    finally:
        db.close()
    derivation_only = [c for c in cells if c.citations and {x.reference_id for x in c.citations} <= DERIVATION_REF_IDS]
    assert len(derivation_only) / len(cells) > 0.8, (
        "most cells no longer cite only their derivation — revisit the UI wording"
    )


def test_the_ui_does_not_call_derivation_sources_anchored_references():
    """ "Anchored to N references" read as N primary mechanistic studies."""
    detail = DETAIL.read_text(encoding="utf-8")
    # Checked against code, not comments: the phrase survives in a comment
    # explaining why it was removed.
    code = "\n".join(ln for ln in detail.splitlines() if not ln.lstrip().startswith("#"))
    assert "Anchored to" not in code
    assert "Derivation source" in code
    assert "Supporting literature" in code

    about = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages" / "9_About.py"
    text = about.read_text(encoding="utf-8")
    assert "linked to its citation at the cell level" not in text
    assert "not the underlying experiments" in text


def test_agent_detail_separates_the_two_kinds_of_citation():
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(DETAIL), default_timeout=120)
    app.session_state["agent_id"] = "benzene-iarc"
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    captions = "\n".join(c.value for c in app.caption)
    assert "Derivation source" in captions
    assert "not the underlying experiments" in captions
