"""The scoring rules must be published in-app, and must match the data.

The Methodology page documented the KCAD assay library only. The derivation
rules — the scientific product — lived solely in ``docs/KCC_EVIDENCE_RULES.md``,
which ships in neither the wheel (``package-data`` is ``data/*.db`` and
``py.typed``) nor the Streamlit deployment. So a reader could rank agents by
score without ever meeting the rules that produced them, or the two caveats that
most affect interpretation:

* **Label offset** — every source label maps one rung up, so an hKCC 4 comes
  from a source label of *Strong* but an hKCC 3 comes from *Moderate*.
* **data_role** — most Track A cells are marked "Not used", meaning the IARC
  working group did not use that data; almost all of those still score 2-4
  (protective overrides are the exception).

These tests assert the rules are reachable in the app and that every number the
page states is reproduced from the shipped rows.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from sqlalchemy import select

from hkcc.app import data_client
from hkcc.db import evidence_rules as rules
from hkcc.db.models import Evidence, IarcMonographKcStrength
from hkcc.db.session import SessionLocal

PAGE = Path(__file__).resolve().parents[1] / "hkcc" / "app" / "pages" / "9a_Methodology.py"


@pytest.fixture(autouse=True)
def _db_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


@pytest.fixture(scope="module")
def stats() -> dict:
    db = SessionLocal()
    try:
        return rules.evidence_rule_stats(db)
    finally:
        db.close()


def test_track_a_mapping_reproduces_every_shipped_score():
    """The published mapping must actually explain the data, protective aside."""
    db = SessionLocal()
    try:
        strengths = {(s.agent_id, s.kcc_id): s for s in db.scalars(select(IarcMonographKcStrength))}
        evidence = [e for e in db.scalars(select(Evidence)) if e.source_track == "10yr-iarc"]
    finally:
        db.close()

    mismatched = []
    for cell in evidence:
        strength = strengths.get((cell.agent_id, cell.kcc_id))
        if not strength:
            continue
        expected = rules.TRACK_A_MAP[strength.strength_label]
        if cell.score != expected and cell.direction != "protective":
            mismatched.append((cell.agent_id, cell.kcc_id, strength.strength_label, cell.score))
    assert not mismatched, f"Track A mapping does not explain these cells: {mismatched[:5]}"


def test_the_label_offset_is_real_and_stated():
    """If the mapping ever became identity, the caveat would be a lie."""
    assert rules.TRACK_A_MAP == {"Strong": 4, "Moderate": 3, "Weak": 2}
    assert "one rung up" in rules.LABEL_OFFSET_CAVEAT
    # The offset means no source label maps to hKCC 1.
    assert 1 not in rules.TRACK_A_MAP.values()


def test_track_b_scores_are_the_count_plus_one(stats):
    assert rules.TRACK_B_MAP == {count: count + 1 for count in (1, 2, 3)}
    assert len(rules.PRIMARY_SYSTEMS) == 3


def test_the_counts_the_page_prints_come_from_the_rows(stats):
    db = SessionLocal()
    try:
        evidence = list(db.scalars(select(Evidence)))
        strengths = {(s.agent_id, s.kcc_id) for s in db.scalars(select(IarcMonographKcStrength))}
    finally:
        db.close()
    ten_year = [e for e in evidence if e.source_track == "10yr-iarc"]

    assert stats["total_cells"] == len(evidence)
    assert stats["by_track"] == dict(Counter(e.source_track for e in evidence))
    assert stats["track_a_rows"] == sum(1 for e in ten_year if (e.agent_id, e.kcc_id) in strengths)
    assert stats["track_b_rows"] == len(ten_year) - stats["track_a_rows"]
    assert stats["zero_cells"] == sum(1 for e in evidence if e.score == 0)
    assert stats["protective_cells"] == sum(1 for e in evidence if e.direction == "protective")
    assert sum(stats["data_roles"].values()) == stats["track_a_rows"]
    assert sum(stats["track_a_labels"].values()) == stats["track_a_rows"]


def test_the_data_role_caveat_is_not_hypothetical(stats):
    """Most 'Not used' cells still score 2-4; protective overrides score 0."""
    assert stats["data_roles"].get("Not used", 0) > 0
    assert stats["not_used_share"] >= 50, "the caveat is framed as the common case"
    assert stats["not_used_score_ge_2"] > 0, "the common case of positive Not-used scores vanished"
    assert stats["not_used_score_ge_2"] + stats["not_used_score_0"] == stats["data_roles"]["Not used"]
    assert stats["not_used_score_0"] == stats["label_overridden_by_direction"]
    assert set(stats["data_roles"]) <= set(rules.DATA_ROLE_MEANING), (
        "a data_role appears in the data that the page does not explain"
    )


def test_label_outruns_primary_residual_is_counted_and_explained(stats):
    """Track A can score positive without a primary Yes; that residual is published."""
    assert stats["label_outruns_primary"] > 0
    assert "outrun" in rules.LABEL_OUTRUNS_PRIMARY_CAVEAT
    allowed = {"unspecified", "negative", "equivocal"}
    assert set(stats["label_outruns_by_direction"]) <= allowed
    assert sum(stats["label_outruns_by_direction"].values()) == stats["label_outruns_primary"]
    source = PAGE.read_text(encoding="utf-8")
    assert "label_outruns_primary" in source, "Methodology must surface the residual"


def test_label_counts_are_not_silently_conflated_with_score_counts(stats):
    """Two Weak-labelled cells score 0; the page must say so rather than imply 63 twos."""
    assert stats["label_overridden_by_direction"] > 0
    source = PAGE.read_text(encoding="utf-8")
    assert "label_overridden_by_direction" in source


def test_the_page_publishes_the_rules_without_reading_the_docs_folder():
    """docs/ is not packaged, so a file read would fail for pip and Cloud users."""
    source = PAGE.read_text(encoding="utf-8")
    assert "KCC_EVIDENCE_RULES.md" in source, "the full document should still be linked"
    assert "open(" not in source and "read_text" not in source, (
        "the page must not read the unpackaged docs/ directory at runtime"
    )


def test_the_rendered_page_states_both_caveats_and_both_tracks():
    testing = pytest.importorskip("streamlit.testing.v1")
    app = testing.AppTest.from_file(str(PAGE), default_timeout=120)
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]

    assert [t.label for t in app.tabs][:1] == ["Evidence scoring"], (
        "scoring is the primary content; KCAD is the secondary tab"
    )
    text = "\n".join([w.value for w in app.warning] + [i.value for i in app.info] + [c.value for c in app.caption])
    assert "one rung up" in text, "label offset caveat missing"
    assert "Not used" in text, "data_role caveat missing"
    assert "ordinal" in text, "the ordinal-scale warning must be here too"
    assert "Do not compare across tracks" in text
    assert "outrun" in text.lower() or "primary" in text.lower(), (
        "the label-outruns-primary residual must be visible on the page"
    )

    # Every rule table must render; a type error silently drops one.
    assert len(app.dataframe) == 5, f"expected 5 rule tables, got {len(app.dataframe)}"


def test_both_data_paths_serve_the_same_rules():
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as real:
        api = real.get("/api/v1/methodology/evidence-rules").json()
    assert api == data_client.get_evidence_rules()
