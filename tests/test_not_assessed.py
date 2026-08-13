"""'Not assessed' must stay distinguishable from a score of 0.

Only 844 of the 171 x 10 possible (agent, KCC) pairs were ever evaluated. The
matrix used to fill the other 866 with 0 — a positive claim of negative evidence
— including in the CSV that users download and cite. Score 0 is a real finding
(assessed; the primary model systems were negative); a blank is the absence of
one, and the two must never render alike.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import func, select

from hkcc.app import data_client
from hkcc.app.components import radar as radar_module
from hkcc.app.components.radar import radar_plot_html
from hkcc.app.utils.evidence import ev_legend_html, fingerprint_html
from hkcc.db.models import KCC, Agent, Evidence
from hkcc.db.session import SessionLocal


@pytest.fixture(autouse=True)
def _default_data_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


def test_matrix_omits_pairs_that_were_never_evaluated():
    db = SessionLocal()
    try:
        n_evidence = db.scalar(select(func.count()).select_from(Evidence))
        n_agents = db.scalar(select(func.count()).select_from(Agent))
        n_kccs = db.scalar(select(func.count()).select_from(KCC))
    finally:
        db.close()

    matrix = data_client.get_matrix()
    emitted = sum(len(row["scores"]) for row in matrix["rows"])
    assert emitted == n_evidence, "matrix emits cells that have no evidence row"
    assert emitted < n_agents * n_kccs, "test data no longer exercises the sparse case"


def test_api_matrix_is_sparse(client):
    """The API must not invent zeros either."""
    from hkcc.db.models import Evidence as E
    from hkcc.db.session import get_db

    db = next(client.app.dependency_overrides[get_db]())
    db.add(KCC(id="kcc-01", n=1, title="T", short="S", description="d", mechanism="m", icon="helix"))
    db.add(KCC(id="kcc-02", n=2, title="T2", short="S2", description="d", mechanism="m", icon="grid"))
    db.add(Agent(id="a1", name="A1", agent_type="Industrial chemical", summary="s"))
    db.flush()
    db.add(E(agent_id="a1", kcc_id="kcc-01", score=3, n_refs=0))
    db.commit()
    db.close()

    rows = client.get("/api/v1/matrix").json()["rows"]
    scores = rows[0]["scores"]
    assert scores == {"kcc-01": 3}, f"unevaluated kcc-02 should be absent, got {scores}"


def test_fingerprint_marks_missing_cells_differently():
    filled = fingerprint_html([0, 1, 2], ["a", "b", "c"])
    missing = fingerprint_html([None, 1, 2], ["a", "b", "c"])
    assert filled != missing
    assert "not assessed" in missing
    assert "dashed" in missing
    assert "not assessed" not in filled


def test_fingerprint_keeps_protective_off_the_positive_ramp():
    """Protective must not paint as ordinary score-0 beige (the list-view bug)."""
    from hkcc.app.theme import THEME

    zero = fingerprint_html([0, 2], ["a", "b"])
    protective = fingerprint_html([0, 2], ["a", "b"], directions=["protective", None])
    assert protective != zero
    assert "protective" in protective
    assert "&#8595;" in protective
    assert THEME["teal"] in protective
    # The second cell is still an ordinary score of 2 on the heat ramp.
    assert "b: 2/4" in protective
    assert "a: 0/4" not in protective


def test_radar_does_not_draw_an_unassessed_characteristic_as_zero():
    """The radar polygon used to send missing values to the origin.

    ``evidence.get(k["id"], 0)`` made a gap indistinguishable from a tested
    negative, and because the collapsed vertex dragged the outline inward it
    overstated "no mechanism" in the most prominent part of the figure.
    """
    kccs = [{"id": f"kcc-{i:02d}", "n": i, "short": f"S{i}"} for i in range(1, 11)]
    scored = radar_plot_html(kccs, {"kcc-01": 0, "kcc-02": 3})
    gapped = radar_plot_html(kccs, {"kcc-02": 3})

    assert scored != gapped, "a score of 0 and an unassessed cell render identically"
    # KCC-01 is the cell under test: assessed-and-negative in one, absent in the other.
    assert "S1: 0/4" in scored
    assert "S1: not assessed" not in scored
    assert "S1: not assessed" in gapped
    assert "S1: 0/4" not in gapped

    # Every chart here has gaps (KCC-03..10), so dashed spokes are expected in
    # both; what must differ is how many.
    assert gapped.count("stroke-dasharray") == scored.count("stroke-dasharray") + 1


def test_radar_draws_every_assessed_characteristic_when_nothing_is_missing():
    kccs = [{"id": f"kcc-{i:02d}", "n": i, "short": f"S{i}"} for i in range(1, 11)]
    full = radar_plot_html(kccs, {f"kcc-{i:02d}": 2 for i in range(1, 11)})
    assert "not assessed" not in full
    assert "stroke-dasharray" not in full, "no axis is missing, so no spoke should be dashed"


def test_radar_source_never_defaults_a_missing_score_to_zero():
    source = Path(radar_module.__file__).read_text(encoding="utf-8")
    assert not re.search(r"evidence\.get\([^)]*,\s*0\s*\)", source), (
        "a missing characteristic must stay None, not become a score of 0"
    )


def test_radar_keeps_protective_cells_off_the_positive_ramp():
    """Same reasoning as the matrix: teal mark, never the 0-4 heat ramp."""
    from hkcc.app.theme import THEME

    kccs = [{"id": f"kcc-{i:02d}", "n": i, "short": f"S{i}"} for i in range(1, 11)]
    html = radar_plot_html(kccs, {"kcc-01": 0}, directions={"kcc-01": "protective"})
    assert THEME["teal"] in html
    assert "S1: protective" in html
    # A protective cell is assessed, so it is not reported as a gap...
    assert "S1: not assessed" not in html
    # ...and it is not painted on the positive 0-4 ramp.
    assert "S1: 0/4" not in html


def test_radar_interpolates_nothing_between_characteristics():
    """The ten KCCs are unordered categories; no line may span two of them.

    A connected polygon implies the space between KCC-01 and KCC-02 carries
    meaning. Sectors are drawn per characteristic and share no edge.
    """
    kccs = [{"id": f"kcc-{i:02d}", "n": i, "short": f"S{i}"} for i in range(1, 11)]
    html = radar_plot_html(kccs, {"kcc-01": 4, "kcc-03": 2})
    assert "<polygon" not in html, "a polygon interpolates across unassessed axes"
    assert "<polyline" not in html


def test_legend_explains_the_not_assessed_state():
    legend = ev_legend_html()
    assert "not assessed" in legend
    assert "dashed" in legend


def test_the_documented_not_assessed_counts_still_match_the_database():
    """KCC_EVIDENCE_RULES.md quotes "N of the M possible pairs" — keep it true.

    These numbers were left behind by the 14-to-10 restructure and read
    "1,550 of the 2,394" against a database holding 866 of 1,710. Anyone
    checking the figures would have concluded the data was wrong, so the
    document is parsed here rather than trusted.
    """
    rules = Path(__file__).resolve().parents[1] / "docs" / "KCC_EVIDENCE_RULES.md"
    text = rules.read_text(encoding="utf-8")
    match = re.search(r"([\d,]+) of the ([\d,]+)\s*\n?\s*possible pairs", text)
    assert match, "the 'N of the M possible pairs' claim has moved or been reworded"
    claimed_missing, claimed_possible = (int(g.replace(",", "")) for g in match.groups())

    db = SessionLocal()
    try:
        n_agents = db.scalar(select(func.count()).select_from(Agent))
        n_kccs = db.scalar(select(func.count()).select_from(KCC))
        n_evidence = db.scalar(select(func.count()).select_from(Evidence))
    finally:
        db.close()

    assert claimed_possible == n_agents * n_kccs
    assert claimed_missing == n_agents * n_kccs - n_evidence


def test_agents_with_evidence_does_not_pad_with_zeros():
    agents, kccs = data_client.agents_with_evidence()
    padded = [a["id"] for a in agents if len(a["evidence"]) == len(kccs) and 0 in a["evidence"].values()]
    sparse = [a for a in agents if len(a["evidence"]) < len(kccs)]
    assert sparse, "no agent has an unevaluated KCC — padding may have returned"
    for agent in agents:
        assert set(agent["evidence"]) <= {k["id"] for k in kccs}
    _ = padded
