"""The agent table's coverage denominator must come from the data.

It was hard-coded to 14 and survived the restructure that moved the four
extended characteristics into Layer 2 as candidate domains. Left alone it would
have rated every agent against ten real cells plus four that no longer exist and
never held a single evidence row — making the whole database look systematically
under-documented against an unreachable ideal.
"""

from sqlalchemy import func, select

from hkcc.app.components.agent_table import agent_table_html
from hkcc.app.theme import apply_theme
from hkcc.db.models import KCC
from hkcc.db.session import SessionLocal

apply_theme(inject=False)

SHORTS = [
    "Electrophilic",
    "Genotoxic",
    "DNA repair",
    "Epigenetic",
    "Oxidative",
    "Inflammation",
    "Immunosuppression",
    "Receptor",
    "Immortalization",
    "Proliferation",
]


def _row(**over):
    row = {
        "id": "benzene-iarc",
        "name": "Benzene",
        "cas": "71-43-2",
        "agent_type": "chemical",
        "iarc_group": "1",
        "sites": ["AML"],
        "scores": [4, 2, None, None, None, None, None, None, None, None],
        "evidence": {"kcc-01": 4, "kcc-02": 2},
    }
    row.update(over)
    return row


def test_agent_table_includes_name_and_link():
    html = agent_table_html([_row()])
    assert "Benzene" in html
    assert "agent_id=benzene-iarc" in html


def test_agent_table_renders_protective_in_the_fingerprint():
    """List view used to paint protective cells as ordinary score-0 beige."""
    from hkcc.app.theme import THEME

    dirs = [None] * 10
    dirs[0] = "protective"
    scores = [0] + [None] * 9
    html = agent_table_html(
        [_row(scores=scores, directions=dirs, evidence={"kcc-01": 0})],
        kcc_shorts=SHORTS,
    )
    assert "&#8595;" in html
    assert THEME["teal"] in html
    assert "protective" in html


def test_coverage_denominator_matches_the_reference_ontology():
    html = agent_table_html([_row()], kcc_shorts=SHORTS)
    assert "2/10" in html
    assert "/14" not in html, "coverage must not be scored against the retired 14-KCC set"


def test_denominator_is_derived_when_no_shorts_are_supplied():
    """The old fallback printed /14 regardless of the ontology in use."""
    html = agent_table_html([_row()])
    assert "2/10" in html
    assert "/14" not in html


def test_denominator_follows_the_ontology_rather_than_any_constant():
    """If the reference set ever changes size, the table must follow it."""
    eight = [None] * 8
    eight[0] = 3
    html = agent_table_html([_row(scores=eight, evidence={"kcc-01": 3})], kcc_shorts=SHORTS[:8])
    assert "1/8" in html


def test_unscored_agents_get_no_denominator_at_all():
    """ "0/10" would read as an assessed zero across every characteristic."""
    html = agent_table_html([_row(scores=[None] * 10, evidence={})], kcc_shorts=SHORTS)
    assert "not scored" in html
    assert "0/10" not in html


def test_the_shipped_ontology_really_is_ten():
    db = SessionLocal()
    try:
        assert db.scalar(select(func.count()).select_from(KCC)) == 10
    finally:
        db.close()
