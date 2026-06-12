"""CORS allowlist behaviour."""

import pytest

from db import config as db_config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("HKCC_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("HKCC_RELEASE_TAG", raising=False)


def test_allowed_origins_uses_env_list(monkeypatch):
    monkeypatch.setenv("HKCC_ALLOWED_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("HKCC_RELEASE_TAG", "prod")
    assert db_config.allowed_origins() == ["https://a.example", "https://b.example"]


def test_allowed_origins_dev_default_wildcard(monkeypatch):
    monkeypatch.setenv("HKCC_RELEASE_TAG", "dev")
    assert db_config.allowed_origins() == ["*"]


def test_allowed_origins_prod_default_closed(monkeypatch):
    monkeypatch.setenv("HKCC_RELEASE_TAG", db_config.APP_VERSION)
    assert db_config.allowed_origins() == []
