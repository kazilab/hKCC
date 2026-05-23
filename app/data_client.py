"""Fetch hKCC data from API, PostgreSQL, or bundled mockup (data.js)."""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app import mockup_store
from db.models import (
    KCC,
    Agent,
    AgentReference,
    Assay,
    AssayAnnotation,
    AssayKCC,
    Evidence,
    KcadAbbreviation,
    KcadColumnDefinition,
    Reference,
)
from db.session import SessionLocal

API_BASE = os.environ.get("API_BASE_URL", "").rstrip("/")


class DataSource(StrEnum):
    API = "api"
    DATABASE = "database"
    MOCKUP = "mockup"


def _api_configured() -> bool:
    return bool(API_BASE)


@lru_cache(maxsize=1)
def _api_healthy() -> bool:
    if not _api_configured():
        return False
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=3.0)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def _db_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL", "").strip())


@lru_cache(maxsize=1)
def _db_healthy() -> bool:
    if not _db_configured():
        return False
    try:
        db = SessionLocal()
        try:
            db.execute(select(KCC).limit(1))
            return True
        finally:
            db.close()
    except SQLAlchemyError:
        return False


@lru_cache(maxsize=1)
def get_data_source() -> DataSource:
    if _api_healthy():
        return DataSource.API
    if _db_healthy():
        return DataSource.DATABASE
    return DataSource.MOCKUP


def data_source_label() -> str:
    src = get_data_source()
    if src is DataSource.API:
        return f"API · {API_BASE}"
    if src is DataSource.DATABASE:
        return "PostgreSQL"
    return "Bundled demo data (set DATABASE_URL or API_BASE_URL in Streamlit secrets)"


def _get(path: str) -> Any:
    r = httpx.get(f"{API_BASE}/api/v1{path}", timeout=15.0)
    r.raise_for_status()
    return r.json()


def _mock() -> dict[str, Any]:
    return mockup_store.load()


def get_kcc(kcc_id: str) -> dict | None:
    for k in list_kccs():
        if k["id"] == kcc_id:
            return k
    return None


def list_kccs() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        return _get("/kccs")
    if src is DataSource.MOCKUP:
        return _mock()["kccs"]
    db = SessionLocal()
    try:
        rows = db.scalars(select(KCC).order_by(KCC.n)).all()
        return [
            {
                "id": k.id,
                "n": k.n,
                "title": k.title,
                "short": k.short,
                "description": k.description,
                "mechanism": k.mechanism,
                "icon": k.icon,
                "is_extended": k.is_extended,
                "examples": [],
            }
            for k in rows
        ]
    finally:
        db.close()


def list_agents() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        return _get("/agents")
    if src is DataSource.MOCKUP:
        return [{k: v for k, v in a.items() if k != "evidence"} for a in _mock()["agents"]]
    db = SessionLocal()
    try:
        rows = db.scalars(select(Agent).options(selectinload(Agent.sites)).order_by(Agent.name)).all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "cas": a.cas or "—",
                "iarc_group": a.iarc_group or "—",
                "agent_type": a.agent_type,
                "summary": a.summary,
                "sites": [s.site for s in a.sites],
                "monograph_volume": a.monograph_volume,
                "monograph_pub_year": a.monograph_pub_year,
                "evaluation_year": a.evaluation_year,
                "source_ref_id": a.source_ref_id,
            }
            for a in rows
        ]
    finally:
        db.close()


def get_matrix() -> dict:
    src = get_data_source()
    if src is DataSource.API:
        return _get("/matrix")
    if src is DataSource.MOCKUP:
        return _mock()["matrix"]
    db = SessionLocal()
    try:
        kccs = list(db.scalars(select(KCC).order_by(KCC.n)))
        kcc_ids = [k.id for k in kccs]
        agents = db.scalars(select(Agent).options(selectinload(Agent.evidence_rows)).order_by(Agent.name)).all()
        rows = []
        for agent in agents:
            score_map = {e.kcc_id: e.score for e in agent.evidence_rows}
            rows.append(
                {
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "iarc_group": agent.iarc_group,
                    "scores": {kid: score_map.get(kid, 0) for kid in kcc_ids},
                }
            )
        return {"kcc_ids": kcc_ids, "rows": rows}
    finally:
        db.close()


