from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from hkcc.api.schemas import KCCOut
from hkcc.db.models import KCC
from hkcc.db.session import get_db

router = APIRouter(prefix="/kccs", tags=["kccs"])


@router.get("", response_model=list[KCCOut])
def list_kccs(db: Session = Depends(get_db)) -> list[KCC]:
    return list(db.scalars(select(KCC).order_by(KCC.n)))


@router.get("/{kcc_id}", response_model=KCCOut)
def get_kcc(kcc_id: str, db: Session = Depends(get_db)) -> KCC:
    row = db.get(KCC, kcc_id)
    if not row:
        raise HTTPException(status_code=404, detail="KCC not found")
    return row
