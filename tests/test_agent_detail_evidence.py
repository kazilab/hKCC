"""Agent Detail must show every assessed cell, including 0 and protective ones.

The "Detailed evidence" list used to start with ``if cell["score"] < 1:
continue``, which hid all 161 cells scoring 0 — among them every protective
finding. Drinking coffee is the clearest case: three characteristics where the
primary systems report the agent as *suppressing* the characteristic simply
vanished from its profile.

A score alone also cannot explain itself. These tests cover the call-level
breakdown that sits under each cell, which is what makes a 0 or a protective
direction readable rather than merely low.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hkcc.app import data_client

PAGES = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages"
DETAIL = PAGES / "4_Agent_Detail.py"
IARC_MATRIX = PAGES / "9b_IARC_Matrix.py"

# Protective in two primary systems, equivocal in the third -> score 0.
COFFEE = "drinking-coffee"
PROTECTIVE_KCCS = {"kcc-05", "kcc-06", "kcc-07"}


@pytest.fixture(autouse=True)
def _default_data_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


@pytest.fixture(scope="module")
def coffee_page():
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(DETAIL), default_timeout=120)
    app.session_state["agent_id"] = COFFEE
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    return app


def test_the_score_filter_is_gone():
    source = DETAIL.read_text(encoding="utf-8")
    assert 'cell["score"] < 1' not in source, "score-0 cells must not be filtered out"


def test_the_data_still_exercises_this_case():
    """Guards the fixture: if coffee stopped being protective, the rest is vacuous."""
    rows = {e["kcc_id"]: e for e in data_client.evidence_for_agent(COFFEE)}
    protective = {kid for kid, e in rows.items() if e["direction"] == "protective"}
    assert protective == PROTECTIVE_KCCS
    assert all(rows[kid]["score"] == 0 for kid in protective)


def test_every_assessed_cell_is_listed(coffee_page):
    listed = len(coffee_page.expander)
    assessed = len(data_client.evidence_for_agent(COFFEE))
    assert listed == assessed, f"{assessed} assessed cells but {listed} shown"


def test_protective_cells_are_listed_and_labelled(coffee_page):
    labels = [e.label for e in coffee_page.expander]
    protective = [line for line in labels if "protective" in line]
    assert len(protective) == len(PROTECTIVE_KCCS)
    for line in protective:
        assert "score 0/4" in line


def test_protective_cells_explain_themselves(coffee_page):
    warnings = "\n".join(w.value for w in coffee_page.warning)
    assert "suppressing" in warnings
    assert "No positive evidence is recorded" in warnings


def test_the_call_breakdown_is_shown(coffee_page):
    text = "\n".join(m.value for m in coffee_page.markdown)
    assert "Model-system calls" in text
    assert coffee_page.dataframe, "no call breakdown table rendered"


def test_the_breakdown_distinguishes_primary_from_supplementary(coffee_page):
    """Only three of the eight model systems feed the score."""
    rows = [
        row
        for frame in coffee_page.dataframe
        for row in frame.value.to_dict("records")  # .value is a DataFrame
    ]
    assert rows, "call breakdown is empty"
    counts = {r["Counts toward score"] for r in rows}
    assert counts == {"yes", "—"}, f"primary/supplementary not distinguished: {counts}"
    assert [r for r in rows if "Protective" in r["Call"]], (
        "coffee's protective calls should be visible in the breakdown"
    )
    # Every row marked as counting must be one of the three documented systems.
    primary = {r["Model system"] for r in rows if r["Counts toward score"] == "yes"}
    assert primary <= {"Exposed Humans", "Human cells in vitro", "Mammalian in vivo"}


def test_volume_100_agents_render_without_a_call_breakdown():
    """That track derives from a figure and has no call table; it must not error."""
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(DETAIL), default_timeout=120)
    app.session_state["agent_id"] = "2-naphthylamine"
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    assert app.expander, "a Volume 100 agent should still list its assessed cells"
    text = "\n".join(m.value for m in app.markdown)
    assert "Model-system calls" not in text


def test_the_deep_link_preselects_the_agent_on_the_iarc_matrix_page():
    """The breakdown links onward for the full matrix; the link must land."""
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(IARC_MATRIX), default_timeout=120)
    app.query_params["iarc_agent"] = COFFEE
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    picked = [s for s in app.selectbox if s.key == "iarc_matrix_agent"]
    assert picked, "agent selectbox not found"
    assert picked[0].value.startswith("Drinking coffee")
    assert "iarc_agent" not in app.query_params, "the param should be consumed, not sticky"
