from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.ratelimit import rate_limit_contribute
from api.schemas import ContributeIn, ContributeOut
from db.models import KCC, Agent, Evidence, Revision
from db.session import get_db

router = APIRouter(prefix="/contribute", tags=["contribute"])


@router.post(
    "",
    response_model=ContributeOut,
    dependencies=[Depends(rate_limit_contribute)],
)
def submit_contribution(body: ContributeIn, db: Session = Depends(get_db)) -> ContributeOut:
    if not db.get(Agent, body.agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    if not db.get(KCC, body.kcc_id):
        raise HTTPException(status_code=404, detail="KCC not found")

    evidence = db.scalar(
        select(Evidence).where(
            Evidence.agent_id == body.agent_id,
            Evidence.kcc_id == body.kcc_id,
        )
    )
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence cell not found")

    note = body.rationale
    if body.submitter_name:
        note = f"[{body.submitter_name}] {note}"

    revision = Revision(
        evidence_id=evidence.id,
        curator_id=None,
        proposed_score=body.proposed_score,
        rationale=note,
        status="pending",
    )
    db.add(revision)
    db.commit()
    db.refresh(revision)
    return ContributeOut(
        revision_id=revision.id,
        status=revision.status,
        message="Proposal recorded for curator review (v2 workflow).",
    )
