"""IARC Monograph 10-year retrospective matrix endpoints.

Surfaces the ``iarc_monograph_*`` tables, derived from Rusyn et al. 2024
(``10.1093/toxsci/kfad134``):

* ``GET /monograph/calls``          per-(volume, agent, model-system, KC) calls
* ``GET /monograph/strengths``      per-(agent, KC) standardized strength labels
* ``GET /monograph/agents``         agents that have rows in the call matrix
* ``GET /monograph/agent/{id}``     compact heat-map shape (calls + strengths) for one agent
* ``GET /monograph/kcc/{id}``       agents that received a ``Yes`` call for a given KC
* ``GET /monograph/volumes``        list of IARC Monograph volume numbers covered
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from hkcc.api.schemas import (
    IarcMonographKcCallOut,
    IarcMonographKcStrengthOut,
)
from hkcc.db.models import Agent, IarcMonographKcCall, IarcMonographKcStrength
from hkcc.db.session import get_db

router = APIRouter(prefix="/monograph", tags=["monograph"])


@router.get("/volumes", response_model=list[dict])
def list_volumes(db: Session = Depends(get_db)) -> list[dict]:
    """Distinct (volume, year) pairs present in the call matrix, sorted by volume."""
    rows = db.execute(
        select(
            IarcMonographKcCall.monograph_volume,
            IarcMonographKcCall.monograph_year,
        ).distinct()
    ).all()
    pairs = {(v, y) for v, y in rows}
    return [{"volume": v, "year": y} for v, y in sorted(pairs, key=lambda p: int(p[0]) if str(p[0]).isdigit() else 0)]


@router.get("/agents", response_model=list[dict])
def list_monograph_agents(db: Session = Depends(get_db)) -> list[dict]:
    """Agents that actually have rows in the call matrix.

    Membership is defined by the data, not by a curated allowlist: the app used
    to filter the picker on ``source_ref_id`` plus a hard-coded list of names,
    which silently hid 12 agents whose calls were present all along.
    """
    rows = db.execute(
        select(
            IarcMonographKcCall.agent_id,
            IarcMonographKcCall.kcc_id,
            IarcMonographKcCall.monograph_volume,
        ).distinct()
    ).all()
    kccs: defaultdict[str, set[str]] = defaultdict(set)
    volumes: defaultdict[str, set[str]] = defaultdict(set)
    for agent_id, kcc_id, volume in rows:
        kccs[agent_id].add(kcc_id)
        volumes[agent_id].add(volume)
    agents = {a.id: a for a in db.scalars(select(Agent).where(Agent.id.in_(kccs)))}
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


@router.get("/calls", response_model=list[IarcMonographKcCallOut])
def list_calls(
    db: Session = Depends(get_db),
    agent_id: str | None = Query(default=None),
    kcc_id: str | None = Query(default=None),
    monograph_volume: str | None = Query(default=None),
    model_system: str | None = Query(default=None),
    call: str | None = Query(default=None, description="Yes / No / Equivocal / Protective"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> list[IarcMonographKcCallOut]:
    stmt = select(IarcMonographKcCall)
    if agent_id:
        stmt = stmt.where(IarcMonographKcCall.agent_id == agent_id)
    if kcc_id:
        stmt = stmt.where(IarcMonographKcCall.kcc_id == kcc_id)
    if monograph_volume:
        stmt = stmt.where(IarcMonographKcCall.monograph_volume == monograph_volume)
    if model_system:
        stmt = stmt.where(IarcMonographKcCall.model_system == model_system)
    if call:
        stmt = stmt.where(IarcMonographKcCall.call == call)
    stmt = stmt.order_by(
        IarcMonographKcCall.agent_id,
        IarcMonographKcCall.kcc_id,
        IarcMonographKcCall.model_system,
    ).limit(limit)
    rows = db.scalars(stmt).all()
    return [IarcMonographKcCallOut.model_validate(r) for r in rows]


@router.get("/strengths", response_model=list[IarcMonographKcStrengthOut])
def list_strengths(
    db: Session = Depends(get_db),
    agent_id: str | None = Query(default=None),
    kcc_id: str | None = Query(default=None),
    strength: str | None = Query(default=None, description="Strong / Moderate / Weak"),
) -> list[IarcMonographKcStrengthOut]:
    stmt = select(IarcMonographKcStrength)
    if agent_id:
        stmt = stmt.where(IarcMonographKcStrength.agent_id == agent_id)
    if kcc_id:
        stmt = stmt.where(IarcMonographKcStrength.kcc_id == kcc_id)
    if strength:
        stmt = stmt.where(IarcMonographKcStrength.strength_label == strength)
    rows = db.scalars(stmt.order_by(IarcMonographKcStrength.agent_id, IarcMonographKcStrength.kcc_id)).all()
    return [IarcMonographKcStrengthOut.model_validate(r) for r in rows]


@router.get("/agent/{agent_id}", response_model=dict)
def agent_matrix(agent_id: str, db: Session = Depends(get_db)) -> dict:
    """Compact heat-map shape for a single agent.

    Response::

        {
          "agent_id": "benzene",
          "monograph_volumes": ["120"],
          "calls": {"kcc-01": {"Exposed Humans": "Yes", "Human cells in vitro": "Yes", ...}},
          "strength": {"kcc-01": {"label": "Strong", "data_role": "Supportive"}},
          "overall_strength_per_volume": {"120": {"kcc-01": "Strong"}}
        }
    """
    if not db.get(Agent, agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")

    calls = db.scalars(select(IarcMonographKcCall).where(IarcMonographKcCall.agent_id == agent_id)).all()
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
    for c in calls:
        vols.add(c.monograph_volume)
        if c.model_system == "Overall strength":
            overall_per_vol[c.monograph_volume][c.kcc_id] = c.call
            continue
        # If the same (kc, model_system) appears in multiple volumes, prefer
        # "Yes" over Equivocal/No so the heat-map shows the highest signal.
        prior = by_kc[c.kcc_id].get(c.model_system)
        prio = {"Yes": 4, "Equivocal": 3, "No": 2, "Protective": 1}
        if prior is None or prio.get(c.call, 0) > prio.get(prior, 0):
            by_kc[c.kcc_id][c.model_system] = c.call

    strengths = db.scalars(select(IarcMonographKcStrength).where(IarcMonographKcStrength.agent_id == agent_id)).all()
    strength_out = {s.kcc_id: {"label": s.strength_label, "data_role": s.data_role} for s in strengths}
    return {
        "agent_id": agent_id,
        "monograph_volumes": sorted(vols, key=lambda x: int(x) if str(x).isdigit() else 0),
        "calls": dict(by_kc),
        "strength": strength_out,
        "overall_strength_per_volume": dict(overall_per_vol),
    }


@router.get("/kcc/{kcc_id}", response_model=list[dict])
def kcc_agents(
    kcc_id: str,
    db: Session = Depends(get_db),
    call: str = Query(default="Yes"),
) -> list[dict]:
    """Agents with the given ``call`` for the given KC across any model system.

    Returns ``[{agent_id, agent_name, volumes, n_calls}]`` sorted by name.
    """
    rows = db.execute(
        select(
            IarcMonographKcCall.agent_id,
            Agent.name,
            IarcMonographKcCall.monograph_volume,
        )
        .join(Agent, Agent.id == IarcMonographKcCall.agent_id)
        .where(IarcMonographKcCall.kcc_id == kcc_id, IarcMonographKcCall.call == call)
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
