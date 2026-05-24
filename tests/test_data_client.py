import pytest

from app.data_client import DataSource, get_data_source, list_kccs


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