def agents_with_evidence() -> tuple[list[dict], list[dict]]:
    kccs = list_kccs()
    src = get_data_source()
    if src is DataSource.MOCKUP:
        agents = [dict(a) for a in _mock()["agents"]]
        return agents, kccs
    agents = list_agents()
    matrix = get_matrix()
    by_id = {r["agent_id"]: r for r in matrix["rows"]}
    enriched = []
    for a in agents:
        row = by_id.get(a["id"], {})
        scores = row.get("scores", {})
        enriched.append({**a, "evidence": scores, "iarc_group": a.get("iarc_group") or row.get("iarc_group")})
    return enriched, kccs


def get_agent(agent_id: str) -> dict | None:
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get(f"/agents/{agent_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    if src is DataSource.MOCKUP:
        for a in _mock()["agents"]:
            if a["id"] == agent_id:
                ev = a.get("evidence", {})
                return {
                    **{k: v for k, v in a.items() if k != "evidence"},
                    "evidence": [
                        {"kcc_id": kid, "score": score, "n_refs": 1 if score > 0 else 0, "reference_ids": []}
                        for kid, score in ev.items()
                    ],
                }
        return None
    db = SessionLocal()
    try:
        agent = db.scalar(
            select(Agent)
            .where(Agent.id == agent_id)
            .options(
                selectinload(Agent.sites),
                selectinload(Agent.evidence_rows).selectinload(Evidence.citations),
            )
        )
        if not agent:
            return None
        evidence = [
            {
                "kcc_id": e.kcc_id,
                "score": e.score,
                "n_refs": e.n_refs,
                "reference_ids": [c.reference_id for c in e.citations],
            }
            for e in agent.evidence_rows
        ]
        return {
            "id": agent.id,
            "name": agent.name,
            "cas": agent.cas or "—",
            "iarc_group": agent.iarc_group or "—",
            "agent_type": agent.agent_type,
            "summary": agent.summary,
            "last_review": agent.last_review.isoformat() if agent.last_review else None,
            "sites": [s.site for s in agent.sites],
            "evidence": evidence,
        }
    finally:
        db.close()


def agents_for_kcc(kcc_id: str, *, min_score: int = 2) -> list[dict]:
    """Agents with evidence >= min_score on the given KCC, sorted by score desc."""
    agents, _ = agents_with_evidence()
    linked = []
    for a in agents:
        ev = a.get("evidence", {})
        if isinstance(ev, list):
            ev = {e["kcc_id"]: e["score"] for e in ev}
        score = ev.get(kcc_id, 0)
        if score >= min_score:
            linked.append({**a, "kcc_score": score})
    return sorted(linked, key=lambda x: x["kcc_score"], reverse=True)


def assays_for_kcc(kcc_id: str) -> list[dict]:
    return [a for a in list_assays() if kcc_id in a.get("kcc_ids", [])]


def references_for_kcc(kcc_id: str) -> list[dict]:
    """References linked to this KCC; includes foundational refs with no specific kcc_ids."""
    refs = list_references()
    foundational_tags = {"Foundational", "Methodology", "Review", "Database"}
    out = []
    for r in refs:
        kids = r.get("kcc_ids", [])
        tags = set(r.get("tags", []))
        if kcc_id in kids:
            out.append(r)
        elif not kids and tags & foundational_tags:
            out.append(r)
    return out


def evidence_for_agent(agent_id: str) -> list[dict]:
    """Per-cell evidence with resolved reference records."""
    agent = get_agent(agent_id)
    if not agent:
        return []
    refs_by_id = {r["id"]: r for r in list_references()}
    foundational = refs_by_id.get("smith2016")
    rows = agent.get("evidence", [])
    if isinstance(rows, dict):
        rows = [
            {"kcc_id": kid, "score": score, "n_refs": 0, "reference_ids": []}
            for kid, score in rows.items()
        ]
    enriched = []
    for e in rows:
        ref_ids = list(e.get("reference_ids", []))
        refs = [refs_by_id[rid] for rid in ref_ids if rid in refs_by_id]
        if not refs and foundational and e.get("score", 0) > 0:
            refs = [foundational]
            ref_ids = [foundational["id"]]
        enriched.append(
            {
                "kcc_id": e["kcc_id"],
                "score": e["score"],
                "n_refs": e.get("n_refs", len(refs)),
                "reference_ids": ref_ids,
                "refs": refs,
            }
        )
    return enriched


def agent_evidence_map(agent: dict, kcc_ids: list[str] | None = None) -> dict[str, int]:
    if isinstance(agent.get("evidence"), dict):
        return agent["evidence"]
    if isinstance(agent.get("evidence"), list):
        return {e["kcc_id"]: e["score"] for e in agent["evidence"]}
    return {}


def kcc_stats(db: Session | None = None) -> dict[str, dict[str, int]]:
    if get_data_source() is DataSource.MOCKUP:
        return _mock()["stats"]
    if db is None:
        db = SessionLocal()
        close = True
    else:
        close = False
    try:
        carc_counts = dict(
            db.execute(
                select(Evidence.kcc_id, func.count())
                .where(Evidence.score > 0)
                .group_by(Evidence.kcc_id)
            ).all()
        )
        assay_counts = dict(db.execute(select(AssayKCC.kcc_id, func.count()).group_by(AssayKCC.kcc_id)).all())
        return {
            kid: {"carc_count": carc_counts.get(kid, 0), "assay_count": assay_counts.get(kid, 0)}
            for kid in [r[0] for r in db.execute(select(KCC.id)).all()]
        }
    finally:
        if close:
            db.close()


def list_assays() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        return _get("/assays")
    if src is DataSource.MOCKUP:
        return [{**a, "source": "mockup", "granularity": "assay"} for a in _mock()["assays"]]
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(Assay)
            .options(
                selectinload(Assay.kcc_links),
                selectinload(Assay.kc_subgroups),
                selectinload(Assay.study_designs),
            )
            .order_by(Assay.name)
        ).all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "name_alt": a.name_alt,
                "type": a.type,
                "target": a.target,
                "throughput": a.throughput,
                "oecd_tg": a.oecd_tg or "—",
                "notes": a.notes or "",
                "source": a.source,
                "granularity": a.granularity,
                "source_ref_id": a.source_ref_id,
                "kcc_ids": [link.kcc_id for link in a.kcc_links],
                "subgroups": [
                    {"kcc_id": sg.kcc_id, "subgroup": sg.subgroup}
                    for sg in a.kc_subgroups
                ],
                "study_designs": [
                    {"kcc_id": sd.kcc_id, "design": sd.design, "source": sd.source}
                    for sd in a.study_designs
                ],
            }
            for a in rows
        ]
    finally:
        db.close()


