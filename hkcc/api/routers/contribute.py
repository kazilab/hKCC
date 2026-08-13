import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hkcc.api.ratelimit import rate_limit_contribute
from hkcc.api.schemas import ContributeIn, ContributeOut
from hkcc.db.models import KCC, Agent, Evidence, Revision
from hkcc.db.session import get_db

router = APIRouter(prefix="/contribute", tags=["contribute"])


def _max_pending() -> int:
    """Ceiling on unreviewed proposals; 0 disables the check."""
    try:
        return int(os.environ.get("HKCC_CONTRIBUTE_MAX_PENDING", "500"))
    except ValueError:
        return 500


@router.post(
    "",
    response_model=ContributeOut,
    dependencies=[Depends(rate_limit_contribute)],
)
def submit_contribution(body: ContributeIn, db: Session = Depends(get_db)) -> ContributeOut:
    """Propose a revision to an **existing** evidence score.

    Scope in v0: revisions only. A pair with no evidence row cannot receive a
    proposal and returns 404 — which is the majority of the matrix (866 of the
    1,710 possible pairs are unassessed). Proposing a *new* cell needs a
    curation workflow that does not exist yet: an unassessed pair has no
    derivation, no source track and no provenance to revise, so accepting one
    would create a score with no rule behind it.

    Proposals are queued for curator review and never change a published score.
    """
    # The endpoint is unauthenticated, so the queue is bounded as well as
    # rate-limited: without a cap a persistent caller can grow the table without
    # limit even while staying inside the per-window budget.
    cap = _max_pending()
    if cap > 0:
        pending = db.scalar(
            select(func.count()).select_from(Revision).where(Revision.status == "pending")
        )
        if pending >= cap:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The review queue is full; contributions are paused until curators catch up.",
            )

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

    revision = Revision(
        evidence_id=evidence.id,
        curator_id=None,
        proposed_score=body.proposed_score,
        rationale=body.rationale,
        submitted_by=body.submitter_name or None,
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
