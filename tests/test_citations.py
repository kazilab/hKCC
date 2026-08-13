"""Citations export — well-formed BibTeX / RIS."""

from types import SimpleNamespace

from hkcc.api.citations import (
    agent_bibtex,
    reference_bibtex,
    reference_ris,
    resource_bibtex,
    resource_ris,
)
from hkcc.db.config import APP_VERSION


def _braces_balanced(text: str) -> bool:
    depth = 0
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def test_resource_bibtex_well_formed():
    out = resource_bibtex(APP_VERSION)
    assert out.startswith("@misc{hkcc2026,")
    assert out.rstrip().endswith("}")
    assert _braces_balanced(out)


def test_agent_bibtex_well_formed():
    agent = SimpleNamespace(id="benzene-1", name="Benzene", cas="71-43-2")
    out = agent_bibtex(agent, APP_VERSION)
    assert "@misc{hkcc_agent_benzene1," in out
    assert "CAS 71-43-2" in out
    assert _braces_balanced(out)


def test_reference_bibtex_no_double_close():
    ref = SimpleNamespace(
        id="smith-2016",
        authors="Smith MT et al.",
        title="Key characteristics of carcinogens",
        journal="EHP",
        year=2016,
        vol="124(6)",
        doi="10.1289/ehp.1509912",
    )
    out = reference_bibtex(ref)
    # Regression: previously emitted '}}' at the end producing malformed BibTeX.
    assert not out.rstrip().endswith("}}")
    assert out.rstrip().endswith("}")
    assert _braces_balanced(out)
    assert "doi = {10.1289/ehp.1509912}" in out


def test_reference_ris_minimum_fields():
    ref = SimpleNamespace(
        id="x",
        authors="A",
        title="T",
        journal="J",
        year=2020,
        vol="1",
        doi=None,
    )
    out = reference_ris(ref)
    assert out.startswith("TY  - JOUR")
    assert out.rstrip().endswith("ER  -")


def test_resource_ris_has_tag_and_year():
    out = resource_ris(APP_VERSION)
    assert f"ET  - {APP_VERSION}" in out
    assert "PY  - 2026" in out
    assert "ER  -" in out


# --- RIS well-formedness -----------------------------------------------------

RIS_TAG = __import__("re").compile(r"^[A-Z][A-Z0-9]  - ")


def _ris_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


def test_resource_ris_every_line_is_a_valid_tag():
    """Regression: 'Licence  - CC-BY-4.0' is not a RIS tag (they are 2 chars)."""
    lines = _ris_lines(resource_ris("1.2.3"))
    bad = [ln for ln in lines if not RIS_TAG.match(ln)]
    assert not bad, f"malformed RIS lines: {bad}"
    assert lines[0] == "TY  - DATA"
    assert lines[-1].startswith("ER  -")


def test_resource_ris_has_author_and_url():
    text = resource_ris("1.2.3")
    assert any(ln.startswith("AU  - ") for ln in _ris_lines(text)), "no author line"
    assert any(ln.startswith("UR  - ") for ln in _ris_lines(text)), "no URL line"


def test_reference_ris_every_line_is_a_valid_tag():
    ref = SimpleNamespace(
        id="r1", authors="Smith MT", title="A title", journal="J", year=2016,
        vol="12", doi="10.1000/xyz", pmid=None,
    )
    lines = _ris_lines(reference_ris(ref))
    bad = [ln for ln in lines if not RIS_TAG.match(ln)]
    assert not bad, f"malformed RIS lines: {bad}"
    assert "DO  - 10.1000/xyz" in lines


def test_citations_do_not_hardcode_a_year():
    """The year was pinned to 2026 in the source."""
    from datetime import UTC, datetime

    year = str(datetime.now(UTC).year)
    assert f"year = {{{year}}}" in resource_bibtex("1.0")
    assert f"PY  - {year}" in resource_ris("1.0")


def test_resource_bibtex_carries_author_and_url():
    out = resource_bibtex("1.0")
    assert "author = {" in out
    assert "\\url{" in out
