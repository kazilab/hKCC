from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.citations import agent_bibtex, resource_bibtex, resource_ris
from api.schemas import AgentDetailOut, AgentOut, EvidenceCellOut
from db.config import get_settings
from db.models import Agent, Evidence
from db.session import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_out(agent: Agent) -> AgentOut:
    return AgentOut(
        id=agent.id,
        name=agent.name,
        cas=agent.cas,
        iarc_group=agent.iarc_group,
        agent_type=agent.agent_type,
        summary=agent.summary,
        last_review=agent.last_review,
        sites=[s.site for s in agent.sites],
    )


@router.get("", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)) -> list[AgentOut]:
    agents = db.scalars(select(Agent).options(selectinload(Agent.sites)).order_by(Agent.name)).all()
    return [_agent_out(a) for a in agents]


@router.get("/citation/resource.bib")
def resource_bib() -> Response:
    tag = get_settings().hkcc_release_tag
    return Response(content=resource_bibtex(tag), media_type="application/x-bibtex")


@router.get("/citation/resource.ris")
def resource_ris_download() -> Response:
    tag = get_settings().hkcc_release_tag
    return Response(content=resource_ris(tag), media_type="application/x-research-info-systems")


@router.get("/{agent_id}", response_model=AgentDetailOut)
def get_agent(agent_id: str, db: Session = Depends(get_db)) -> AgentDetailOut:
    agent = db.scalar(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.sites),
            selectinload(Agent.evidence_rows).selectinload(Evidence.citations),
        )
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    evidence = [
        EvidenceCellOut(
            kcc_id=e.kcc_id,
            score=e.score,
            n_refs=e.n_refs,
            reference_ids=[c.reference_id for c in e.citations],
        )
        for e in agent.evidence_rows
    ]
    base = _agent_out(agent)
    return AgentDetailOut(**base.model_dump(), evidence=evidence)


@router.get("/{agent_id}/citation.bib")
def agent_bibtex_download(agent_id: str, db: Session = Depends(get_db)) -> Response:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    tag = get_settings().hkcc_release_tag
    return Response(
        content=agent_bibtex(agent, tag),
        media_type="application/x-bibtex",
        headers={"Content-Disposition": f'attachment; filename="{agent_id}.bib"'},
    )
