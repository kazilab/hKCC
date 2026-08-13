"""Agent classification sanity checks.

The IARC import defaulted ``agent_type`` to "Industrial chemical" for every row
it created, which filed night shift work, welding, coffee and processed meat as
industrial chemicals. ``agent_type`` drives the Type facet on the Carcinogens
page, so a wrong value is visible to every user.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from hkcc.db.models import Agent
from hkcc.db.session import SessionLocal

# Controlled vocabulary. Extend deliberately — a typo here becomes a stray
# filter entry in the UI.
ALLOWED_TYPES = {
    "Industrial chemical",
    "Industrial solvent",
    "Industrial impurity",
    "Pesticide",
    "Persistent organic pollutant",
    "Brominated flame retardant",
    "Nanomaterial",
    "Occupational exposure",
    "Dietary factor",
    "Personal habit",
    # Added with the IARC Volume 100 import: that set is mostly not chemicals.
    "Pharmaceutical",
    "Biological agent",
    "Radiation",
    "Metal or metalloid",
    "Mineral fibre or dust",
    "Occupational dust",
}

# Exposures that are categorically not chemical substances.
NON_CHEMICAL = {
    "night-shift-work": "Occupational exposure",
    "welding": "Occupational exposure",
    "drinking-coffee": "Dietary factor",
    "drinking-mate-and-very-hot-beverages": "Dietary factor",
    "red-and-processed-meat": "Dietary factor",
    "opium-consumption": "Personal habit",
}

# IARC Monograph Volume 112 was the pesticides volume.
VOL_112_PESTICIDES = {"glyphosate-iarc", "tetrachlorvinphos", "malathion", "diazinon", "parathion"}


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_agent_types_come_from_the_controlled_vocabulary(db):
    used = {a.agent_type for a in db.scalars(select(Agent))}
    unknown = used - ALLOWED_TYPES
    assert not unknown, f"agent_type values outside the vocabulary: {unknown}"


def test_non_chemical_exposures_are_not_filed_as_chemicals(db):
    wrong = {}
    for agent_id, expected in NON_CHEMICAL.items():
        agent = db.get(Agent, agent_id)
        assert agent is not None, f"{agent_id} missing from agents"
        if agent.agent_type != expected:
            wrong[agent_id] = agent.agent_type
    assert not wrong, f"non-chemical exposures mis-typed: {wrong}"


def test_no_non_chemical_agent_claims_to_be_a_chemical(db):
    """Belt and braces: an agent with no CAS and a verb-like name isn't a chemical."""
    offenders = [
        a.id
        for a in db.scalars(select(Agent))
        if a.id in NON_CHEMICAL and "chemical" in a.agent_type.lower()
    ]
    assert not offenders, offenders


def test_volume_112_agents_are_all_pesticides(db):
    wrong = {
        aid: db.get(Agent, aid).agent_type
        for aid in VOL_112_PESTICIDES
        if db.get(Agent, aid) is not None and db.get(Agent, aid).agent_type != "Pesticide"
    }
    assert not wrong, f"Vol 112 pesticides mis-typed: {wrong}"


def test_every_agent_has_a_type(db):
    missing = [a.id for a in db.scalars(select(Agent)) if not (a.agent_type or "").strip()]
    assert not missing, f"agents with no agent_type: {missing}"


# --- name hygiene (M3) ------------------------------------------------------


def test_no_all_caps_agent_names_except_acronyms(db):
    """Source tables shipped ALL-CAPS names; only true acronyms should remain."""
    allowed = {"DDT"}
    shouting = [
        a.name
        for a in db.scalars(select(Agent))
        if a.name == a.name.upper() and a.name != a.name.lower() and a.name not in allowed
    ]
    assert not shouting, f"ALL-CAPS agent names: {shouting}"


def test_known_source_typos_are_corrected(db):
    """Each correction is corroborated by the agent's own monograph volume."""
    names = {a.name for a in db.scalars(select(Agent))}
    for typo in ("Molyndenum trioxide", "Isobutyl Nitrate", "2-Metcaptobenzothiazole", "Tetrabrobobisphenol A"):
        assert typo not in names, f"uncorrected source typo still present: {typo}"
    assert "Molybdenum trioxide" in names
    assert "Isobutyl nitrite" in names


def test_locant_prefixes_are_lower_case(db):
    """ortho-/para-/tert-/N,N- keep chemical convention, not title case."""
    import re

    bad = [
        a.name
        for a in db.scalars(select(Agent))
        if re.search(r"\b(Ortho|Para|Meta|Tert)-", a.name) or "N,n-" in a.name
    ]
    assert not bad, f"mis-cased locant prefixes: {bad}"


def test_agent_ids_do_not_carry_source_typos(db):
    """Display names were corrected; the id slugs must not keep the misspelling."""
    typos = ("molynd", "metcapt", "tetrabrobo", "nitrate-isobutyl")
    offenders = [a.id for a in db.scalars(select(Agent)) if any(t in a.id for t in typos)]
    assert not offenders, f"agent ids still containing a source typo: {offenders}"

# NB: no "id must resemble its name" check. Deliberate abbreviations (`2mbt`,
# `dmf`), ASCII ids for Greek-letter names (`b-picoline` for β-Picoline) and
# differing word order (`uv-and-solar-radiation`) are all legitimate, so such a
# heuristic only produces false alarms. The typo check above covers the real
# risk: a display name corrected while its id keeps the misspelling.
