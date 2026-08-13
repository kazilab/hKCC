import pytest

from hkcc.app.data_client import (
    DataSource,
    _correct_reference,
    get_data_source,
    list_kccs,
    unique_literature_references,
)


@pytest.fixture(autouse=True)
def _force_no_data(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'missing.db'}")
    monkeypatch.delenv("API_BASE_URL", raising=False)
    from hkcc.app import data_client

    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


def test_no_data_source_when_sqlite_file_missing():
    assert get_data_source() is DataSource.NO_DATA


def test_list_kccs_without_data_source_is_empty():
    assert list_kccs() == []


def test_corrects_de_coster_year_typo():
    bad_year = 2000 + 88
    ref = {
        "id": "kcad-doi-example",
        "year": bad_year,
        "title": f"De Coster {bad_year}  Paz-y-Mino 2007",
    }

    assert _correct_reference(ref)["year"] == 2008
    assert _correct_reference(ref)["title"] == "De Coster 2008  Paz-y-Mino 2007"


def test_unique_literature_references_hides_placeholders_and_collapses_duplicates():
    refs = [
        {
            "id": "a",
            "year": 2020,
            "title": "Same Paper",
            "authors": "A",
            "journal": "J",
            "doi": None,
            "tags": ["KCAD"],
            "kcc_ids": ["KC1"],
        },
        {
            "id": "b",
            "year": 2020,
            "title": "  Same   Paper ",
            "authors": "B",
            "journal": "J",
            "doi": "10.1/example",
            "tags": ["Review"],
            "kcc_ids": ["KC2"],
        },
        {
            "id": "placeholder",
            "year": 2021,
            "title": "—",
            "authors": "Unknown",
            "journal": "—",
            "tags": [],
            "kcc_ids": [],
        },
    ]

    visible = unique_literature_references(refs)

    assert [r["id"] for r in visible] == ["b"]
    assert visible[0]["tags"] == ["KCAD", "Review"]
    assert visible[0]["kcc_ids"] == ["KC1", "KC2"]
