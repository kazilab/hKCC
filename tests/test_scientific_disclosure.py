"""Claims about provenance, attribution and evidence bars must survive review.

Five findings from external scientific review, each verified against the shipped
data before it was fixed:

* The methodology described 144 score-0 cells as holding evidence "only in
  supplementary model systems". Only 32 hold a positive call; 112 hold none.
* Per-model-system calls were presented as extracted verbatim from IARC
  Monographs. They are Rusyn & Wright's retrospective author coding; only the
  standardized strength label and data role are Working Group outputs.
* CD5 requires a functional coupling assay and explicitly excludes connexin
  expression alone — yet the connexin assay was tagged ``functional``.
* The domains API returned bare assay ids, discarding the ``evidence_level`` a
  consumer needs to apply that exclusion.
* The document claimed per-agent counts are internally consistent because no
  agent mixes tracks. 62 of 73 mix *derivations* within the ten-year track.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from hkcc.app import data_client
from hkcc.db import evidence_rules as rules
from hkcc.db.models import CandidateDomain, CandidateDomainAssay
from hkcc.db.session import SessionLocal

ROOT = Path(__file__).resolve().parents[1]
RULES_DOC = (ROOT / "docs" / "KCC_EVIDENCE_RULES.md").read_text(encoding="utf-8")
ROADMAP = ROOT / "docs" / "ROADMAP.md"


@pytest.fixture(autouse=True)
def _db_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    data_client._api_healthy.cache_clear()
    data_client._db_healthy.cache_clear()
    data_client.get_data_source.cache_clear()


# ── attribution ──────────────────────────────────────────────────────────────


def test_model_system_calls_are_not_attributed_to_iarc_working_groups():
    page = (ROOT / "hkcc" / "app" / "pages" / "9b_IARC_Matrix.py").read_text(encoding="utf-8")
    assert "verbatim from IARC Monograph" not in page, "calls presented as IARC determinations"
    assert "not IARC Working Group" in page
    assert "Track B rests on author coding" in rules.TRACK_B_ATTRIBUTION
    assert "author coding" in RULES_DOC or "retrospective coding" in RULES_DOC


def test_working_group_attribution_is_reserved_for_strength_and_data_role():
    """Those two really are extracted Working Group outputs; the calls are not."""
    assert "working group" in rules.DATA_ROLE_MEANING["Not used"].lower()
    assert "strength label and data role" in rules.TRACK_B_ATTRIBUTION


def test_the_attribution_caveat_is_served_on_both_paths():
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as client:
        api = client.get("/api/v1/methodology/evidence-rules").json()
    assert "track_b_attribution" in api["caveats"]
    assert api["caveats"] == data_client.get_evidence_rules()["caveats"]


# ── within-track mixing ──────────────────────────────────────────────────────


def test_the_within_track_mixing_figure_is_computed_not_asserted():
    stats = data_client.get_evidence_rules()["stats"]
    assert stats["ten_year_agents"] == 73
    assert stats["agents_mixing_derivations"] == 62
    assert "62 of 73 agents" in RULES_DOC


def test_the_doc_no_longer_claims_per_agent_counts_are_internally_consistent():
    assert "are internally consistent. Ranking" not in RULES_DOC, (
        "the retired claim is back: mixing derivations makes counts non-uniform"
    )
    assert "mix *derivations* inside the 10-year track" in RULES_DOC


# ── candidate domain evidence bars ───────────────────────────────────────────


def test_no_assay_is_tagged_above_the_level_its_domain_excludes():
    """CD5 excludes connexin expression alone, so that assay is not functional."""
    db = SessionLocal()
    try:
        domains = {d.id: d for d in db.scalars(select(CandidateDomain))}
        links = list(db.scalars(select(CandidateDomainAssay)))
    finally:
        db.close()
    cd5 = next(d for d in domains.values() if d.code == "CD5")
    assert "does not establish loss of functional coupling" in cd5.key_exclusions
    connexin = next(link for link in links if link.assay_id == "kcc-gjic-connexin")
    assert connexin.evidence_level == "descriptive", "an assay excluded by its own domain must not be tagged functional"
    # The functional readout the bar actually asks for is still present.
    scrape = next(link for link in links if link.assay_id == "kcc-gjic-scrape-load")
    assert scrape.evidence_level == "functional"


def test_evidence_level_survives_both_data_paths():
    from fastapi.testclient import TestClient

    from hkcc.api.main import app

    with TestClient(app) as client:
        api = {d["code"]: d for d in client.get("/api/v1/domains").json()}
    local = {d["code"]: d for d in data_client.list_candidate_domains()}
    assert api["CD5"]["assay_links"] == local["CD5"]["assay_links"]
    levels = {link["evidence_level"] for link in api["CD5"]["assay_links"]}
    assert levels == {"descriptive", "functional"}, "the API is flattening the evidence level"


def test_domains_are_presented_as_provisional():
    """The bars cannot be enforced: no dose, duration or cytotoxicity is stored."""
    from hkcc.db.models import AssayAnnotation

    absent = {"dose", "duration", "route", "comparator", "cytotoxicity", "replication"}
    assert not (absent & set(AssayAnnotation.__table__.columns.keys())), (
        "an exposure/quality field exists now — the provisional wording can be revisited"
    )
    page = (ROOT / "hkcc" / "app" / "pages" / "2_Browse_KCCs.py").read_text(encoding="utf-8")
    assert "**Provisional.**" in page
    assert "cannot yet be" in page


def test_every_domain_status_is_still_candidate():
    db = SessionLocal()
    try:
        statuses = {d.status for d in db.scalars(select(CandidateDomain))}
    finally:
        db.close()
    assert statuses == {"candidate"}


# ── classification conflicts ─────────────────────────────────────────────────


def test_the_group_conflicts_are_detected_from_the_data():
    conflicts = data_client.iarc_group_conflicts()
    assert set(conflicts) == {"aldrin", "dieldrin", "ortho-nitroanisole"}
    assert conflicts["ortho-nitroanisole"] == {"agent_row": "2B", "source_table": ["2A"]}


def test_combined_exposures_name_the_component_classifications():
    from hkcc.db.config import COMBINED_EXPOSURES

    assert set(COMBINED_EXPOSURES) == {
        "red-and-processed-meat",
        "drinking-mate-and-very-hot-beverages",
    }
    assert "Group 1" in COMBINED_EXPOSURES["red-and-processed-meat"]
    assert "Group 3" in COMBINED_EXPOSURES["drinking-mate-and-very-hot-beverages"]

    db = SessionLocal()
    try:
        from hkcc.db.models import Agent

        present = {a.id for a in db.scalars(select(Agent))}
    finally:
        db.close()
    assert set(COMBINED_EXPOSURES) <= present, "a flagged agent id no longer exists"


@pytest.mark.parametrize(
    ("agent_id", "phrase"),
    [
        ("aldrin", "Conflicting IARC classification"),
        ("red-and-processed-meat", "Combined exposure"),
        ("drinking-mate-and-very-hot-beverages", "Combined exposure"),
    ],
)
def test_the_warnings_reach_the_agent_page(agent_id, phrase):
    testing = pytest.importorskip("streamlit.testing.v1")
    page = ROOT / "hkcc" / "app" / "pages" / "4_Agent_Detail.py"
    app = testing.AppTest.from_file(str(page), default_timeout=180)
    app.session_state["agent_id"] = agent_id
    app.run()
    assert not app.exception, [str(e.value) for e in app.exception]
    assert phrase in "\n".join(w.value for w in app.warning)


def test_an_unaffected_agent_carries_no_classification_warning():
    testing = pytest.importorskip("streamlit.testing.v1")
    page = ROOT / "hkcc" / "app" / "pages" / "4_Agent_Detail.py"
    app = testing.AppTest.from_file(str(page), default_timeout=180)
    app.session_state["agent_id"] = "benzene-iarc"
    app.run()
    text = "\n".join(w.value for w in app.warning)
    assert "Conflicting IARC classification" not in text
    assert "Combined exposure" not in text


# ── the roadmap is the index for what was deferred ───────────────────────────


def test_the_roadmap_records_every_deferred_finding():
    text = ROADMAP.read_text(encoding="utf-8")
    for topic in (
        "derivation_method",
        "positive coverage",
        "red-and-processed-meat",
        "ortho-nitroanisole",
        "cytotoxicity",
        "agent_sites",
    ):
        assert topic in text, f"deferred item not recorded in the roadmap: {topic}"
    assert "docs/ROADMAP.md" in (ROOT / "README.md").read_text(encoding="utf-8")
