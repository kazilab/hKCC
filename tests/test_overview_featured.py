"""Guards for the Overview landing page.

The featured block and the worked example used to key off hard-coded agent ids
(``benzene``, ``asbestos``, …). Those ids stopped existing when the IARC import
renamed them, so the section rendered empty and the example panel showed an
all-zero fingerprint labelled "BENZENE". Both are now derived from the data;
these tests fail if anything reintroduces a constant that can drift.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hkcc.app import data_client
from hkcc.app.utils.evidence import count_at_least, has_evidence, kcc_coverage

OVERVIEW = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages" / "1_Overview.py"


@pytest.fixture(autouse=True)
def _default_data_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


def _ranked() -> list[dict]:
    """Mirror the page's ranking: counts at successive thresholds, never a sum.

    The 0-4 scale is ordinal, so summing scores is not meaningful — see
    ``total_evidence``'s docstring for a worked counterexample.
    """
    agents, _ = data_client.agents_with_evidence()
    scored = [a for a in agents if has_evidence(a.get("evidence", {}))]
    return sorted(
        scored,
        key=lambda a: (
            kcc_coverage(a.get("evidence", {})),
            count_at_least(a.get("evidence", {}), 3),
            count_at_least(a.get("evidence", {}), 4),
            a.get("name", ""),
        ),
        reverse=True,
    )


def test_featured_block_is_not_empty():
    """The landing page must show featured agents, not a 'no matches' caption."""
    assert len(_ranked()) >= 6


def test_featured_agents_all_resolve_and_carry_evidence():
    for agent in _ranked()[:6]:
        assert agent["id"], "featured agent must have an id"
        assert has_evidence(agent["evidence"]), f"{agent['id']} has no evidence"


def test_worked_example_has_real_evidence():
    """The 'EXAMPLE ·' panel must never render an all-zero fingerprint."""
    example = _ranked()[0]
    assert has_evidence(example["evidence"])
    assert kcc_coverage(example["evidence"]) > 0
    # Regression: benzene rendered an all-zero fingerprint because the id lookup missed.
    assert example["id"] == "benzene-iarc"
    assert kcc_coverage(example["evidence"]) == 10
    assert count_at_least(example["evidence"], 4) == 7


def test_overview_has_no_hardcoded_agent_id_list():
    """A literal FEATURED id list is what broke this page; keep it gone."""
    source = OVERVIEW.read_text(encoding="utf-8")
    assert "FEATURED = [" not in source
    assert not re.search(r'by_id\.get\(\s*"[a-z0-9-]+"\s*\)', source), (
        "Overview must not look up an agent by a hard-coded id"
    )


def test_ranking_never_uses_a_sum_of_ordinal_scores():
    """Summing 0-4 scores implies interval spacing the derivation does not support.

    Concretely it also adds one per assessed cell, because both count-derived
    tracks map ``count -> count + 1``. So breadth inflates the total: 2,4-D sums
    to 14 against cyclophosphamide's 13, while cyclophosphamide is stronger at
    every threshold. Ranking must therefore compare counts, not sums.
    """
    source = OVERVIEW.read_text(encoding="utf-8")
    ranking = source.split("def _rank_key", 1)[1].split("\n\n\n", 1)[0]
    assert "total_evidence" not in ranking, "ranking must not sum ordinal scores"
    assert "count_at_least" in ranking


def test_the_sum_really_does_invert_the_threshold_ordering():
    """Guards the claim in total_evidence's docstring with live data."""
    agents, _ = data_client.agents_with_evidence()
    by_id = {a["id"]: a for a in agents}
    a, b = by_id.get("24d"), by_id.get("cyclophosphamide")
    if not (a and b):
        pytest.skip("reference agents not present in this dataset")
    assert sum(a["evidence"].values()) > sum(b["evidence"].values())
    assert count_at_least(a["evidence"], 3) < count_at_least(b["evidence"], 3)
    assert count_at_least(a["evidence"], 4) < count_at_least(b["evidence"], 4)
