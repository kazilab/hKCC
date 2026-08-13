"""The two data paths must return the same shape.

``data_client`` reads from a live API when ``API_BASE_URL`` is set and straight
from SQLite otherwise. The two serialisations were written separately and
drifted: ``get_agent`` on the database path omitted ``monograph_volume``,
``monograph_pub_year``, ``evaluation_year`` and ``source_ref_id``, all of which
the API returned. Agent Detail builds its caption from those fields, so the
provenance line — "IARC Monograph 29, Sup 7, 100F, 120 · Evaluated 2017" —
silently disappeared on the database path, which is the default and what the
public Streamlit deployment runs.

A page cannot defend against that: it reads a key that is simply absent. So the
guarantee belongs here, as a key-by-key comparison of the two paths for every
resource the app reads.

Matching keys turned out not to be enough. The database path also substituted
the display string ``"—"`` for a missing CAS or IARC group where the API
returned ``null`` — and the same module's matrix rows already returned ``null``,
so one agent had two shapes inside a single process while every key-set check
passed. The last tests here compare values, not just field names.
"""

from __future__ import annotations

import pytest

from hkcc.app import data_client

AGENT = "benzene-iarc"


@pytest.fixture(autouse=True)
def _db_path(monkeypatch):
    """Force the database path regardless of the caller's environment."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


@pytest.fixture(scope="module")
def client():
    """Overrides the shared fixture, which serves an empty in-memory database.

    Comparing two serialisations of *different* data proves nothing; both sides
    must read the shipped hkcc.db.
    """
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as test_client:
        yield test_client


def _api(client, path: str):
    response = client.get(f"/api/v1{path}")
    assert response.status_code == 200, f"{path} -> {response.status_code}"
    return response.json()


def _assert_same_keys(db_obj: dict, api_obj: dict, what: str) -> None:
    db_only = sorted(set(db_obj) - set(api_obj))
    api_only = sorted(set(api_obj) - set(db_obj))
    assert not api_only, f"{what}: the API returns {api_only}, the database path does not"
    assert not db_only, f"{what}: the database path returns {db_only}, the API does not"


def test_agent_detail_has_the_same_fields_on_both_paths(client):
    _assert_same_keys(data_client.get_agent(AGENT), _api(client, f"/agents/{AGENT}"), "agent detail")


def test_evidence_cells_have_the_same_fields_on_both_paths(client):
    db_cell = data_client.get_agent(AGENT)["evidence"][0]
    api_cell = _api(client, f"/agents/{AGENT}")["evidence"][0]
    _assert_same_keys(db_cell, api_cell, "evidence cell")
    # These carry the interpretation; a score without them is not readable.
    for field in ("direction", "source_track", "source_count", "data_role", "curator_notes"):
        assert field in db_cell, f"database path drops {field} from evidence cells"
        assert field in api_cell, f"API drops {field} from evidence cells"


def test_agent_list_items_have_the_same_fields_on_both_paths(client):
    _assert_same_keys(data_client.list_agents()[0], _api(client, "/agents")[0], "agent list item")


def test_kccs_have_the_same_fields_on_both_paths(client):
    _assert_same_keys(data_client.list_kccs()[0], _api(client, "/kccs")[0], "kcc")


def test_candidate_domains_have_the_same_fields_on_both_paths(client):
    db_rows = data_client.list_candidate_domains()
    if not db_rows:
        pytest.skip("no candidate domains in this dataset")
    _assert_same_keys(db_rows[0], _api(client, "/domains")[0], "candidate domain")


def test_matrix_rows_have_the_same_fields_on_both_paths(client):
    _assert_same_keys(data_client.get_matrix()["rows"][0], _api(client, "/matrix")["rows"][0], "matrix row")


def test_assays_have_the_same_fields_on_both_paths(client):
    db_rows = data_client.list_assays()
    if not db_rows:
        pytest.skip("no assays in this dataset")
    _assert_same_keys(db_rows[0], _api(client, "/assays")[0], "assay")


def test_the_provenance_caption_survives_on_the_database_path():
    """The concrete regression: Agent Detail's caption lost two of its parts."""
    agent = data_client.get_agent(AGENT)
    assert agent["monograph_volume"], "no monograph volume — the caption drops it"
    assert agent["evaluation_year"], "no evaluation year — the caption drops it"
    assert agent["source_ref_id"], "no source reference — provenance is unattributable"


def test_agent_values_match_and_not_just_the_field_names(client):
    """Same keys is not the same data.

    The database path substituted the display string ``"—"`` for a missing CAS
    or IARC group while the API returned ``null`` — and this module's own matrix
    rows already returned ``null``, so one agent had two shapes inside a single
    process. The key-set checks above all passed throughout.
    """
    for agent_id in (AGENT, "nitroanisole"):
        db_agent = data_client.get_agent(agent_id)
        api_agent = _api(client, f"/agents/{agent_id}")
        for field in ("cas", "iarc_group", "agent_type", "name", "monograph_volume", "evaluation_year"):
            assert db_agent[field] == api_agent[field], (
                f"{agent_id}.{field}: database path {db_agent[field]!r}, API {api_agent[field]!r}"
            )


def test_no_data_path_emits_a_display_placeholder():
    """An em dash is a rendering decision and must not reach the data layer."""
    agents = data_client.list_agents()
    offenders = [(a["id"], field) for a in agents for field in ("cas", "iarc_group") if a[field] == "—"]
    assert not offenders, f"display placeholders leaking from the data layer: {offenders[:5]}"


def test_the_missing_group_agent_is_consistent_across_every_view(client):
    """nitroanisole is the one agent with no IARC group; all three views agree."""
    db_list = next(a for a in data_client.list_agents() if a["id"] == "nitroanisole")
    db_matrix = next(r for r in data_client.get_matrix()["rows"] if r["agent_id"] == "nitroanisole")
    api_list = next(a for a in _api(client, "/agents") if a["id"] == "nitroanisole")
    api_matrix = next(r for r in _api(client, "/matrix")["rows"] if r["agent_id"] == "nitroanisole")
    values = {
        db_list["iarc_group"],
        db_matrix["iarc_group"],
        api_list["iarc_group"],
        api_matrix["iarc_group"],
    }
    assert values == {None}, f"iarc_group differs across views: {values}"
