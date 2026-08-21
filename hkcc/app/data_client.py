"""Fetch hKCC data from API or the configured database."""

from __future__ import annotations

import functools
import os
from collections.abc import Callable
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar

import httpx
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from hkcc.db.config import KCAD_PAPER_REF_ID, get_settings
from hkcc.db.models import (
    KCC,
    Agent,
    AgentReference,
    Assay,
    AssayAnnotation,
    AssayKCC,
    CandidateDomain,
    Evidence,
    KcadAbbreviation,
    KcadColumnDefinition,
    Reference,
)

API_BASE = os.environ.get("API_BASE_URL", "").rstrip("/")

# The dataset only changes on a release, so a generous TTL is safe and keeps
# the app responsive: each read runs once per window instead of on every
# Streamlit rerun (which fires on every widget interaction).
_READ_TTL = 600  # seconds

_F = TypeVar("_F", bound=Callable[..., Any])


def _cached(ttl: int = _READ_TTL) -> Callable[[_F], _F]:
    """``st.cache_data`` that is only active under a live Streamlit runtime.

    Outside ``streamlit run`` (pytest, scripts, the API) the bare function runs
    every call, so cached state never leaks across data-source switches or
    between test cases — the behaviour tests assert on is preserved exactly.
    """

    def decorate(fn: _F) -> _F:
        cached_fn = st.cache_data(ttl=ttl, show_spinner=False)(fn)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                if st.runtime.exists():
                    return cached_fn(*args, **kwargs)
            except Exception:  # noqa: BLE001 — never let caching break a read
                pass
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorate


class DataSource(StrEnum):
    API = "api"
    DATABASE = "database"
    NO_DATA = "no_data"
    # Backward-compatible alias for older deployed page code. This does not
    # enable sample rows; it resolves to the no-data state.
    MOCKUP = "no_data"


def _open_db():
    """Create a database session lazily.

    Streamlit Cloud may import this module before optional DB driver imports are
    usable. Keeping ``db.session`` lazy lets API-only/no-data mode render instead
    of failing the whole app during module import.
    """
    from hkcc.db.session import SessionLocal

    return SessionLocal()


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
        db = _open_db()
        try:
            db.execute(select(KCC).limit(1))
            return True
        finally:
            db.close()
    except (ImportError, SQLAlchemyError):
        return False


@lru_cache(maxsize=1)
def get_data_source() -> DataSource:
    """Resolve where reads come from.

    Cached because it probes the network. Call :func:`refresh_data_source` to
    re-evaluate — the app does this when an API-backed read fails, so a backend
    that goes away mid-session falls back to the local database instead of
    raising for the rest of the process lifetime.
    """
    if _api_healthy():
        return DataSource.API
    if _db_healthy():
        return DataSource.DATABASE
    return DataSource.NO_DATA


def refresh_data_source() -> DataSource:
    """Drop the cached health probes and resolve the data source again."""
    _api_healthy.cache_clear()
    _db_healthy.cache_clear()
    get_data_source.cache_clear()
    return get_data_source()


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
    return "No database found (hkcc.db is missing — set DATABASE_URL or API_BASE_URL)"


def _get(path: str) -> Any:
    r = httpx.get(f"{API_BASE}/api/v1{path}", timeout=15.0)
    r.raise_for_status()
    return r.json()


def get_kcc(kcc_id: str) -> dict | None:
    for k in list_kccs():
        if k["id"] == kcc_id:
            return k
    return None


@_cached()
def list_kccs() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/kccs")
        except httpx.HTTPError:
            if refresh_data_source() is DataSource.API:
                raise
            return list_kccs()
    if src is DataSource.NO_DATA:
        return []
    db = _open_db()
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


