"""Sentry init is best-effort: never raise if DSN missing or SDK absent."""

import sys

import pytest

from api import observability


@pytest.fixture(autouse=True)
def _reset():
    observability._INITIALISED = False
    yield
    observability._INITIALISED = False


def test_init_returns_false_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert observability.init_sentry("test") is False


def test_init_returns_false_when_sdk_missing(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.io/1")
    monkeypatch.setitem(sys.modules, "sentry_sdk", None)
    assert observability.init_sentry("test") is False
