import pytest

from app.data_client import DataSource, _correct_reference, get_data_source, list_kccs


@pytest.fixture(autouse=True)
def _force_no_data(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'missing.db'}")
    monkeypatch.delenv("API_BASE_URL", raising=False)
    from app import data_client

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
