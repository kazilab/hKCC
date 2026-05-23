from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.schemas import (
    AssayAnnotationOut,
    AssayOut,
    AssayStudyDesignOut,
    AssaySubgroupOut,
    ReferenceOut,
)
from db.models import Assay, AssayAnnotation, Reference
from db.session import get_db

router = APIRouter(prefix="/assays", tags=["assays"])


def _assay_out(a: Assay) -> AssayOut:
    return AssayOut(
        id=a.id,
        name=a.name,
        name_alt=a.name_alt,
        type=a.type,
        target=a.target,
        throughput=a.throughput,
        oecd_tg=a.oecd_tg,
        notes=a.notes,
        source=a.source,
        granularity=a.granularity,
        source_ref_id=a.source_ref_id,
        kcc_ids=[link.kcc_id for link in a.kcc_links],
        subgroups=[
            AssaySubgroupOut(kcc_id=sg.kcc_id, subgroup=sg.subgroup)
            for sg in a.kc_subgroups
        ],
        study_designs=[
            AssayStudyDesignOut(kcc_id=sd.kcc_id, design=sd.design, source=sd.source)
            for sd in a.study_designs
        ],
    )


_ASSAY_LOAD_OPTS = (
    selectinload(Assay.kcc_links),
    selectinload(Assay.kc_subgroups),
    selectinload(Assay.study_designs),
)


@router.get("", response_model=list[AssayOut])
def list_assays(
    db: Session = Depends(get_db),
    source: str | None = Query(default=None, description="Filter by provenance (mockup/kcad)"),
    design: str | None = Query(
        default=None,
        description="Filter by study design (in_vivo/ex_vivo/in_vitro/in_silico)",
    ),
    subgroup: str | None = Query(default=None, description="Filter by KC subgroup label"),
) -> list[AssayOut]:
    stmt = select(Assay).options(*_ASSAY_LOAD_OPTS).order_by(Assay.name)
    if source:
        stmt = stmt.where(Assay.source == source)
    rows = db.scalars(stmt).all()
    out = [_assay_out(a) for a in rows]
    if design:
        out = [a for a in out if any(sd.design == design for sd in a.study_designs)]
    if subgroup:
        sg_lower = subgroup.lower()
        out = [
            a
            for a in out
            if any(sg.subgroup.lower() == sg_lower for sg in a.subgroups)
        ]
    return out


@router.get("/references", response_model=list[ReferenceOut])
def list_references(
    db: Session = Depends(get_db),
    source: str | None = Query(default=None),
) -> list[ReferenceOut]:
    stmt = (
        select(Reference)
        .options(selectinload(Reference.tags), selectinload(Reference.kcc_links))
        .order_by(Reference.year.desc().nullslast())
    )
    if source:
        stmt = stmt.where(Reference.source == source)
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
            article_id=r.article_id,
            url=r.url,
            tags=[t.tag for t in r.tags],
            kcc_ids=[lk.kcc_id for lk in r.kcc_links],
        )
        for r in db.scalars(stmt).all()
    ]


@router.get("/{assay_id}", response_model=AssayOut)
def get_assay(assay_id: str, db: Session = Depends(get_db)) -> AssayOut:
    assay = db.scalar(
        select(Assay).where(Assay.id == assay_id).options(*_ASSAY_LOAD_OPTS)
    )
    if not assay:
        raise HTTPException(status_code=404, detail="Assay not found")
    return _assay_out(assay)


@router.get("/{assay_id}/annotations", response_model=list[AssayAnnotationOut])
def list_annotations(
    assay_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[AssayAnnotationOut]:
    rows = db.scalars(
        select(AssayAnnotation)
        .where(AssayAnnotation.assay_id == assay_id)
        .order_by(AssayAnnotation.id)
        .limit(limit)
    ).all()
    return [AssayAnnotationOut.model_validate(r) for r in rows]
