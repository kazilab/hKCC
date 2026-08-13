"""POST /api/v1/contribute — validation, 404 paths, rate limiting."""

import pytest

from hkcc.api.main import app
from hkcc.api.ratelimit import reset_rate_limit
from hkcc.db.models import KCC, Agent, Evidence
from hkcc.db.session import get_db


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


def test_contribute_no_longer_accepts_an_email(client):
    """The field was validated then silently discarded; now it is refused outright."""
    _seed(client)
    r = client.post("/api/v1/contribute", json=_payload(submitter_email="anon@example.org"))
    assert r.status_code == 422, "unknown fields must be rejected, not quietly dropped"


def test_submitter_name_is_stored_separately_from_the_rationale(client):
    """Attribution used to be concatenated into the scientific rationale text."""
    from hkcc.db.models import Revision

    _seed(client)
    r = client.post("/api/v1/contribute", json=_payload(rationale="A clean rationale sentence."))
    assert r.status_code == 200
    db = next(app.dependency_overrides[get_db]())
    rev = db.get(Revision, r.json()["revision_id"])
    assert rev.rationale == "A clean rationale sentence."
    assert "[Anon]" not in rev.rationale
    assert rev.submitted_by == "Anon"
    db.close()


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
    from hkcc.api import ratelimit

    monkeypatch.setattr(ratelimit, "MAX_PER_WINDOW", 2)
    monkeypatch.setattr(ratelimit, "WINDOW_SECONDS", 60)
    reset_rate_limit()
    _seed(client)
    assert client.post("/api/v1/contribute", json=_payload()).status_code == 200
    assert client.post("/api/v1/contribute", json=_payload()).status_code == 200
    blocked = client.post("/api/v1/contribute", json=_payload())
    assert blocked.status_code == 429
    assert "Rate limit" in blocked.json()["detail"]


# --- header-spoofing and queue-cap guards -----------------------------------


def test_rate_limit_is_not_bypassable_with_x_forwarded_for(client, monkeypatch):
    """Regression: rotating X-Forwarded-For used to reset the budget every time.

    With no trusted proxy configured (the default) the header must be ignored
    entirely, so a caller stays in one bucket however they label themselves.
    """
    monkeypatch.setenv("HKCC_CONTRIBUTE_MAX_PER_WINDOW", "3")
    monkeypatch.setenv("HKCC_CONTRIBUTE_WINDOW_SECONDS", "3600")
    monkeypatch.setenv("HKCC_TRUSTED_PROXY_HOPS", "0")
    import importlib

    from hkcc.api import ratelimit

    importlib.reload(ratelimit)
    ratelimit.reset_rate_limit()
    monkeypatch.setattr("hkcc.api.routers.contribute.rate_limit_contribute", ratelimit.rate_limit_contribute)
    app.dependency_overrides[
        __import__("hkcc.api.ratelimit", fromlist=["rate_limit_contribute"]).rate_limit_contribute
    ] = ratelimit.rate_limit_contribute

    _seed(client)
    codes = [
        client.post(
            "/api/v1/contribute",
            json=_payload(),
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
        ).status_code
        for i in range(1, 7)
    ]
    assert codes.count(200) == 3, f"spoofed header still buys extra writes: {codes}"
    assert codes[-1] == 429


def test_trusted_proxy_hops_reads_the_hop_the_proxy_appended(monkeypatch):
    """With one trusted proxy, the rightmost XFF entry identifies the caller."""
    import importlib

    from hkcc.api import ratelimit

    monkeypatch.setenv("HKCC_TRUSTED_PROXY_HOPS", "1")
    importlib.reload(ratelimit)

    class _Req:
        headers = {"x-forwarded-for": "1.1.1.1, 2.2.2.2, 9.9.9.9"}
        client = type("C", (), {"host": "127.0.0.1"})()

    assert ratelimit._client_key(_Req()) == "9.9.9.9"

    class _Short:
        headers = {}
        client = type("C", (), {"host": "127.0.0.1"})()

    assert ratelimit._client_key(_Short()) == "127.0.0.1"
    monkeypatch.delenv("HKCC_TRUSTED_PROXY_HOPS", raising=False)
    importlib.reload(ratelimit)


def test_pending_queue_is_capped(client, monkeypatch):
    monkeypatch.setenv("HKCC_CONTRIBUTE_MAX_PENDING", "2")
    _seed(client)
    codes = [client.post("/api/v1/contribute", json=_payload()).status_code for _ in range(4)]
    assert codes[:2] == [200, 200]
    assert 503 in codes, f"queue cap not enforced: {codes}"


def test_uvicorn_does_not_trust_proxy_headers_by_default(monkeypatch):
    """uvicorn's --proxy-headers default would hand us a spoofed peer address."""
    from hkcc.cli import proxy_settings

    monkeypatch.delenv("HKCC_TRUSTED_PROXY_HOPS", raising=False)
    assert proxy_settings() == (False, None)

    monkeypatch.setenv("HKCC_TRUSTED_PROXY_HOPS", "1")
    proxy_headers, allow = proxy_settings()
    assert proxy_headers is True
    assert allow == "127.0.0.1"

    monkeypatch.setenv("HKCC_FORWARDED_ALLOW_IPS", "10.1.2.3")
    assert proxy_settings() == (True, "10.1.2.3")
