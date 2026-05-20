"""POST /api/v1/contribute — validation, 404 paths, rate limiting."""

import pytest

from api.main import app
from api.ratelimit import reset_rate_limit
from db.models import KCC, Agent, Evidence
from db.session import get_db


@pytest.fixture(autouse=True)
def _reset_rate_limit(monkeypatch):
    monkeypatch.setenv("HKCC_CONTRIBUTE_MAX_PER_WINDOW", "1000")
    monkeypatch.setenv("HKCC_CONTRIBUTE_WINDOW_SECONDS", "60")
    reset_rate_limit()


def _seed(client):
    db = next(app.dependency_overrides[get_db]())
    db.add(KCC(id="kcc-01", n=1, title="Genotoxicity", short="Geno", description="d", mechanism="m", icon="helix"))
    db.add(Agent(id="benzene", name="Benzene", cas="71-43-2", iarc_group="1", agent_type="chemical", summary="s"))
    db.flush()
    db.add(Evidence(agent_id="benzene", kcc_id="kcc-01", score=2, n_refs=0))
    db.commit()
    db.close()


def _payload(**over):
    base = {
        "agent_id": "benzene",
        "kcc_id": "kcc-01",
        "proposed_score": 3,
        "rationale": "Long enough rationale text",
        "submitter_name": "Anon",
        "submitter_email": "anon@example.org",
    }
    base.update(over)
    return base


def test_contribute_happy_path(client):
    _seed(client)
    r = client.post("/api/v1/contribute", json=_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["revision_id"] >= 1


def test_contribute_rejects_short_rationale(client):
    _seed(client)
    r = client.post("/api/v1/contribute", json=_payload(rationale="too short"))
    assert r.status_code == 422


def test_contribute_rejects_bad_email(client):
    _seed(client)
    r = client.post("/api/v1/contribute", json=_payload(submitter_email="not-an-email"))
    assert r.status_code == 422


def test_contribute_rejects_score_out_of_range(client):
    _seed(client)
    r = client.post("/api/v1/contribute", json=_payload(proposed_score=9))
    assert r.status_code == 422


def test_contribute_404_when_agent_missing(client):
    _seed(client)
    r = client.post("/api/v1/contribute", json=_payload(agent_id="nope"))
    assert r.status_code == 404


def test_contribute_404_when_evidence_cell_missing(client):
    _seed(client)
    db = next(app.dependency_overrides[get_db]())
    db.add(KCC(id="kcc-02", n=2, title="X", short="X", description="d", mechanism="m", icon="grid"))
    db.commit()
    db.close()
    r = client.post("/api/v1/contribute", json=_payload(kcc_id="kcc-02"))
    assert r.status_code == 404


def test_contribute_rate_limit(client, monkeypatch):
    monkeypatch.setenv("HKCC_CONTRIBUTE_MAX_PER_WINDOW", "2")
    monkeypatch.setenv("HKCC_CONTRIBUTE_WINDOW_SECONDS", "60")
    from api import ratelimit

    monkeypatch.setattr(ratelimit, "MAX_PER_WINDOW", 2)
    monkeypatch.setattr(ratelimit, "WINDOW_SECONDS", 60)
    reset_rate_limit()
    _seed(client)
    assert client.post("/api/v1/contribute", json=_payload()).status_code == 200
    assert client.post("/api/v1/contribute", json=_payload()).status_code == 200
    blocked = client.post("/api/v1/contribute", json=_payload())
    assert blocked.status_code == 429
    assert "Rate limit" in blocked.json()["detail"]
