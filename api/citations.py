"""BibTeX and RIS export helpers."""

from __future__ import annotations

from db.config import APP_CONTACT_EMAIL, APP_DEVELOPER
from db.models import Agent, Reference
from db.references import normalized_dois


def _canonical_doi(ref: Reference) -> str | None:
    dois = normalized_dois(ref.doi)
    return dois[0] if dois else None


def resource_bibtex(release_tag: str) -> str:
    return (
        "@misc{hkcc2026,\n"
        "  title = {hKCC: Key Characteristics of Human Carcinogens},\n"
        f"  version = {{{release_tag}}},\n"
        "  year = {2026},\n"
        f"  publisher = {{{APP_DEVELOPER}}},\n"
        "  license = {CC-BY-4.0},\n"
        f"  note = {{Contact: {APP_CONTACT_EMAIL}}}\n"
        "}\n"
    )


def resource_ris(release_tag: str) -> str:
    return (
        "TY  - DATA\n"
        "TI  - hKCC: Key Characteristics of Human Carcinogens\n"
        f"ET  - {release_tag}\n"
        "PY  - 2026\n"
        f"PB  - {APP_DEVELOPER}\n"
        f"N1  - Contact: {APP_CONTACT_EMAIL}\n"
        "Licence  - CC-BY-4.0\n"
        "ER  - \n"
    )


def agent_bibtex(agent: Agent, release_tag: str) -> str:
    key = agent.id.replace("-", "")
    cas = f", CAS {agent.cas}" if agent.cas else ""
    return (
        f"@misc{{hkcc_agent_{key},\n"
        f"  title = {{hKCC profile: {agent.name}{cas}}},\n"
        f"  howpublished = {{hKCC database}},\n"
        f"  version = {{{release_tag}}},\n"
        "  year = {2026}\n"
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
    canonical_doi = _canonical_doi(ref)
    if canonical_doi:
        lines.append(f"DO  - {canonical_doi}")
    lines.append("ER  - ")
    return "\n".join(lines) + "\n"