@_cached()
def list_candidate_domains() -> list[dict]:
    """Layer 2: cross-cutting domains that qualify a KCC observation.

    These carry no evidence score by design — an observation is scored once,
    against its key characteristic. See docs/KCC_EVIDENCE_RULES.md.
    """
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/domains")
        except httpx.HTTPError:
            return []
    if src is DataSource.NO_DATA:
        return []
    db = _open_db()
    try:
        rows = db.scalars(
            select(CandidateDomain)
            .options(
                selectinload(CandidateDomain.kcc_links),
                selectinload(CandidateDomain.assay_links),
                selectinload(CandidateDomain.reference_links),
            )
            .order_by(CandidateDomain.n)
        ).all()
        return [
            {
                "id": d.id,
                "code": d.code,
                "n": d.n,
                "title": d.title,
                "short": d.short,
                "definition": d.definition,
                "minimum_evidence": d.minimum_evidence,
                "key_exclusions": d.key_exclusions,
                "status": d.status,
                "source_ref_id": d.source_ref_id,
                "home_kcc_ids": sorted(lk.kcc_id for lk in d.kcc_links if lk.relation == "home"),
                "downstream_kcc_ids": sorted(lk.kcc_id for lk in d.kcc_links if lk.relation == "downstream"),
                "upstream_kcc_ids": sorted(lk.kcc_id for lk in d.kcc_links if lk.relation == "upstream"),
                "contrastive_kcc_ids": sorted(lk.kcc_id for lk in d.kcc_links if lk.relation == "contrastive"),
                # Deprecated two-value view, kept so existing callers keep working.
                # "primary" collapses to `home`; everything else is "secondary",
                # which is exactly what the four relations exist to separate.
                "primary_kcc_ids": sorted(lk.kcc_id for lk in d.kcc_links if lk.relation == "home"),
                "secondary_kcc_ids": sorted(lk.kcc_id for lk in d.kcc_links if lk.relation != "home"),
                "assay_ids": sorted(lk.assay_id for lk in d.assay_links),
                # Structured form: a domain"s minimum_evidence can demand a
                # functional readout, so the level has to survive the API.
                "assay_links": sorted(
                    (
                        {"assay_id": lk.assay_id, "evidence_level": lk.evidence_level}
                        for lk in d.assay_links
                    ),
                    key=lambda link: link["assay_id"],
                ),
                "reference_ids": sorted(lk.reference_id for lk in d.reference_links),
            }
            for d in rows
        ]
    finally:
        db.close()


