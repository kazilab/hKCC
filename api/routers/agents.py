from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.citations import agent_bibtex, resource_bibtex, resource_ris
from api.schemas import AgentDetailOut, AgentOut, EvidenceCellOut, ReferenceOut
from db.config import get_settings
from db.models import Agent, AgentReference, Evidence, Reference
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


@router.get("/{agent_id}/references", response_model=list[ReferenceOut])
def list_agent_references(agent_id: str, db: Session = Depends(get_db)) -> list[ReferenceOut]:
    """References linked to this agent via `agent_references` (KCAD-derived)."""
    if not db.get(Agent, agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    rows = db.scalars(
        select(Reference)
        .join(AgentReference, AgentReference.reference_id == Reference.id)
        .where(AgentReference.agent_id == agent_id)
        .options(selectinload(Reference.tags), selectinload(Reference.kcc_links))
        .order_by(Reference.year.desc().nullslast())
    ).all()
    return [
        ReferenceOut(
            id=r.id,
            year=r.year,
            authors=r.authors,
            title=r.title,
            journal=r.journal,
            vol=r.vol,
            doi=r.doi,
            pmid=r.pmid,
            citations=r.citations,
            source=r.source,
            tags=[t.tag for t in r.tags],
            kcc_ids=[lk.kcc_id for lk in r.kcc_links],
        )
        for r in rows
    ]
