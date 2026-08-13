"""BibTeX and RIS export helpers.

RIS tags are exactly two characters followed by two spaces, a hyphen and a
space. Anything else is skipped or rejected by reference managers, so the tag
set here is limited to real RIS fields.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hkcc.db.config import APP_CONTACT_EMAIL, APP_DEVELOPER, APP_TITLE
from hkcc.db.models import Agent, Reference
from hkcc.db.references import normalized_dois

RESOURCE_URL = "https://github.com/kazilab/hkcc"


def _canonical_doi(ref: Reference) -> str | None:
    dois = normalized_dois(ref.doi)
    return dois[0] if dois else None


def _year() -> str:
    """Release year. Derived, so citations do not hard-code a year that ages."""
    return str(datetime.now(UTC).year)


def resource_bibtex(release_tag: str) -> str:
    year = _year()
    return (
        f"@misc{{hkcc{year},\n"
        f"  title = {{hKCC: {APP_TITLE}}},\n"
        f"  author = {{{APP_DEVELOPER}}},\n"
        f"  version = {{{release_tag}}},\n"
        f"  year = {{{year}}},\n"
        f"  howpublished = {{\\url{{{RESOURCE_URL}}}}},\n"
        f"  publisher = {{{APP_DEVELOPER}}},\n"
        "  note = {Data licensed CC-BY-4.0. Contact: " + APP_CONTACT_EMAIL + "}\n"
        "}\n"
    )


def resource_ris(release_tag: str) -> str:
    year = _year()
    lines = [
        "TY  - DATA",
        f"TI  - hKCC: {APP_TITLE}",
        f"AU  - {APP_DEVELOPER}",
        f"PY  - {year}",
        f"ET  - {release_tag}",
        f"PB  - {APP_DEVELOPER}",
        f"UR  - {RESOURCE_URL}",
        "N1  - Data licensed CC-BY-4.0",
        f"N1  - Contact: {APP_CONTACT_EMAIL}",
        "ER  - ",
    ]
    return "\n".join(lines) + "\n"


def agent_bibtex(agent: Agent, release_tag: str) -> str:
    key = agent.id.replace("-", "")
    year = _year()
    cas = f", CAS {agent.cas}" if agent.cas else ""
    return (
        f"@misc{{hkcc_agent_{key},\n"
        f"  title = {{hKCC profile: {agent.name}{cas}}},\n"
        f"  author = {{{APP_DEVELOPER}}},\n"
        f"  howpublished = {{\\url{{{RESOURCE_URL}}}}},\n"
        f"  version = {{{release_tag}}},\n"
        f"  year = {{{year}}}\n"
        "}\n"
    )


def reference_bibtex(ref: Reference) -> str:
    key = ref.id.replace("-", "")
    canonical_doi = _canonical_doi(ref)
    doi = f",\n  doi = {{{canonical_doi}}}" if canonical_doi else ""
    return (
        f"@article{{{key},\n"
        f"  author = {{{ref.authors}}},\n"
        f"  title = {{{ref.title}}},\n"
        f"  journal = {{{ref.journal}}},\n"
        f"  year = {{{ref.year or ''}}},\n"
        f"  volume = {{{ref.vol or ''}}}{doi}\n"
        "}\n"
    )


def reference_ris(ref: Reference) -> str:
    lines = [
        "TY  - JOUR",
        f"AU  - {ref.authors}",
        f"TI  - {ref.title}",
        f"JO  - {ref.journal}",
    ]
    if ref.year:
        lines.append(f"PY  - {ref.year}")
    if ref.vol:
        lines.append(f"VL  - {ref.vol}")
    canonical_doi = _canonical_doi(ref)
    if canonical_doi:
        lines.append(f"DO  - {canonical_doi}")
        lines.append(f"UR  - https://doi.org/{canonical_doi}")
    lines.append("ER  - ")
    return "\n".join(lines) + "\n"
