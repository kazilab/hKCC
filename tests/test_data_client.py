import os

import pytest

from app.data_client import DataSource, get_data_source, list_kccs


@pytest.fixture(autouse=True)
def _force_mockup(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    from app import data_client

    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()
    mockup_store = __import__("app.mockup_store", fromlist=["load"])
    mockup_store.load.cache_clear()


def test_mockup_source_without_env():
    assert get_data_source() is DataSource.MOCKUP


def test_list_kccs_mockup():
    kccs = list_kccs()
    assert len(kccs) == 14
    assert kccs[0]["id"] == "kcc-01"