@_cached()
def list_agents() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/agents")
        except httpx.HTTPError:
            if refresh_data_source() is DataSource.API:
                raise
            return list_agents()
    if src is DataSource.NO_DATA:
        return []
    db = _open_db()
    try:
        rows = db.scalars(select(Agent).options(selectinload(Agent.sites)).order_by(Agent.name)).all()
        return [
            {
                "id": a.id,
                "name": a.name,
                # Raw values, not display placeholders. Substituting "—" here
                # made the database path disagree with the API (which returns
                # null) and with this module's own matrix rows, so the same
                # agent had two shapes depending on the deployment. Rendering
                # the em dash is the UI's job.
                "cas": a.cas,
                "iarc_group": a.iarc_group,
                "agent_type": a.agent_type,
                "summary": a.summary,
                "last_review": a.last_review.isoformat() if a.last_review else None,
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


@_cached()
def get_matrix() -> dict:
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/matrix")
        except httpx.HTTPError:
            if refresh_data_source() is DataSource.API:
                raise
            return get_matrix()
    if src is DataSource.NO_DATA:
        return {"kcc_ids": [], "rows": []}
    db = _open_db()
    try:
        kccs = list(db.scalars(select(KCC).order_by(KCC.n)))
        kcc_ids = [k.id for k in kccs]
        agents = db.scalars(select(Agent).options(selectinload(Agent.evidence_rows)).order_by(Agent.name)).all()
        rows = []
        for agent in agents:
            score_map = {e.kcc_id: e.score for e in agent.evidence_rows}
            dir_map = {e.kcc_id: e.direction for e in agent.evidence_rows if e.direction != "positive"}
            track_map = {e.kcc_id: e.source_track for e in agent.evidence_rows}
            # The full role, not just "Not used". Emitting only the hazardous
            # value made every Supportive/Upgrade cell indistinguishable from a
            # cell with no role, so the CSV exported 103 of them blank.
            role_map = {e.kcc_id: e.data_role for e in agent.evidence_rows if e.data_role}
            count_map = {e.kcc_id: e.source_count for e in agent.evidence_rows if e.source_count is not None}
            rows.append(
                {
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "iarc_group": agent.iarc_group,
                    # Missing key = not assessed; see docs/KCC_EVIDENCE_RULES.md.
                    "scores": {kid: score_map[kid] for kid in kcc_ids if kid in score_map},
                    "directions": {kid: dir_map[kid] for kid in kcc_ids if kid in dir_map},
                    "source_tracks": {kid: track_map[kid] for kid in kcc_ids if kid in track_map},
                    "data_roles": {kid: role_map[kid] for kid in kcc_ids if kid in role_map},
                    "source_counts": {kid: count_map[kid] for kid in kcc_ids if kid in count_map},
                }
            )
        return {"kcc_ids": kcc_ids, "rows": rows}
    finally:
        db.close()


@_cached()
def _evidence_scores() -> dict[str, dict[str, int]]:
    """``{agent_id: {kcc_id: score}}`` for every scored cell.

    Backs :func:`agents_with_evidence` without re-scanning the whole ``agents``
    table (which :func:`list_agents` already loads): in DB mode this is a single
    projection over ``evidence``; in API mode it reuses the cached matrix.
    """
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return {}
    if src is DataSource.API:
        return {r["agent_id"]: dict(r.get("scores", {})) for r in get_matrix()["rows"]}
    db = _open_db()
    try:
        scores: dict[str, dict[str, int]] = {}
        for agent_id, kcc_id, score in db.execute(select(Evidence.agent_id, Evidence.kcc_id, Evidence.score)):
            scores.setdefault(agent_id, {})[kcc_id] = score
        return scores
    finally:
        db.close()


@_cached()
def _evidence_tracks() -> dict[str, str]:
    """``{agent_id: source_track}``. Empty when the agent has no evidence."""
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return {}
    if src is DataSource.API:
        return {
            r["agent_id"]: next(iter(r.get("source_tracks", {}).values()), None)
            for r in get_matrix()["rows"]
            if r.get("source_tracks")
        }
    db = _open_db()
    try:
        return {
            agent_id: track
            for agent_id, track in db.execute(select(Evidence.agent_id, Evidence.source_track).distinct())
        }
    finally:
        db.close()


@_cached()
def _evidence_directions() -> dict[str, dict[str, str]]:
    """``{agent_id: {kcc_id: direction}}`` for non-positive directions only.

    Fingerprints and list views need this so protective cells are not painted
    as ordinary score-0 beige on the positive heat ramp.
    """
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return {}
    if src is DataSource.API:
        return {r["agent_id"]: dict(r.get("directions") or {}) for r in get_matrix()["rows"] if r.get("directions")}
    db = _open_db()
    try:
        dirs: dict[str, dict[str, str]] = {}
        for agent_id, kcc_id, direction in db.execute(
            select(Evidence.agent_id, Evidence.kcc_id, Evidence.direction).where(Evidence.direction != "positive")
        ):
            dirs.setdefault(agent_id, {})[kcc_id] = direction
        return dirs
    finally:
        db.close()


def agents_with_evidence() -> tuple[list[dict], list[dict]]:
    kccs = list_kccs()
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return [], kccs
    agents = list_agents()
    scores_by_agent = _evidence_scores()
    tracks_by_agent = _evidence_tracks()
    dirs_by_agent = _evidence_directions()
    kcc_ids = [k["id"] for k in kccs]
    enriched = []
    for a in agents:
        scores = scores_by_agent.get(a["id"], {})
        enriched.append(
            {
                **a,
                # Only evaluated pairs; a missing KCC means "not assessed".
                "evidence": {kid: scores[kid] for kid in kcc_ids if kid in scores},
                # Non-positive directions only; absence means "positive".
                "directions": dirs_by_agent.get(a["id"], {}),
                # Which published derivation the agent's scores come from. No
                # agent mixes tracks, but scores are not comparable across them.
                "source_track": tracks_by_agent.get(a["id"]),
                "iarc_group": a.get("iarc_group"),
            }
        )
    return enriched, kccs


@_cached()
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
    db = _open_db()
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
                "direction": e.direction,
                "source_track": e.source_track,
                "source_count": e.source_count,
                "data_role": e.data_role,
                "curator_notes": e.curator_notes,
                "n_refs": e.n_refs,
                "reference_ids": [c.reference_id for c in e.citations],
            }
            for e in agent.evidence_rows
        ]
        return {
            "id": agent.id,
            "name": agent.name,
            # Raw values; see the note in list_agents.
            "cas": agent.cas,
            "iarc_group": agent.iarc_group,
            "agent_type": agent.agent_type,
            "summary": agent.summary,
            "last_review": agent.last_review.isoformat() if agent.last_review else None,
            "sites": [s.site for s in agent.sites],
            # Monograph provenance. These were absent from the database path
            # while `list_agents` and the API both returned them, so Agent
            # Detail silently dropped "IARC Monograph <vols> · Evaluated <year>"
            # from its caption on exactly the deployment most people use.
            # tests/test_data_source_parity.py keeps the two paths aligned.
            "monograph_volume": agent.monograph_volume,
            "monograph_pub_year": agent.monograph_pub_year,
            "evaluation_year": agent.evaluation_year,
            "source_ref_id": agent.source_ref_id,
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


# Tags marking a paper as general framework/methodology literature rather than
# evidence for a particular characteristic.
FRAMEWORK_TAGS = frozenset({"Foundational", "Methodology", "Review", "Database"})


def references_for_kcc(kcc_id: str) -> list[dict]:
    """References **explicitly linked** to this KCC via ``reference_kccs``.

    This used to fall back to every framework-tagged paper when a KCC had no
    links. Since ``reference_kccs`` holds no rows, that fallback fired for all
    ten characteristics and each page listed the same 14 papers under
    "Anchoring publications" — presenting general framework literature as
    evidence anchored to that specific characteristic. The list is now empty
    when nothing is linked, which is the truth; framework papers are returned
    separately by :func:`framework_references`.
    """
    return [r for r in list_references() if kcc_id in r.get("kcc_ids", [])]


def framework_references() -> list[dict]:
    """General framework, methodology and review papers.

    Not anchored to any characteristic — they are background for the project as
    a whole, and are labelled as such wherever they appear.
    """
    return [
        r
        for r in list_references()
        if not r.get("kcc_ids") and set(r.get("tags", [])) & FRAMEWORK_TAGS
    ]


def evidence_for_agent(agent_id: str) -> list[dict]:
    """Per-cell evidence with resolved reference records."""
    agent = get_agent(agent_id)
    if not agent:
        return []
    refs_by_id = {r["id"]: r for r in list_references()}
    rows = agent.get("evidence", [])
    if isinstance(rows, dict):
        rows = [{"kcc_id": kid, "score": score, "n_refs": 0, "reference_ids": []} for kid, score in rows.items()]
    enriched = []
    for e in rows:
        ref_ids = list(e.get("reference_ids", []))
        # A cell with no linked citation is shown without one. Substituting a
        # general framework paper here would attribute evidence to a reference
        # that never supported it. (The previous fallback looked up the id
        # "smith2016", which does not exist, so it silently never fired.)
        refs = [refs_by_id[rid] for rid in ref_ids if rid in refs_by_id]
        enriched.append(
            {
                "kcc_id": e["kcc_id"],
                "score": e["score"],
                "direction": e.get("direction", "positive"),
                "source_track": e.get("source_track", "10yr-iarc"),
                "source_count": e.get("source_count"),
                "data_role": e.get("data_role"),
                "curator_notes": e.get("curator_notes"),
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
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return {}
    # An API-backed deployment must not touch the bundled SQLite file. This
    # function had no API branch at all, so it silently fell through to
    # `_open_db()` and served counts from whatever local database happened to
    # exist — or raised, on a deployment that ships none.
    if src is DataSource.API and db is None:
        kccs = list_kccs()
        matrix = get_matrix()
        assays = list_assays()
        carc = {k["id"]: 0 for k in kccs}
        for row in matrix.get("rows", []):
            directions = row.get("directions", {})
            for kcc_id, score in row.get("scores", {}).items():
                if score >= 2 and directions.get(kcc_id, "positive") == "positive":
                    carc[kcc_id] = carc.get(kcc_id, 0) + 1
        assay_counts: dict[str, int] = {}
        for assay in assays:
            for kcc_id in assay.get("kcc_ids", []):
                assay_counts[kcc_id] = assay_counts.get(kcc_id, 0) + 1
        return {
            k["id"]: {
                "carc_count": carc.get(k["id"], 0),
                "assay_count": assay_counts.get(k["id"], 0),
            }
            for k in kccs
        }
    if db is None:
        db = _open_db()
        close = True
    else:
        close = False
    try:
        # Agents showing *positive* evidence at "limited" or better.
        #
        # This counted `score > 0` across every direction, so a cell scoring 1-4
        # whose primary systems reported No, Equivocal or nothing was tallied as
        # an agent with evidence for the characteristic: KC2 read 152 where 129
        # agents actually have positive evidence. The threshold also now matches
        # `kcc_coverage`, so the KCC tiles and the coverage column agree.
        carc_counts = dict(
            db.execute(
                select(Evidence.kcc_id, func.count())
                .where(Evidence.score >= 2, Evidence.direction == "positive")
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


@_cached()
def list_assays() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/assays")
        except httpx.HTTPError:
            if refresh_data_source() is DataSource.API:
                raise
            return list_assays()
    if src is DataSource.NO_DATA:
        return []
    db = _open_db()
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
                "subgroups": [{"kcc_id": sg.kcc_id, "subgroup": sg.subgroup} for sg in a.kc_subgroups],
                "study_designs": [
                    {"kcc_id": sd.kcc_id, "design": sd.design, "source": sd.source} for sd in a.study_designs
                ],
            }
            for a in rows
        ]
    finally:
        db.close()


def _correct_reference(ref: dict) -> dict:
    """Apply narrow corrections for known upstream KCAD citation typos."""
    title = str(ref.get("title") or "")
    year = ref.get("year")
    if "De Coster" in title and "Paz-y-Mino 2007" in title and year != 2008:
        corrected = dict(ref)
        corrected["year"] = 2008
        corrected["title"] = title.replace(str(year), "2008", 1)
        return corrected
    return ref


def _clean_title(value: object) -> str:
    return " ".join(str(value or "").split())


def _is_placeholder_title(value: object) -> bool:
    title = _clean_title(value)
    return title in {"", "-", "–", "—"}


def _reference_identifiers(ref: dict) -> tuple[str | None, str | None]:
    """Normalized (doi, pmid) for identity comparison; blanks become ``None``."""
    from hkcc.db.references import normalized_dois, normalized_pmids

    dois = normalized_dois(ref.get("doi"))
    pmids = normalized_pmids(ref.get("pmid"))
    return (dois[0].lower() if dois else None, pmids[0] if pmids else None)


def _literature_dedupe_key(ref: dict) -> tuple[object, ...] | None:
    """Identity key for one published work.

    Keyed on a persistent identifier first. Keying on ``(year, title)`` merged
    two distinct 1981 papers on occupational hexachlorocyclohexane exposure —
    different DOIs, different PMIDs, different first authors — into one card.
    A DOI or PMID identifies a work; a title does not.

    Rows with neither identifier still fall back to (year, title), but
    :func:`unique_literature_references` refuses to merge under that key when
    the rows carry identifiers that disagree.
    """
    doi, pmid = _reference_identifiers(ref)
    if doi:
        return ("doi", doi)
    if pmid:
        return ("pmid", pmid)
    title = _clean_title(ref.get("title"))
    if _is_placeholder_title(title):
        return None
    return ("title", ref.get("year"), title.casefold())


def _identifiers_conflict(first: dict, second: dict) -> bool:
    """True when both rows name an identifier and the identifiers disagree."""
    doi_a, pmid_a = _reference_identifiers(first)
    doi_b, pmid_b = _reference_identifiers(second)
    return bool((doi_a and doi_b and doi_a != doi_b) or (pmid_a and pmid_b and pmid_a != pmid_b))


def _merge_values(first: list, second: list) -> list:
    return list(dict.fromkeys([*first, *second]))


def _reference_score(ref: dict) -> int:
    """Prefer the duplicate row with richer display metadata."""
    score = 0
    for field in ("doi", "pmid", "url", "article_id", "journal", "authors", "vol"):
        value = _clean_title(ref.get(field))
        if value and not _is_placeholder_title(value):
            score += 1
    score += len(ref.get("tags", []))
    score += len(ref.get("kcc_ids", []))
    return score


def unique_literature_references(refs: list[dict]) -> list[dict]:
    """Filter and de-duplicate references for public Literature display.

    The database keeps separate Reference rows because foreign keys may need
    stable source-specific IDs. The Literature page only needs one visible card
    per paper, so rows with the same normalized (year, title) collapse together.
    """
    rows_by_key: dict[tuple[object, str], dict] = {}
    order: list[tuple[object, str]] = []
    for ref in refs:
        key = _literature_dedupe_key(ref)
        if key is None:
            continue
        existing = rows_by_key.get(key)
        if existing is None:
            rows_by_key[key] = dict(ref)
            order.append(key)
            continue

        # Never merge across conflicting identifiers. Two rows sharing a title
        # but carrying different DOIs or PMIDs are different works, and folding
        # them together attributes one paper's metadata to the other.
        if _identifiers_conflict(existing, ref):
            fallback = (*key, ref.get("id"))
            rows_by_key[fallback] = dict(ref)
            order.append(fallback)
            continue

        winner = dict(ref) if _reference_score(ref) > _reference_score(existing) else dict(existing)
        winner["tags"] = _merge_values(existing.get("tags", []), ref.get("tags", []))
        winner["kcc_ids"] = _merge_values(existing.get("kcc_ids", []), ref.get("kcc_ids", []))
        winner["citations"] = max(existing.get("citations") or 0, ref.get("citations") or 0)
        rows_by_key[key] = winner
    return [rows_by_key[key] for key in order]


@_cached()
def list_references() -> list[dict]:
    src = get_data_source()
    if src is DataSource.API:
        try:
            return [_correct_reference(r) for r in _get("/assays/references")]
        except httpx.HTTPError:
            if refresh_data_source() is DataSource.API:
                raise
            return list_references()
    if src is DataSource.NO_DATA:
        return []
    db = _open_db()
    try:
        rows = db.scalars(
            select(Reference)
            .options(selectinload(Reference.tags), selectinload(Reference.kcc_links))
            .order_by(Reference.year.desc().nullslast())
        ).all()
        return [
            _correct_reference(
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
            )
            for r in rows
        ]
    finally:
        db.close()


@_cached()
def list_literature_references() -> list[dict]:
    return unique_literature_references(list_references())


@_cached()
def references_for_agent(agent_id: str) -> list[dict]:
    """KCAD-derived references linked to an agent via `agent_references`.

    Returns ``[]`` when no data source is available.
    """
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return []
    if src is DataSource.API:
        try:
            return [_correct_reference(r) for r in _get(f"/agents/{agent_id}/references")]
        except httpx.HTTPError:
            return []
    db = _open_db()
    try:
        rows = db.execute(
            select(Reference, AgentReference.source)
            .join(AgentReference, AgentReference.reference_id == Reference.id)
            .where(AgentReference.agent_id == agent_id)
            .order_by(Reference.year.desc().nullslast())
        ).all()
        return [
            _correct_reference(
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
            )
            for (r, ar_source) in rows
        ]
    finally:
        db.close()


@_cached()
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
    db = _open_db()
    try:
        rows = db.scalars(
            select(AssayAnnotation)
            .where(AssayAnnotation.assay_id == assay_id)
            .order_by(AssayAnnotation.id)
            .limit(limit)
            .options(selectinload(AssayAnnotation.references))
        ).all()
        return [
            {
                "id": a.id,
                "kcc_id": a.kcc_id,
                "secondary_kcc_id": a.secondary_kcc_id,
                # Every KC named in the raw cell; the scalar above keeps only
                # the first. Filter on this one.
                "secondary_kcc_ids": a.secondary_kcc_ids,
                "secondary_kc_raw": a.secondary_kc_raw,
                "reference_id": a.reference_id,
                "references": [
                    {
                        "position": ar.position,
                        "reference_id": ar.reference_id,
                        "id_type": ar.id_type,
                    }
                    for ar in a.references
                ],
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
    return len(list_literature_references())


def iarc_group_conflicts() -> dict[str, dict]:
    """Agents whose `agents.iarc_group` disagrees with the source strength table.

    ``iarc_monograph_kc_strength`` carries the IARC group as recorded by Rusyn et
    al. 2024 alongside each strength label. Three agents disagree with the agent
    row (aldrin 3 vs 2A, dieldrin 3 vs 2A, ortho-nitroanisole 2B vs 2A), so the
    database asserts two different classifications for the same substance.

    Which one is right is a curation decision, not something the code can settle
    — so the conflict is surfaced rather than silently resolved.
    """
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return {}
    if src is DataSource.API:
        try:
            rows = _get("/monograph/strengths")
        except httpx.HTTPError:
            return {}
        by_agent: dict[str, set[str]] = {}
        for row in rows:
            if row.get("iarc_group"):
                by_agent.setdefault(row["agent_id"], set()).add(row["iarc_group"])
        agents = {a["id"]: a.get("iarc_group") for a in list_agents()}
    else:
        from hkcc.db.models import IarcMonographKcStrength

        db = _open_db()
        try:
            by_agent = {}
            for row in db.scalars(select(IarcMonographKcStrength)):
                if row.iarc_group:
                    by_agent.setdefault(row.agent_id, set()).add(row.iarc_group)
            agents = {a.id: a.iarc_group for a in db.scalars(select(Agent))}
        finally:
            db.close()
    return {
        agent_id: {"agent_row": agents.get(agent_id), "source_table": sorted(groups)}
        for agent_id, groups in by_agent.items()
        if agents.get(agent_id) and agents[agent_id] not in groups
    }


@_cached()
def evidence_track_counts() -> dict[str, int]:
    """Assessed cells per source track, e.g. ``{"10yr-iarc": 502, "vol100-kc": 342}``.

    Derived from the matrix rather than hard-coded, so pages that describe where
    the scores come from cannot drift from the data they describe. Works on both
    the API and direct-database paths because ``source_tracks`` travels with
    every matrix row.
    """
    counts: dict[str, int] = {}
    for row in get_matrix().get("rows", []):
        for track in (row.get("source_tracks") or {}).values():
            counts[track] = counts.get(track, 0) + 1
    return counts


@_cached()
def get_evidence_rules() -> dict:
    """Score derivation rules plus live row counts (see API /methodology/evidence-rules)."""
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/methodology/evidence-rules")
        except httpx.HTTPError:
            return {}
    if src is DataSource.NO_DATA:
        return {}
    from hkcc.db.evidence_rules import evidence_rules_payload

    db = _open_db()
    try:
        return evidence_rules_payload(db)
    finally:
        db.close()


@_cached()
def list_abbreviations() -> list[dict]:
    """KCAD abbreviation glossary (Supplementary Table 3)."""
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return []
    if src is DataSource.API:
        try:
            return _get("/methodology/abbreviations")
        except httpx.HTTPError:
            return []
    db = _open_db()
    try:
        rows = db.scalars(select(KcadAbbreviation).order_by(KcadAbbreviation.abbreviation)).all()
        return [{"abbreviation": r.abbreviation, "expansion": r.expansion} for r in rows]
    finally:
        db.close()


@_cached()
def list_column_definitions() -> list[dict]:
    """KCAD column data dictionary (Supplementary Table 2)."""
    src = get_data_source()
    if src is DataSource.NO_DATA:
        return []
    if src is DataSource.API:
        try:
            return _get("/methodology/columns")
        except httpx.HTTPError:
            return []
    db = _open_db()
    try:
        rows = db.scalars(select(KcadColumnDefinition).order_by(KcadColumnDefinition.column_name)).all()
        return [{"column_name": r.column_name, "definition": r.definition, "hkcc_note": r.hkcc_note} for r in rows]
    finally:
        db.close()


@_cached()
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
        db = _open_db()
        try:
            paper = db.get(Reference, KCAD_PAPER_REF_ID)
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
    """Base URL for display. Falls back to the local default when unconfigured."""
    return API_BASE or "http://localhost:8000"


def configured_api_base() -> str | None:
    """The API base URL only when one is actually configured, else ``None``.

    A deployment that serves the app without an API (Streamlit Cloud reading the
    bundled database) has no public endpoint. Presenting the localhost fallback
    there would give visitors links pointing at their own machine.
    """
    return API_BASE or None


# ─── 10-yr IARC retrospective (Rusyn 2024) ───────────────────────────────────


def _monograph_imports():
    """Lazy import to keep optional when no database is available."""
    from hkcc.db.models import Agent, IarcMonographKcCall, IarcMonographKcStrength  # noqa: WPS433

    return Agent, IarcMonographKcCall, IarcMonographKcStrength


@_cached()
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
    db = _open_db()
    try:
        from sqlalchemy import select

        rows = db.execute(select(Call.monograph_volume, Call.monograph_year).distinct()).all()
        pairs = sorted(
            {(v, y) for v, y in rows},
            key=lambda p: int(p[0]) if str(p[0]).isdigit() else 0,
        )
        return [{"volume": v, "year": y} for v, y in pairs]
    finally:
        db.close()


@_cached()
def list_monograph_agents() -> list[dict]:
    """Agents with rows in the 10-year call matrix (see API /monograph/agents).

    Derived from the call table itself. The page previously built this list from
    ``source_ref_id`` plus a hard-coded set of names, which excluded 12 agents
    that had call data — and would have excluded every future import too.
    """
    src = get_data_source()
    if src is DataSource.API:
        try:
            return _get("/monograph/agents")
        except httpx.HTTPError:
            return []
    if src is DataSource.NO_DATA:
        return []
    from collections import defaultdict

    from sqlalchemy import select

    Agent_, Call, _ = _monograph_imports()
    db = _open_db()
    try:
        rows = db.execute(select(Call.agent_id, Call.kcc_id, Call.monograph_volume).distinct()).all()
        kccs: defaultdict[str, set[str]] = defaultdict(set)
        volumes: defaultdict[str, set[str]] = defaultdict(set)
        for agent_id, kcc_id, volume in rows:
            kccs[agent_id].add(kcc_id)
            volumes[agent_id].add(volume)
        agents = {a.id: a for a in db.scalars(select(Agent_).where(Agent_.id.in_(kccs)))}
        out = []
        for agent_id in kccs:
            agent = agents.get(agent_id)
            out.append(
                {
                    "agent_id": agent_id,
                    "name": agent.name if agent else agent_id,
                    "iarc_group": agent.iarc_group if agent else None,
                    "kcc_count": len(kccs[agent_id]),
                    "volumes": sorted(volumes[agent_id]),
                }
            )
        return sorted(out, key=lambda r: (r["name"] or "").lower())
    finally:
        db.close()


@_cached()
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
    db = _open_db()
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
            "strength": {s.kcc_id: {"label": s.strength_label, "data_role": s.data_role} for s in strengths},
            "overall_strength_per_volume": dict(overall_per_vol),
        }
    finally:
        db.close()


@_cached()
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
    db = _open_db()
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
