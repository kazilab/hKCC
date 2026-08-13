from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from hkcc.api.schemas import MatrixOut, MatrixRowOut
from hkcc.db.models import KCC, Agent
from hkcc.db.session import get_db

router = APIRouter(prefix="/matrix", tags=["matrix"])


@router.get("", response_model=MatrixOut)
def evidence_matrix(db: Session = Depends(get_db)) -> MatrixOut:
    kccs = list(db.scalars(select(KCC).order_by(KCC.n)))
    kcc_ids = [k.id for k in kccs]
    agents = db.scalars(select(Agent).options(selectinload(Agent.evidence_rows)).order_by(Agent.name)).all()
    rows: list[MatrixRowOut] = []
    for agent in agents:
        score_map = {e.kcc_id: e.score for e in agent.evidence_rows}
        dir_map = {e.kcc_id: e.direction for e in agent.evidence_rows}
        track_map = {e.kcc_id: e.source_track for e in agent.evidence_rows}
        # The full role, not just "Not used". Emitting only the hazardous value
        # made every Supportive/Upgrade cell indistinguishable from a cell with
        # no role at all, so the matrix CSV exported 103 of them blank.
        role_map = {e.kcc_id: e.data_role for e in agent.evidence_rows if e.data_role}
        count_map = {e.kcc_id: e.source_count for e in agent.evidence_rows if e.source_count is not None}
        rows.append(
            MatrixRowOut(
                agent_id=agent.id,
                agent_name=agent.name,
                iarc_group=agent.iarc_group,
                # Only evaluated pairs are emitted. A missing key means "not
                # assessed", which is not the same claim as a score of 0.
                scores={kid: score_map[kid] for kid in kcc_ids if kid in score_map},
                # Only non-positive directions are emitted, so the common case
                # stays compact; a missing key means "positive".
                directions={kid: dir_map[kid] for kid in kcc_ids if kid in dir_map and dir_map[kid] != "positive"},
                source_tracks={kid: track_map[kid] for kid in kcc_ids if kid in track_map},
                data_roles={kid: role_map[kid] for kid in kcc_ids if kid in role_map},
                source_counts={kid: count_map[kid] for kid in kcc_ids if kid in count_map},
            )
        )
    return MatrixOut(kcc_ids=kcc_ids, rows=rows)
