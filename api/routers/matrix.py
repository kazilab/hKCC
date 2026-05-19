from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.schemas import MatrixOut, MatrixRowOut
from db.models import Agent, Evidence, KCC
from db.session import get_db

router = APIRouter(prefix="/matrix", tags=["matrix"])


@router.get("", response_model=MatrixOut)
def evidence_matrix(db: Session = Depends(get_db)) -> MatrixOut:
    kccs = list(db.scalars(select(KCC).order_by(KCC.n)))
    kcc_ids = [k.id for k in kccs]
    agents = db.scalars(
        select(Agent).options(selectinload(Agent.evidence_rows)).order_by(Agent.name)
    ).all()
    rows: list[MatrixRowOut] = []
    for agent in agents:
        score_map = {e.kcc_id: e.score for e in agent.evidence_rows}
        rows.append(
            MatrixRowOut(
                agent_id=agent.id,
                agent_name=agent.name,
                iarc_group=agent.iarc_group,
                scores={kid: score_map.get(kid, 0) for kid in kcc_ids},
            )
        )
    return MatrixOut(kcc_ids=kcc_ids, rows=rows)
