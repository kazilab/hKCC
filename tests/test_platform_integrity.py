"""Platform-level defects found by external review, each verified before fixing.

* The annotations endpoint capped at 500 rows with no cursor. Five assays exceed
  it; the largest holds 7,874, so a consumer received 6% of the data with
  nothing in the response to say so.
* The shipped SQLite file carried 2 of the 5 constraints ``evidence`` declares.
  Every row was valid, but nothing prevented an invalid write.
* Literature de-duplication keyed on ``(year, title)`` and merged two distinct
  1981 papers with different DOIs, PMIDs and authors.
* ``reference_kccs`` is empty, so a fallback listed the same 14 framework papers
  on all ten KCC pages under "Anchoring publications".
* ``/health`` reported "ok" without touching the database — and the Streamlit
  client uses that probe to decide whether the API can serve reads.
* ``kcc_stats`` had no API branch, so an API-backed deployment opened the local
  SQLite file anyway.
* Two search widgets bound to ``?q=`` on one page each called ``st.rerun()``,
  producing an endless loop.
* A missing citation count rendered as "0 cites", which reads as a judgement.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from hkcc.app import data_client
from hkcc.db.models import Assay, AssayAnnotation, Evidence
from hkcc.db.session import SessionLocal, engine

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _db_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


@pytest.fixture(scope="module")
def api():
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as client:
        yield client


# ── annotation pagination ────────────────────────────────────────────────────


def test_the_largest_assay_can_be_retrieved_completely(api):
    db = SessionLocal()
    try:
        assay_id, expected = db.execute(
            select(AssayAnnotation.assay_id, func.count())
            .group_by(AssayAnnotation.assay_id)
            .order_by(func.count().desc())
            .limit(1)
        ).one()
    finally:
        db.close()
    assert expected > 500, "no assay exceeds the page cap — the test would be vacuous"

    seen, cursor, pages = [], 0, 0
    while True:
        page = api.get(f"/api/v1/assays/{assay_id}/annotations?limit=500&cursor={cursor}").json()
        assert page["total"] == expected, "total must reflect the whole result set, not the page"
        seen.extend(item["id"] for item in page["items"])
        pages += 1
        if not page["next_cursor"]:
            break
        cursor = page["next_cursor"]
        assert pages < 100, "cursor is not advancing"

    assert len(seen) == expected, f"retrieved {len(seen)} of {expected}"
    assert len(set(seen)) == expected, "pages overlap"
    assert seen == sorted(seen), "pagination is not stably ordered"


def test_truncation_is_visible_in_a_single_page(api):
    db = SessionLocal()
    try:
        assay_id = db.execute(
            select(AssayAnnotation.assay_id).group_by(AssayAnnotation.assay_id).order_by(func.count().desc()).limit(1)
        ).scalar_one()
    finally:
        db.close()
    page = api.get(f"/api/v1/assays/{assay_id}/annotations?limit=10").json()
    assert page["count"] == 10
    assert page["total"] > page["count"], "a truncated response must say so"
    assert page["next_cursor"], "a truncated response must be resumable"


def test_annotation_filters_narrow_the_total_too(api):
    assay_id = "kcad-bisulfite-conversion-converting-unmodified-cytosine-to-uracil-in-dna"
    unfiltered = api.get(f"/api/v1/assays/{assay_id}/annotations?limit=1").json()
    empty = api.get(f"/api/v1/assays/{assay_id}/annotations?limit=1&kcc_id=kcc-02").json()
    assert unfiltered["total"] > 0
    assert empty["total"] == 0, "the filter must apply to `total`, not only to the page"


def test_unknown_assay_is_404_not_an_empty_page(api):
    assert api.get("/api/v1/assays/does-not-exist/annotations").status_code == 404


# ── shipped constraints ──────────────────────────────────────────────────────


def test_the_shipped_database_carries_every_declared_constraint():
    from hkcc.db.schema_repair import missing_constraints

    missing = missing_constraints(engine, "evidence")
    assert not missing, f"constraints declared by the ORM but absent from SQLite: {sorted(missing)}"


def test_the_constraints_actually_reject_invalid_rows():
    """Present in the DDL is not the same as enforced."""
    import sqlite3

    from hkcc.db.config import get_settings

    path = get_settings().database_url.replace("sqlite:///", "")
    con = sqlite3.connect(path)
    try:
        for label, direction, track, score in (
            ("direction vocabulary", "sideways", "10yr-iarc", 2),
            ("protective must score 0", "protective", "10yr-iarc", 3),
            ("source_track vocabulary", "positive", "invented", 2),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(
                    "INSERT INTO evidence (agent_id,kcc_id,score,n_refs,direction,source_track) "
                    "VALUES ('benzene-iarc','kcc-01',?,0,?,?)",
                    (score, direction, track),
                )
            con.rollback()
    finally:
        con.close()


def test_the_rebuild_preserved_every_row():
    db = SessionLocal()
    try:
        assert db.scalar(select(func.count()).select_from(Evidence)) == 844
    finally:
        db.close()


# ── reference identity ───────────────────────────────────────────────────────


def test_distinct_works_are_not_merged_on_a_shared_title():
    refs = data_client.list_literature_references()
    hch = [r for r in refs if r.get("year") == 1981 and "hexachlorocyclohexane" in (r.get("title") or "").lower()]
    assert len(hch) == 2, "two 1981 papers with different DOIs must remain separate cards"
    assert len({r["doi"] for r in hch}) == 2


def test_no_literature_card_merges_conflicting_identifiers():
    from collections import defaultdict

    from hkcc.app.data_client import _literature_dedupe_key, _reference_identifiers

    groups = defaultdict(list)
    for ref in data_client.list_references():
        key = _literature_dedupe_key(ref)
        if key:
            groups[key].append(ref)
    for key, rows in groups.items():
        dois = {d for d, _ in map(_reference_identifiers, rows) if d}
        pmids = {p for _, p in map(_reference_identifiers, rows) if p}
        assert len(dois) <= 1, f"{key}: merges different DOIs {dois}"
        assert len(pmids) <= 1, f"{key}: merges different PMIDs {pmids}"


def test_kcc_pages_do_not_present_framework_papers_as_anchors():
    from hkcc.db.models import ReferenceKCC

    db = SessionLocal()
    try:
        linked = db.scalar(select(func.count()).select_from(ReferenceKCC))
    finally:
        db.close()
    anchors = {k["id"]: data_client.references_for_kcc(k["id"]) for k in data_client.list_kccs()}
    if linked == 0:
        assert all(not v for v in anchors.values()), "reference_kccs is empty, so no KCC has anchoring publications"
    assert data_client.framework_references(), "framework papers should still be offered separately"


# ── readiness, data source, small UI truths ──────────────────────────────────


def test_health_reports_the_database(api):
    body = api.get("/health").json()
    assert body["database"] == "ok"
    assert body["status"] == "ok"


def test_health_degrades_when_the_database_is_unreachable(api):
    import hkcc.db.session as session_module

    def boom():
        raise RuntimeError("database gone")

    original, session_module.SessionLocal = session_module.SessionLocal, boom
    try:
        response = api.get("/health")
        assert response.status_code == 503, "a dead database must not report healthy"
        assert response.json()["status"] == "degraded"
    finally:
        session_module.SessionLocal = original


def test_kcc_stats_never_opens_the_database_in_api_mode(monkeypatch):
    """An API-backed deployment must not touch the bundled SQLite file.

    Checked by behaviour, not by reading the source: `_open_db` is replaced with
    a function that fails the test if called, so the assertion holds regardless
    of how the branch is written.
    """

    def forbidden():
        raise AssertionError("kcc_stats opened the local database while API-backed")

    monkeypatch.setattr(data_client, "get_data_source", lambda: data_client.DataSource.API)
    monkeypatch.setattr(data_client, "_open_db", forbidden)
    monkeypatch.setattr(data_client, "list_kccs", lambda: [{"id": "kcc-01", "n": 1, "short": "S"}])
    monkeypatch.setattr(
        data_client,
        "get_matrix",
        lambda: {"rows": [{"agent_id": "a", "scores": {"kcc-01": 3}, "directions": {}}]},
    )
    monkeypatch.setattr(data_client, "list_assays", lambda: [{"id": "x", "kcc_ids": ["kcc-01"]}])

    stats = data_client.kcc_stats()
    assert stats == {"kcc-01": {"carc_count": 1, "assay_count": 1}}


def test_kcc_stats_api_branch_applies_the_same_positive_rule(monkeypatch):
    """Both paths must count positive cells at >= 2, not any non-zero score."""
    monkeypatch.setattr(data_client, "get_data_source", lambda: data_client.DataSource.API)
    monkeypatch.setattr(data_client, "_open_db", lambda: pytest.fail("opened the database"))
    monkeypatch.setattr(data_client, "list_kccs", lambda: [{"id": "kcc-01", "n": 1, "short": "S"}])
    monkeypatch.setattr(data_client, "list_assays", lambda: [])
    monkeypatch.setattr(
        data_client,
        "get_matrix",
        lambda: {
            "rows": [
                {"agent_id": "a", "scores": {"kcc-01": 1}, "directions": {}},  # below threshold
                {"agent_id": "b", "scores": {"kcc-01": 3}, "directions": {"kcc-01": "negative"}},
                {"agent_id": "c", "scores": {"kcc-01": 2}, "directions": {}},  # the only one counted
            ]
        },
    )
    assert data_client.kcc_stats()["kcc-01"]["carc_count"] == 1


def test_only_one_search_widget_per_page():
    """Two widgets bound to ?q= each rerun on mismatch — an endless loop."""
    testing = pytest.importorskip("streamlit.testing.v1")
    for name in ("2_Browse_KCCs", "3_Carcinogens", "6_Assays", "1_Overview"):
        app = testing.AppTest.from_file(str(ROOT / "hkcc" / "app" / "pages" / f"{name}.py"), default_timeout=180)
        app.run()
        assert not app.exception, [str(e.value) for e in app.exception]
        searches = [t for t in app.text_input if "search" in (t.label or "").lower()]
        assert len(searches) == 1, f"{name}: {len(searches)} search inputs bound to the same param"


def test_a_missing_citation_count_is_not_reported_as_zero():
    from hkcc.app.components.ref_card import ref_card_html
    from hkcc.app.theme import apply_theme

    apply_theme(inject=False)
    base = {"id": "r", "title": "T", "authors": "A", "journal": "J", "year": 2020}
    assert "cites n/a" in ref_card_html({**base, "citations": None})
    assert "0 cites" in ref_card_html({**base, "citations": 0}), "a real zero should still show"
    assert "12 cites" in ref_card_html({**base, "citations": 12})


# ── exports and accessibility ────────────────────────────────────────────────


def test_release_manifest_carries_row_counts_and_checksums(tmp_path, monkeypatch):
    monkeypatch.setenv("HKCC_EXPORT_DIR", str(tmp_path))
    import json

    from hkcc.pipelines.export_release import export_release

    out = export_release("manifest-check")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))

    db = SessionLocal()
    try:
        n_evidence = db.scalar(select(func.count()).select_from(Evidence))
        n_assays = db.scalar(select(func.count()).select_from(Assay))
    finally:
        db.close()
    assert manifest["tables"]["evidence"]["rows"] == n_evidence
    assert manifest["tables"]["assays"]["rows"] == n_assays
    assert manifest["total_rows"] > 0
    for entry in manifest["tables"].values():
        assert len(entry["csv_sha256"]) == 64, "every table needs a checksum"
    assert len(manifest["checksums"]) == 3, "each downloadable bundle needs a checksum"


def test_the_agent_export_keeps_direction_and_source():
    page = (ROOT / "hkcc" / "app" / "pages" / "3_Carcinogens.py").read_text(encoding="utf-8")
    assert "source_track" in page
    assert "_direction" in page, "the agent CSV drops the direction of every score"


def test_clickable_rows_are_reachable_by_keyboard():
    from hkcc.app.components.agent_table import agent_table_html
    from hkcc.app.theme import apply_theme

    apply_theme(inject=False)
    html = agent_table_html(
        [
            {
                "id": "a",
                "name": "A",
                "cas": "1",
                "agent_type": "x",
                "iarc_group": "1",
                "scores": [1],
                "evidence": {"k": 1},
                "sites": [],
            }
        ]
    )
    assert 'tabindex="0"' in html, "rows are not focusable"
    assert 'role="button"' in html, "rows have no accessible role"
    assert "onkeydown" in html, "rows cannot be activated from the keyboard"
    assert "aria-label" in html


def test_theme_colours_meet_wcag_aa_for_body_text():
    from hkcc.app.theme import DARK_THEME, PAPER_THEME

    def luminance(value: str) -> float:
        value = value.lstrip("#")
        channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    def contrast(fg: str, bg: str) -> float:
        a, b = luminance(fg), luminance(bg)
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)

    failures = []
    for name, theme in (("dark", DARK_THEME), ("light", PAPER_THEME)):
        for ground in ("paper", "paper2", "paper3"):
            for token in ("accent", "muted", "ink"):
                ratio = contrast(theme[token], theme[ground])
                if ratio < 4.5:
                    failures.append(f"{name}.{token} on {ground}: {ratio:.2f}:1")
    assert not failures, f"below WCAG AA (4.5:1) for body text: {failures}"
