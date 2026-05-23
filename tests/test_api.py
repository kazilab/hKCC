from api.main import app
from db.models import KCC, Agent, AgentReference, Assay, AssayAnnotation, AssayKCC, Reference
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


def _seed_kcad(client):
    db = next(app.dependency_overrides[get_db]())
    db.add_all(
        [
            Assay(
                id="kcad-ames-assay",
                name="Ames assay",
                type="in vitro",
                target="Mutagenicity",
                throughput="medium",
                source="kcad",
                granularity="assay",
            ),
            AssayKCC(assay_id="kcad-ames-assay", kcc_id="kcc-01"),
            Reference(
                id="kcad-pmid-1234567",
                year=1992,
                authors="Smith",
                title="Smith 1992",
                journal="—",
                pmid="1234567",
                source="kcad",
            ),
            AgentReference(agent_id="benzene", reference_id="kcad-pmid-1234567", source="kcad"),
            AssayAnnotation(
                assay_id="kcad-ames-assay",
                kcc_id="kcc-01",
                reference_id="kcad-pmid-1234567",
                agent_id="benzene",
                monograph_chem="Benzene",
                organism="Bacteria",
                cell_format="in vitro",
            ),
        ]
    )
    db.commit()
    db.close()


def test_list_assays_filter_by_source(client):
    _seed(client)
    _seed_kcad(client)
    r = client.get("/api/v1/assays")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["source"] == "kcad"
    assert rows[0]["granularity"] == "assay"

    r2 = client.get("/api/v1/assays?source=mockup")
    assert r2.json() == []


def test_get_assay_annotations(client):
    _seed(client)
    _seed_kcad(client)
    r = client.get("/api/v1/assays/kcad-ames-assay/annotations")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["monograph_chem"] == "Benzene"
    assert rows[0]["kcc_id"] == "kcc-01"


def test_list_agent_references(client):
    _seed(client)
    _seed_kcad(client)
    r = client.get("/api/v1/agents/benzene/references")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["id"] == "kcad-pmid-1234567"
    assert rows[0]["pmid"] == "1234567"
    assert rows[0]["source"] == "kcad"


def test_list_agent_references_404(client):
    _seed(client)
    r = client.get("/api/v1/agents/unknown/references")
    assert r.status_code == 404


def test_list_references_filter_by_source(client):
    _seed(client)
    _seed_kcad(client)
    r = client.get("/api/v1/assays/references?source=kcad")
    assert r.status_code == 200
    assert all(row["source"] == "kcad" for row in r.json())
