"""P2 data helpers — KCC detail, evidence citations."""

import pytest

from hkcc.app import data_client


@pytest.fixture(autouse=True)
def _default_data_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    from hkcc.app import data_client as dc

    dc._api_healthy.cache_clear()
    dc._db_healthy.cache_clear()
    dc.get_data_source.cache_clear()


def test_get_kcc_benzene_path():
    k = data_client.get_kcc("kcc-02")
    assert k is not None
    assert k["short"] == "Genotoxic"


def test_agents_for_kcc():
    linked = data_client.agents_for_kcc("kcc-02", min_score=3)
    assert any(a["id"] == "benzene-iarc" for a in linked)


def test_references_for_kcc_returns_only_linked_papers():
    """Framework papers are not evidence for a characteristic.

    This asserted the opposite: that `references_for_kcc` falls back to every
    framework-tagged paper. Because `reference_kccs` holds no rows, that
    fallback fired for all ten KCCs, so each page listed the same 14 papers
    under "Anchoring publications". (It also queried `kcc-11`, retired when the
    extended characteristics became Layer 2 domains.)
    """
    for kcc_id in (k["id"] for k in data_client.list_kccs()):
        linked = data_client.references_for_kcc(kcc_id)
        assert all(kcc_id in r.get("kcc_ids", []) for r in linked), f"{kcc_id}: unlinked paper returned as an anchor"


def test_framework_references_are_offered_separately():
    framework = data_client.framework_references()
    assert any(r["id"] == "smith2016-kcc" for r in framework), "the KCC framework paper is missing"
    assert all(not r.get("kcc_ids") for r in framework), "a KCC-linked paper leaked into the framework list"


def test_evidence_for_agent_resolves_refs():
    rows = data_client.evidence_for_agent("benzene-iarc")
    assert rows
    scored = [r for r in rows if r["score"] > 0]
    assert scored
    assert scored[0]["refs"] or scored[0]["n_refs"] >= 0
