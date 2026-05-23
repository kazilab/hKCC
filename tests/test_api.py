from api.main import app
from db.models import (
    KCC,
    Agent,
    AgentReference,
    Assay,
    AssayAnnotation,
    AssayKCC,
    AssayKcSubgroup,
    AssayStudyDesign,
    KcadAbbreviation,
    KcadColumnDefinition,
    Reference,
)
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


def _seed_supplementary(client):
    db = next(app.dependency_overrides[get_db]())
    db.add(
        Reference(
            id="kcad-paper-rigutto-2025",
            year=2025,
            authors="Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT",
            title="Mapping assays to the key characteristics of carcinogens",
            journal="Database (Oxford)",
            vol="2025",
            doi="10.1093/database/baaf026",
            article_id="baaf026",
            url="https://doi.org/10.1093/database/baaf026",
            source="kcad-paper",
        )
    )
    db.add(
        KcadAbbreviation(
            abbreviation="8-OHdG",
            expansion="8-hydroxy-2'-deoxyguanosine",
            source_ref_id="kcad-paper-rigutto-2025",
        )
    )
    db.add(
        KcadColumnDefinition(
            column_name="KC",
            definition="Primary key characteristic of carcinogens",
            source_ref_id="kcad-paper-rigutto-2025",
        )
    )
    db.add(
        AssayKcSubgroup(
            assay_id="kcad-ames-assay",
            kcc_id="kcc-01",
            subgroup="Gene mutation",
            source_ref_id="kcad-paper-rigutto-2025",
        )
    )
    db.add(
        AssayStudyDesign(
            assay_id="kcad-ames-assay",
            kcc_id="kcc-01",
            design="in_vitro",
            source="stable5",
            source_ref_id="kcad-paper-rigutto-2025",
        )
    )
    db.commit()
    db.close()


def test_get_source_paper(client):
    _seed(client)
    _seed_kcad(client)
    _seed_supplementary(client)
    r = client.get("/api/v1/methodology/source")
    assert r.status_code == 200
    paper = r.json()
    assert paper["id"] == "kcad-paper-rigutto-2025"
    assert paper["doi"] == "10.1093/database/baaf026"
    assert paper["article_id"] == "baaf026"


def test_list_abbreviations(client):
    _seed(client)
    _seed_kcad(client)
    _seed_supplementary(client)
    r = client.get("/api/v1/methodology/abbreviations")
    assert r.status_code == 200
    abbrevs = r.json()
    assert any(a["abbreviation"] == "8-OHdG" for a in abbrevs)


def test_get_abbreviation_by_key(client):
    _seed(client)
    _seed_kcad(client)
    _seed_supplementary(client)
    r = client.get("/api/v1/methodology/abbreviations/8-OHdG")
    assert r.status_code == 200
    assert r.json()["expansion"].startswith("8-hydroxy")


def test_list_columns(client):
    _seed(client)
    _seed_kcad(client)
    _seed_supplementary(client)
    r = client.get("/api/v1/methodology/columns")
    assert r.status_code == 200
    cols = r.json()
    assert any(c["column_name"] == "KC" for c in cols)


def test_assay_carries_subgroups_and_designs(client):
    _seed(client)
    _seed_kcad(client)
    _seed_supplementary(client)
    r = client.get("/api/v1/assays/kcad-ames-assay")
    assert r.status_code == 200
    a = r.json()
    assert a["subgroups"] == [{"kcc_id": "kcc-01", "subgroup": "Gene mutation"}]
    assert a["study_designs"] == [
        {"kcc_id": "kcc-01", "design": "in_vitro", "source": "stable5"}
    ]
    assert a["source_ref_id"] is None  # not set on this seeded row


def test_list_assays_filter_by_design(client):
    _seed(client)
    _seed_kcad(client)
    _seed_supplementary(client)
    r = client.get("/api/v1/assays?design=in_vitro")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["id"] == "kcad-ames-assay"
    # Filter out unrelated design → empty result.
    r2 = client.get("/api/v1/assays?design=in_silico")
    assert r2.json() == []


def test_list_assays_filter_by_subgroup(client):
    _seed(client)
    _seed_kcad(client)
    _seed_supplementary(client)
    r = client.get("/api/v1/assays?subgroup=Gene+mutation")
    assert r.status_code == 200
    assert len(r.json()) == 1
    r2 = client.get("/api/v1/assays?subgroup=DNA+adducts")
    assert r2.json() == []