def list_references() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        return _get("/assays/references")
    if src is DataSource.MOCKUP:
        return [{**r, "source": "mockup", "pmid": None} for r in _mock()["references"]]
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(Reference)
            .options(selectinload(Reference.tags), selectinload(Reference.kcc_links))
            .order_by(Reference.year.desc().nullslast())
        ).all()
        return [
            {
                "id": r.id,
                "year": r.year,
                "authors": r.authors,
                "title": r.title,
                "journal": r.journal,
                "vol": r.vol or "",
                "doi": r.doi or "—",
                "pmid": r.pmid,
                "citations": r.citations or 0,
                "source": r.source,
                "article_id": r.article_id,
                "url": r.url,
                "tags": [t.tag for t in r.tags],
                "kcc_ids": [lk.kcc_id for lk in r.kcc_links],
            }
            for r in rows
        ]
    finally:
        db.close()


def references_for_agent(agent_id: str) -> list[dict]:
    """KCAD-derived references linked to an agent via `agent_references`.

    Returns ``[]`` in MOCKUP mode (no AgentReference rows in `data.js`).
    """
    src = get_data_source()
    if src is DataSource.MOCKUP:
        return []
    if src is DataSource.API:
        try:
            return _get(f"/agents/{agent_id}/references")
        except httpx.HTTPError:
            return []
    db = SessionLocal()
    try:
        rows = db.execute(
            select(Reference, AgentReference.source)
            .join(AgentReference, AgentReference.reference_id == Reference.id)
            .where(AgentReference.agent_id == agent_id)
            .order_by(Reference.year.desc().nullslast())
        ).all()
        return [
            {
                "id": r.id,
                "year": r.year,
                "authors": r.authors,
                "title": r.title,
                "journal": r.journal,
                "vol": r.vol or "",
                "doi": r.doi or "—",
                "pmid": r.pmid,
                "citations": r.citations or 0,
                "source": r.source,
                "link_source": ar_source,
            }
            for (r, ar_source) in rows
        ]
    finally:
        db.close()


