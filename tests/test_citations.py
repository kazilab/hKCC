"""Citations export — well-formed BibTeX / RIS."""

from types import SimpleNamespace

from api.citations import (
    agent_bibtex,
    reference_bibtex,
    reference_ris,
    resource_bibtex,
    resource_ris,
)
from db.config import APP_VERSION


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
