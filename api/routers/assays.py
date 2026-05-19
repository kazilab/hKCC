from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.schemas import AssayOut, ReferenceOut
from db.models import Assay, Reference
from db.session import get_db

router = APIRouter(prefix="/assays", tags=["assays"])


@router.get("", response_model=list[AssayOut])
def list_assays(db: Session = Depends(get_db)) -> list[AssayOut]:
    assays = db.scalars(select(Assay).options(selectinload(Assay.kcc_links)).order_by(Assay.name)).all()
    return [
        AssayOut(
            id=a.id,
            name=a.name,
            type=a.type,
            target=a.target,
            throughput=a.throughput,
            oecd_tg=a.oecd_tg,
            notes=a.notes,
            kcc_ids=[link.kcc_id for link in a.kcc_links],
        )
        for a in assays
    ]


@router.get("/references", response_model=list[ReferenceOut])
def list_references(db: Session = Depends(get_db)) -> list[ReferenceOut]:
    refs = db.scalars(
        select(Reference)
        .options(
            selectinload(Reference.tags),
            selectinload(Reference.kcc_links),
        )
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
            citations=r.citations,
            tags=[t.tag for t in r.tags],
            kcc_ids=[lk.kcc_id for lk in r.kcc_links],
        )
        for r in refs
    ]


@router.get("/{assay_id}", response_model=AssayOut)
def get_assay(assay_id: str, db: Session = Depends(get_db)) -> AssayOut:
    assay = db.scalar(select(Assay).where(Assay.id == assay_id).options(selectinload(Assay.kcc_links)))
    if not assay:
        raise HTTPException(status_code=404, detail="Assay not found")
    return AssayOut(
        id=assay.id,
        name=assay.name,
        type=assay.type,
        target=assay.target,
        throughput=assay.throughput,
        oecd_tg=assay.oecd_tg,
        notes=assay.notes,
        kcc_ids=[link.kcc_id for link in assay.kcc_links],
    )
