"""Controlled vocabularies quoted in the docs must match the enforced ones.

``DATABASE_TABLES.md`` listed ten ``agent_type`` values as "a controlled list,
enforced by tests/test_agent_types.py". The Volume 100 import added six more —
``Pharmaceutical``, ``Biological agent``, ``Radiation``, ``Metal or metalloid``,
``Mineral fibre or dust``, ``Occupational dust`` — and the paragraph was not
updated, so the documentation understated the vocabulary by a third while
citing the test as its authority.

Prose that names a closed set is a promise about the data. This test checks the
promise against both the enforced set and the shipped rows.
"""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select

from hkcc.db.models import Agent
from hkcc.db.session import SessionLocal
from tests.test_agent_types import ALLOWED_TYPES

DOC = Path(__file__).resolve().parents[1] / "docs" / "DATABASE_TABLES.md"


def _documented_types() -> set[str]:
    """Backticked values in the `agent_type` vocabulary paragraph."""
    text = DOC.read_text(encoding="utf-8")
    start = text.index("**`agent_type` vocabulary.**")
    end = text.index("The IARC import originally defaulted", start)
    section = text[start:end]
    # Structural filter rather than a list of exceptions to maintain: file
    # paths, module names and CONSTANT_NAMES all carry "/", "." or "_", and no
    # agent_type value does.
    return {token for token in re.findall(r"`([^`]+)`", section) if not any(ch in token for ch in "/._")}


def test_documented_agent_types_match_the_enforced_set():
    documented = _documented_types()
    missing = ALLOWED_TYPES - documented
    extra = documented - ALLOWED_TYPES
    assert not missing, f"documented vocabulary omits enforced types: {sorted(missing)}"
    assert not extra, f"documented vocabulary invents types the test rejects: {sorted(extra)}"


def test_every_documented_type_is_one_the_data_could_use():
    """A vocabulary entry nothing uses is worth knowing about too."""
    db = SessionLocal()
    try:
        in_use = {a.agent_type for a in db.scalars(select(Agent))}
    finally:
        db.close()
    assert in_use <= ALLOWED_TYPES, f"data uses undeclared types: {sorted(in_use - ALLOWED_TYPES)}"
    assert in_use <= _documented_types(), "the data uses a type the docs never mention"


def test_the_paragraph_still_points_at_its_source_of_truth():
    text = DOC.read_text(encoding="utf-8")
    assert "tests/test_agent_types.py" in text
    assert "ALLOWED_TYPES" in text


def test_readme_row_counts_match_the_database():
    """The README's headline figures are a promise about the shipped dataset.

    It advertised 1,170 references against 1,171 in the database. Small, but
    the counts are the first thing a reader checks, and this is the third
    documented figure in this repo to drift from the data it describes.
    """
    import re

    from sqlalchemy import func

    from hkcc.db.models import Assay, Evidence, Reference

    readme = (DOC.parent.parent / "README.md").read_text(encoding="utf-8")
    claim = re.search(
        r"(\d[\d,]*) agents, (\d[\d,]*) evidence cells, (\d[\d,]*) assays, (\d[\d,]*) references",
        readme,
    )
    assert claim, "the README headline counts have moved or been reworded"
    agents_c, evidence_c, assays_c, refs_c = (int(g.replace(",", "")) for g in claim.groups())

    db = SessionLocal()
    try:
        counts = {
            model: db.scalar(select(func.count()).select_from(model)) for model in (Agent, Evidence, Assay, Reference)
        }
    finally:
        db.close()
    assert agents_c == counts[Agent]
    assert evidence_c == counts[Evidence]
    assert assays_c == counts[Assay]
    assert refs_c == counts[Reference]
