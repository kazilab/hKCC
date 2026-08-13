"""Agent-level data integrity.

The KCAD and IARC imports were never reconciled, so the same substance appeared
twice under different ids — in one case (TCAB) with two different IARC groups.
Those rows have been merged; these tests fail if a future data update
reintroduces a duplicate or an agent row with nothing attached to it.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

import pytest
from sqlalchemy import func, select

from hkcc.db.models import (
    Agent,
    AgentReference,
    AssayAnnotation,
    Evidence,
    IarcMonographKcCall,
    IarcMonographKcStrength,
)
from hkcc.db.session import SessionLocal

# Substances IARC evaluates jointly with a salt or as a mixture. These are
# genuinely distinct entries, not duplicates, and are expected to coexist.
KNOWN_DISTINCT_FAMILIES = {
    "aniline",
    "orthoanisidine",
    "hydrazine",
    "aldrin",
    "dieldrin",
    "styrene",
}


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


# Greek letters distinguish real substances (alpha- vs beta-particle emitters,
# beta-picoline). Stripping them as "non-ASCII punctuation" merges distinct
# agents, so transliterate before folding.
_GREEK = {
    "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma", "\u03b4": "delta",
    "\u03bc": "mu", "\u03c9": "omega",
}


def _norm(name: str) -> str:
    s = (name or "").lower()
    for greek, latin in _GREEK.items():
        s = s.replace(greek, latin)
    s = unicodedata.normalize("NFKD", s)
    for ch in "\u02b9\u2019\u2032":
        s = s.replace(ch, "'")
    s = re.sub(r"\([^)]*\)", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def test_no_two_agents_share_a_cas(db):
    """A CAS number identifies one substance; two rows sharing one is a duplicate."""
    by_cas = defaultdict(list)
    for agent in db.scalars(select(Agent)):
        cas = (agent.cas or "").strip()
        if cas and "," not in cas:  # combined entries legitimately list several
            by_cas[cas].append(agent.id)
    dupes = {c: ids for c, ids in by_cas.items() if len(ids) > 1}
    assert not dupes, f"agents sharing a CAS number: {dupes}"


def test_no_two_agents_share_a_normalized_name(db):
    by_name = defaultdict(list)
    for agent in db.scalars(select(Agent)):
        by_name[_norm(agent.name)].append(agent.id)
    dupes = {n: ids for n, ids in by_name.items() if len(ids) > 1}
    assert not dupes, f"agents with the same normalized name: {dupes}"


def test_merged_duplicate_ids_are_gone(db):
    """Regression: these ids were duplicates of a surviving agent."""
    removed = [
        "2-metcaptobenzothiazole",
        "tetrabrobobisphenol-a",
        "3-3-4-4-tetrachloroazobenzene",
        "styrene-oxide",
        "cobalt-metal-without-tungsten-carbide-or-other-metal-alloys",
        "dieldrin-and-aldrin-metabolized-to-dieldrin",
    ]
    still_present = [i for i in removed if db.get(Agent, i) is not None]
    assert not still_present, f"merged/dropped agent ids reappeared: {still_present}"


def test_tcab_has_a_single_unambiguous_group(db):
    """TCAB was Group 2B in one source row and 2A in another."""
    tcab = db.get(Agent, "tcab")
    assert tcab is not None
    assert tcab.iarc_group == "2A"
    assert tcab.cas == "14047-09-7"


def test_merged_agents_carry_both_sources(db):
    """A merge must keep the KCAD literature and the IARC evidence together."""
    for agent_id in ("2mbt", "tbbpa", "tcab"):
        evidence = db.scalar(select(func.count()).select_from(Evidence).where(Evidence.agent_id == agent_id))
        refs = db.scalar(
            select(func.count()).select_from(AgentReference).where(AgentReference.agent_id == agent_id)
        )
        assert evidence > 0, f"{agent_id} lost its IARC evidence"
        assert refs > 0, f"{agent_id} lost its KCAD references"


def test_every_agent_has_something_attached(db):
    """An agent with no evidence, literature or annotations is an empty UI row."""
    empty = []
    for agent in db.scalars(select(Agent)):
        counts = [
            db.scalar(select(func.count()).select_from(t).where(t.agent_id == agent.id))
            for t in (Evidence, AgentReference, AssayAnnotation, IarcMonographKcCall, IarcMonographKcStrength)
        ]
        if not any(counts):
            empty.append(agent.id)
    assert not empty, f"agents with no linked data: {empty}"
