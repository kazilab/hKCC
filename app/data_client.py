"""Fetch hKCC data from API or the configured database."""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from db.config import get_settings
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
    NO_DATA = "no_data"
    # Backward-compatible alias for older deployed page code. This does not
    # enable demo/mockup rows; it resolves to the no-data state.
    MOCKUP = "no_data"


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
    url = (get_settings().database_url or "").strip()
    if not url:
        return False
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database and parsed.database != ":memory:":
        return Path(parsed.database).expanduser().is_file()
    return True


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
    return DataSource.NO_DATA


def data_source_label() -> str:
    src = get_data_source()
    if src is DataSource.API:
        return f"API · {API_BASE}"
    if src is DataSource.DATABASE:
        parsed = make_url(get_settings().database_url)
        if parsed.get_backend_name() == "sqlite":
            name = Path(parsed.database or "SQLite").name
            return f"SQLite · {name}"
        return "PostgreSQL"
    return "No database found (build hkcc.db or set DATABASE_URL/API_BASE_URL)"


def _get(path: str) -> Any:
    r = httpx.get(f"{API_BASE}/api/v1{path}", timeout=15.0)
    r.raise_for_status()
    return r.json()


def get_kcc(kcc_id: str) -> dict | None:
    for k in list_kccs():
        if k["id"] == kcc_id:
            return k
    return None


