from api.main import app
from db.models import KCC, Agent
from db.session import get_db


def _seed(client):
    db = next(app.dependency_overrides[get_db]())
    db.add(
        KCC(
            id="kcc-01",
            n=1,
            title="Genotoxicity",
            short="Genotoxic",
            description="desc",
            mechanism="mech",
            icon="helix",
        )
    )
    db.add(
        Agent(
            id="benzene",
            name="Benzene",
            cas="71-43-2",
            iarc_group="1",
            agent_type="chemical",
            summary="summary",
        )
    )
    db.commit()
    db.close()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_kccs_empty(client):
    r = client.get("/api/v1/kccs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_kccs(client):
    _seed(client)
    r = client.get("/api/v1/kccs")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == "kcc-01"
