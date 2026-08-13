"""Membership of the IARC matrix page must be defined by the call table.

Two defects sat next to each other on that page:

* The "Agents (paper)" metric computed ``len({v["volume"] for v in volumes})``
  — the volume count again — and so reported 19 agents against the 73 that
  actually have calls.
* The agent picker filtered on ``source_ref_id`` starting with "rusyn2024" plus
  a hard-coded list of eleven names. Twelve agents whose calls were present all
  along were unreachable (2mbt, tbbpa, tcab, parathion, ortho-nitroanisole,
  aldrin, dieldrin and others), and any future import would have been invisible
  until someone remembered to edit the list.

Both now derive from ``iarc_monograph_kc_calls``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import distinct, func, select

from hkcc.app import data_client
from hkcc.db.models import IarcMonographKcCall as Call
from hkcc.db.session import SessionLocal

PAGE = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages" / "9b_IARC_Matrix.py"
SOURCE = PAGE.read_text(encoding="utf-8")

# Present in the call table, absent from the retired allowlist.
PREVIOUSLY_HIDDEN = {
    "1-1-1-trichloroethane",
    "24d",
    "2mbt",
    "aldrin",
    "dieldrin",
    "dmf",
    "glycidyl-methacrylate",
    "ortho-nitroanisole",
    "parathion",
    "styrene-7-8-oxide",
    "tbbpa",
    "tcab",
}


@pytest.fixture(autouse=True)
def _db_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


@pytest.fixture(scope="module")
def agent_ids_with_calls() -> set[str]:
    db = SessionLocal()
    try:
        return {a for (a,) in db.execute(select(distinct(Call.agent_id)))}
    finally:
        db.close()


def test_the_listing_is_exactly_the_agents_that_have_calls(agent_ids_with_calls):
    listed = {a["agent_id"] for a in data_client.list_monograph_agents()}
    assert listed == agent_ids_with_calls, (
        f"missing: {sorted(agent_ids_with_calls - listed)}; "
        f"listed without calls: {sorted(listed - agent_ids_with_calls)}"
    )


def test_the_agents_the_allowlist_hid_are_back(agent_ids_with_calls):
    """Guards the fixture too: these must genuinely have calls."""
    assert PREVIOUSLY_HIDDEN <= agent_ids_with_calls
    listed = {a["agent_id"] for a in data_client.list_monograph_agents()}
    assert PREVIOUSLY_HIDDEN <= listed


def test_every_listed_agent_resolves_to_a_real_agent_row():
    """A call-table id with no `agents` row would render as a bare slug."""
    known = {a["id"] for a in data_client.list_agents()}
    for row in data_client.list_monograph_agents():
        assert row["agent_id"] in known, f"{row['agent_id']} has no agents row"
        assert row["name"], f"{row['agent_id']} has no name"
        assert row["kcc_count"] > 0
        assert row["volumes"], f"{row['agent_id']} has calls but no volume"


def test_the_hard_coded_allowlist_is_gone():
    for name in ("Pentachlorophenol", "Malathion", "Diazinon"):
        assert name not in SOURCE, f"{name} is still hard-coded in the agent filter"
    assert 'startswith("rusyn2024")' not in SOURCE
    assert "rusyn2024" not in SOURCE.split("tab_agent", 1)[-1].split("tab_kc", 1)[0]


def test_the_agent_metric_counts_agents_not_volumes(agent_ids_with_calls):
    """The bug was a copy of the volume expression under an agent label."""
    assert 'len({v["volume"] for v in volumes})' not in SOURCE.split("Agents", 1)[1][:200]
    db = SessionLocal()
    try:
        n_volumes = db.scalar(select(func.count(distinct(Call.monograph_volume))))
    finally:
        db.close()
    n_agents = len(data_client.list_monograph_agents())
    assert n_agents == len(agent_ids_with_calls)
    assert n_agents != n_volumes, "test cannot distinguish the two counts in this dataset"


def test_the_page_renders_the_full_picker():
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(PAGE), default_timeout=120)
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]

    picker = [s for s in app.selectbox if s.key == "iarc_matrix_agent"]
    assert picker, "agent selectbox not found"
    assert len(picker[0].options) == len(data_client.list_monograph_agents())

    metrics = {m.label: m.value for m in app.metric}
    assert metrics["Agents with calls"] == str(len(data_client.list_monograph_agents()))
    assert "Agents (paper)" not in metrics, "the mislabelled metric is still rendered"


def test_the_api_and_database_paths_agree():
    """Same shape from both sources, like every other resource.

    Deliberately does not take the shared ``client`` fixture: that fixture
    installs a dependency override pointing at an empty in-memory database,
    which any TestClient built inside the test would inherit.
    """
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as real:
        api_rows = real.get("/api/v1/monograph/agents").json()
    db_rows = data_client.list_monograph_agents()
    assert {r["agent_id"] for r in api_rows} == {r["agent_id"] for r in db_rows}
    assert set(api_rows[0]) == set(db_rows[0])
