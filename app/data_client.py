"""Fetch hKCC data from API, PostgreSQL, or bundled mockup (data.js)."""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app import mockup_store
from db.models import Agent, Assay, AssayKCC, Evidence, KCC, Reference
from db.session import SessionLocal

API_BASE = os.environ.get("API_BASE_URL", "").rstrip("/")


class DataSource(str, Enum):
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
        return _mock()["assays"]
    db = SessionLocal()
    try:
        rows = db.scalars(select(Assay).options(selectinload(Assay.kcc_links)).order_by(Assay.name)).all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "target": a.target,
                "throughput": a.throughput,
                "oecd_tg": a.oecd_tg or "—",
                "notes": a.notes or "",
                "kcc_ids": [link.kcc_id for link in a.kcc_links],
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
        return _mock()["references"]
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
                "citations": r.citations or 0,
                "tags": [t.tag for t in r.tags],
                "kcc_ids": [lk.kcc_id for lk in r.kcc_links],
            }
            for r in rows
        ]
    finally:
        db.close()


def list_assays_count() -> int:
    return len(list_assays())


def list_references_count() -> int:
    return len(list_references())


def api_base_url() -> str:
    return API_BASE or "http://localhost:8000"
