"""The Overview's "how to read this" text must describe the actual data.

It drifted badly. It named only the 10-year retrospective as the source of the
0-4 score, silently omitting the 342 Volume 100 cells — 40% of the matrix — and
it told readers that "a score of 0 can mean negative evidence *or* no
evaluation", which is the opposite of what every other part of the app does: an
unevaluated pair carries no cell at all.

Prose can be wrong without any test failing, so the numbers it quotes are read
from the data at render time and the retired claims are asserted gone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hkcc.app import data_client

OVERVIEW = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages" / "1_Overview.py"
SOURCE = OVERVIEW.read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _default_data_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


def test_the_score_zero_claim_is_gone():
    """ "0 can mean ... no evaluation" contradicts the sparse-matrix design."""
    assert "no evaluation" not in SOURCE
    assert "A score of 0 can mean" not in SOURCE


def test_both_tracks_are_named():
    """Describing only Rusyn 2024 hid 40% of the scores."""
    assert "Rusyn" in SOURCE
    assert "Krewski" in SOURCE, "the Volume 100 track must be named, not just implied"


def test_the_quoted_cell_counts_are_read_from_the_data():
    """Hard-coded totals are how the previous text went stale."""
    body = SOURCE.split('eyebrow">How to read this', 1)[1]
    for literal in ("502", "342", "844", "866", "1710", "1,710"):
        assert literal not in body, f"{literal} is hard-coded in the blurb; derive it instead"
    assert "n_tenyr" in body
    assert "n_vol100" in body
    assert "n_unassessed" in body


def test_the_rendered_page_states_the_derived_numbers():
    """Executes the page, rather than grepping it.

    The blurb reads variables defined 200 lines earlier; a source check would
    pass even if that wiring raised NameError at render time.
    """
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(OVERVIEW), default_timeout=120)
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]

    text = "\n".join(m.value for m in app.markdown)
    counts = data_client.evidence_track_counts()
    assert f"**{counts['10yr-iarc']} cells**" in text
    assert f"**{counts['vol100-kc']} cells**" in text
    assert "Rusyn" in text and "Krewski" in text
    assert "no evaluation" not in text
    assert "A score of 0 is a finding, not a blank" in text


def test_track_counts_helper_matches_the_evidence_table():
    from sqlalchemy import func, select

    from hkcc.db.models import Evidence
    from hkcc.db.session import SessionLocal

    counts = data_client.evidence_track_counts()
    db = SessionLocal()
    try:
        assert sum(counts.values()) == db.scalar(select(func.count()).select_from(Evidence))
        for track, n in counts.items():
            expected = db.scalar(select(func.count()).select_from(Evidence).where(Evidence.source_track == track))
            assert n == expected, f"{track}: blurb would say {n}, database holds {expected}"
    finally:
        db.close()
    assert set(counts) == {"10yr-iarc", "vol100-kc"}


def test_the_unassessed_total_the_blurb_will_quote_is_correct():
    counts = data_client.evidence_track_counts()
    agents = data_client.list_agents()
    kccs = data_client.list_kccs()
    n_possible = len(agents) * len(kccs)
    n_unassessed = n_possible - sum(counts.values())
    from sqlalchemy import func, select

    from hkcc.db.models import KCC, Agent
    from hkcc.db.session import SessionLocal

    assert n_unassessed > 0, "the blurb explains a sparse matrix; this one is full"
    # Checked against the tables rather than a literal, so a data update needs
    # no edit here -- only the prose this protects.
    db = SessionLocal()
    try:
        n_agents = db.scalar(select(func.count()).select_from(Agent))
        n_kccs = db.scalar(select(func.count()).select_from(KCC))
    finally:
        db.close()
    assert n_possible == n_agents * n_kccs
    assert n_unassessed + sum(counts.values()) == n_possible
