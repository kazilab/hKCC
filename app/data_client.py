"""Fetch hKCC data from API or fall back to direct DB."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from db.models import KCC, Agent, Assay, AssayKCC, Evidence, Reference
from db.session import SessionLocal

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")


def _clear_api_cache() -> None:
    _use_api.cache_clear()


@lru_cache(maxsize=1)
def _use_api() -> bool:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=2.0)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def _get(path: str) -> Any:
    r = httpx.get(f"{API_BASE}/api/v1{path}", timeout=10.0)
    r.raise_for_status()
    return r.json()


def list_kccs() -> list[dict]:
    if _use_api():
        return _get("/kccs")
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
    if _use_api():
        return _get("/agents")
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
    if _use_api():
        return _get("/matrix")
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
    """Agents merged with per-KCC scores and matrix metadata."""
    kccs = list_kccs()
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
    if _use_api():
        try:
            return _get(f"/agents/{agent_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
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
    if "evidence" in agent and isinstance(agent["evidence"], dict):
        return agent["evidence"]
    if "evidence" in agent and isinstance(agent["evidence"], list):
        return {e["kcc_id"]: e["score"] for e in agent["evidence"]}
    return {}


def kcc_stats(db: Session | None = None) -> dict[str, dict[str, int]]:
    close = False
    if db is None:
        db = SessionLocal()
        close = True
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
    if _use_api():
        return _get("/assays")
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
    if _use_api():
        return _get("/assays/references")
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
    return API_BASE