def list_kccs() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        return _get("/kccs")
    if src is DataSource.NO_DATA:
        return []
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
    if src is DataSource.NO_DATA:
        return []
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
    if src is DataSource.NO_DATA:
        return {"kcc_ids": [], "rows": []}
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
    if src is DataSource.NO_DATA:
        return [], kccs
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
    if src is DataSource.NO_DATA:
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
    if get_data_source() is DataSource.NO_DATA:
        return {}
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
    if src is DataSource.NO_DATA:
        return []
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
    if src is DataSource.NO_DATA:
        return []
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

    Returns ``[]`` when no data source is available.
    """
    src = get_data_source()
    if src is DataSource.NO_DATA:
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
    if src is DataSource.NO_DATA:
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
    if src is DataSource.NO_DATA:
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
    if src is DataSource.NO_DATA:
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

    Returns ``None`` when no data source is available.
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
    return None


def api_base_url() -> str:
    return API_BASE or "http://localhost:8000"


# ─── 10-yr IARC retrospective (Rusyn 2024) ───────────────────────────────────


def _monograph_imports():
    """Lazy import to keep optional when no database is available."""
    from db.models import Agent, IarcMonographKcCall, IarcMonographKcStrength  # noqa: WPS433

    return Agent, IarcMonographKcCall, IarcMonographKcStrength


def list_monograph_volumes() -> list[dict]:
    """Distinct IARC Monograph volumes covered by the 10-yr matrix."""
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/monograph/volumes")
        except httpx.HTTPError:
            return []
    if src is DataSource.NO_DATA:
        return []
    _, Call, _ = _monograph_imports()
    db = SessionLocal()
    try:
        from sqlalchemy import select

        rows = db.execute(
            select(Call.monograph_volume, Call.monograph_year).distinct()
        ).all()
        pairs = sorted(
            {(v, y) for v, y in rows},
            key=lambda p: int(p[0]) if str(p[0]).isdigit() else 0,
        )
        return [{"volume": v, "year": y} for v, y in pairs]
    finally:
        db.close()


def get_monograph_agent_matrix(agent_id: str) -> dict:
    """Compact heat-map shape for a single agent (see API /monograph/agent/{id})."""
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get(f"/monograph/agent/{agent_id}")
        except httpx.HTTPError:
            return {}
    if src is DataSource.NO_DATA:
        return {}
    from collections import defaultdict

    from sqlalchemy import select

    Agent, Call, Strength = _monograph_imports()
    db = SessionLocal()
    try:
        if not db.get(Agent, agent_id):
            return {}
        calls = db.scalars(select(Call).where(Call.agent_id == agent_id)).all()
        if not calls:
            return {
                "agent_id": agent_id,
                "monograph_volumes": [],
                "calls": {},
                "strength": {},
                "overall_strength_per_volume": {},
            }
        by_kc: dict[str, dict[str, str]] = defaultdict(dict)
        overall_per_vol: dict[str, dict[str, str]] = defaultdict(dict)
        vols: set[str] = set()
        prio = {"Yes": 4, "Equivocal": 3, "No": 2, "Protective": 1}
        for c in calls:
            vols.add(c.monograph_volume)
            if c.model_system == "Overall strength":
                overall_per_vol[c.monograph_volume][c.kcc_id] = c.call
                continue
            prior = by_kc[c.kcc_id].get(c.model_system)
            if prior is None or prio.get(c.call, 0) > prio.get(prior, 0):
                by_kc[c.kcc_id][c.model_system] = c.call
        strengths = db.scalars(select(Strength).where(Strength.agent_id == agent_id)).all()
        return {
            "agent_id": agent_id,
            "monograph_volumes": sorted(vols, key=lambda x: int(x) if str(x).isdigit() else 0),
            "calls": dict(by_kc),
            "strength": {
                s.kcc_id: {"label": s.strength_label, "data_role": s.data_role}
                for s in strengths
            },
            "overall_strength_per_volume": dict(overall_per_vol),
        }
    finally:
        db.close()


def list_monograph_kcc_agents(kcc_id: str, *, call: str = "Yes") -> list[dict]:
    """Agents with the given call for ``kcc_id`` across any model system."""
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get(f"/monograph/kcc/{kcc_id}?call={call}")
        except httpx.HTTPError:
            return []
    if src is DataSource.NO_DATA:
        return []
    from collections import defaultdict

    from sqlalchemy import select

    Agent, Call, _ = _monograph_imports()
    db = SessionLocal()
    try:
        rows = db.execute(
            select(Call.agent_id, Agent.name, Call.monograph_volume)
            .join(Agent, Agent.id == Call.agent_id)
            .where(Call.kcc_id == kcc_id, Call.call == call)
        ).all()
        by_agent: dict[tuple[str, str], set[str]] = defaultdict(set)
        for aid, name, vol in rows:
            by_agent[(aid, name)].add(vol)
        return [
            {
                "agent_id": aid,
                "agent_name": name,
                "volumes": sorted(vols, key=lambda x: int(x) if str(x).isdigit() else 0),
                "n_calls": len(vols),
            }
            for (aid, name), vols in sorted(by_agent.items(), key=lambda x: x[0][1].lower())
        ]
    finally:
        db.close()


def list_foundational_references() -> list[dict]:
    """Reference rows whose `source` tag is 'foundational' (anchored to PDFs).

    No-data mode returns an empty list.
    """
    src = get_data_source()
    if src is DataSource.API:
        try:
            return [
                r for r in (_get("/assays/references") or [])
                if r.get("source") == "foundational"
            ]
        except httpx.HTTPError:
            return []
    if src is DataSource.NO_DATA:
        return []
    from sqlalchemy import select

    from db.models import Reference, ReferenceTag

    db = SessionLocal()
    try:
        refs = db.scalars(
            select(Reference).where(Reference.source == "foundational")
        ).all()
        if not refs:
            return []
        tag_rows = db.execute(
            select(ReferenceTag.reference_id, ReferenceTag.tag).where(
                ReferenceTag.reference_id.in_([r.id for r in refs])
            )
        ).all()
        tags_by_ref: dict[str, list[str]] = {}
        for rid, tag in tag_rows:
            tags_by_ref.setdefault(rid, []).append(tag)
        return [
            {
                "id": r.id,
                "year": r.year,
                "authors": r.authors,
                "title": r.title,
                "journal": r.journal,
                "vol": r.vol,
                "doi": r.doi,
                "url": r.url,
                "pdf_path": r.pdf_path,
                "tags": sorted(tags_by_ref.get(r.id, [])),
            }
            for r in sorted(refs, key=lambda x: (-(x.year or 0), x.title or ""))
        ]
    finally:
        db.close()
