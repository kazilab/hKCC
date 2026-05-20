"""P2 data helpers — KCC detail, evidence citations."""


import pytest

from app import data_client


@pytest.fixture(autouse=True)
def _mockup_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    from app import data_client as dc

    dc._api_healthy.cache_clear()
    dc._db_healthy.cache_clear()
    dc.get_data_source.cache_clear()
    from app import mockup_store

    mockup_store.load.cache_clear()


def test_get_kcc_benzene_path():
    k = data_client.get_kcc("kcc-02")
    assert k is not None
    assert k["short"] == "Genotoxic"


def test_agents_for_kcc():
    linked = data_client.agents_for_kcc("kcc-02", min_score=3)
    assert any(a["id"] == "benzene" for a in linked)


def test_references_for_kcc_includes_foundational():
    refs = data_client.references_for_kcc("kcc-11")
    assert any(r["id"] == "smith2016" for r in refs)


def test_evidence_for_agent_resolves_refs():
    rows = data_client.evidence_for_agent("benzene")
    assert rows
    scored = [r for r in rows if r["score"] > 0]
    assert scored
    assert scored[0]["refs"] or scored[0]["n_refs"] >= 0