def annotations_for_assay(assay_id: str, *, limit: int = 50) -> list[dict]:
    """Per-study annotations for a KCAD assay (from `assay_annotations`)."""
    src = get_data_source()
    if src is DataSource.MOCKUP:
        return []
    if src is DataSource.API:
        try:
            return _get(f"/assays/{assay_id}/annotations?limit={limit}")
        except httpx.HTTPError:
            return []
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(AssayAnnotation)
            .where(AssayAnnotation.assay_id == assay_id)
            .order_by(AssayAnnotation.id)
            .limit(limit)
        ).all()
        return [
            {
                "id": a.id,
                "kcc_id": a.kcc_id,
                "secondary_kcc_id": a.secondary_kcc_id,
                "secondary_kc_raw": a.secondary_kc_raw,
                "reference_id": a.reference_id,
                "agent_id": a.agent_id,
                "kc_subgroup": a.kc_subgroup,
                "kc_subgroup2": a.kc_subgroup2,
                "effect": a.effect,
                "assay_endpoint": a.assay_endpoint,
                "assay_endpoint2": a.assay_endpoint2,
                "assay_endpoint3": a.assay_endpoint3,
                "biomarker": a.biomarker,
                "method2": a.method2,
                "stimulant_activation_agent": a.stimulant_activation_agent,
                "target_cell": a.target_cell,
                "organism": a.organism,
                "species": a.species,
                "mammalian": a.mammalian,
                "tissue": a.tissue,
                "tissue2": a.tissue2,
                "cell_type": a.cell_type,
                "immortalized": a.immortalized,
                "cell_format": a.cell_format,
                "design": a.design,
                "design_transgenic": a.design_transgenic,
                "monograph_num": a.monograph_num,
                "monograph_chem": a.monograph_chem,
                "oecd_tg": a.oecd_tg,
                "cebp_ref_idx": a.cebp_ref_idx,
            }
            for a in rows
        ]
    finally:
        db.close()


def list_assays_count() -> int:
    return len(list_assays())


def list_references_count() -> int:
    return len(list_references())


def list_abbreviations() -> list[dict]:
    """KCAD abbreviation glossary (STable3)."""
    src = get_data_source()
    if src is DataSource.MOCKUP:
        return []
    if src is DataSource.API:
        try:
            return _get("/methodology/abbreviations")
        except httpx.HTTPError:
            return []
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(KcadAbbreviation).order_by(KcadAbbreviation.abbreviation)
        ).all()
        return [
            {"abbreviation": r.abbreviation, "expansion": r.expansion}
            for r in rows
        ]
    finally:
        db.close()


def list_column_definitions() -> list[dict]:
    """KCAD column data dictionary (STable2)."""
    src = get_data_source()
    if src is DataSource.MOCKUP:
        return []
    if src is DataSource.API:
        try:
            return _get("/methodology/columns")
        except httpx.HTTPError:
            return []
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(KcadColumnDefinition).order_by(KcadColumnDefinition.column_name)
        ).all()
        return [
            {"column_name": r.column_name, "definition": r.definition}
            for r in rows
        ]
    finally:
        db.close()


def get_source_paper() -> dict | None:
    """The KCAD source publication (Rigutto et al. 2025) as a Reference row.

    Returns a hard-coded fallback in mockup mode so the citation card still
    renders without a DB.
    """
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/methodology/source")
        except httpx.HTTPError:
            return None
    if src is DataSource.DATABASE:
        db = SessionLocal()
        try:
            paper = db.get(Reference, "kcad-paper-rigutto-2025")
            if paper is None:
                return None
            return {
                "id": paper.id,
                "year": paper.year,
                "authors": paper.authors,
                "title": paper.title,
                "journal": paper.journal,
                "vol": paper.vol,
                "doi": paper.doi,
                "article_id": paper.article_id,
                "url": paper.url,
            }
        finally:
            db.close()
    # MOCKUP fallback — embedded citation.
    return {
        "id": "kcad-paper-rigutto-2025",
        "year": 2025,
        "authors": "Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT",
        "title": "Mapping assays to the key characteristics of carcinogens to support decision-making",
        "journal": "Database (Oxford)",
        "vol": "2025",
        "doi": "10.1093/database/baaf026",
        "article_id": "baaf026",
        "url": "https://doi.org/10.1093/database/baaf026",
    }


def api_base_url() -> str:
    return API_BASE or "http://localhost:8000"
