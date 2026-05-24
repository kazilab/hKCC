"""Methodology endpoints — KCAD glossary, column dictionary, source paper."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas import (
    KcadAbbreviationOut,
    KcadColumnDefinitionOut,
    ReferenceOut,
)
from db.models import KcadAbbreviation, KcadColumnDefinition, Reference
from db.session import get_db
from pipelines.import_kcad import KCAD_PAPER_REF_ID

router = APIRouter(prefix="/methodology", tags=["methodology"])


@router.get("/abbreviations", response_model=list[KcadAbbreviationOut])
def list_abbreviations(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Substring filter on abbreviation/expansion"),
) -> list[KcadAbbreviationOut]:
    stmt = select(KcadAbbreviation).order_by(KcadAbbreviation.abbreviation)
    rows = db.scalars(stmt).all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r.abbreviation.lower() or ql in r.expansion.lower()]
    return [KcadAbbreviationOut.model_validate(r) for r in rows]


@router.get("/abbreviations/{abbr}", response_model=KcadAbbreviationOut)
def get_abbreviation(abbr: str, db: Session = Depends(get_db)) -> KcadAbbreviationOut:
    row = db.get(KcadAbbreviation, abbr)
    if row is None:
        raise HTTPException(status_code=404, detail="Abbreviation not found")
    return KcadAbbreviationOut.model_validate(row)


@router.get("/columns", response_model=list[KcadColumnDefinitionOut])
def list_columns(db: Session = Depends(get_db)) -> list[KcadColumnDefinitionOut]:
    rows = db.scalars(
        select(KcadColumnDefinition).order_by(KcadColumnDefinition.column_name)
    ).all()
    return [KcadColumnDefinitionOut.model_validate(r) for r in rows]


@router.get("/source", response_model=ReferenceOut)
def get_source_paper(db: Session = Depends(get_db)) -> ReferenceOut:
    """Return the KCAD source publication reference row (Rigutto et al. 2025)."""
    paper = db.get(Reference, KCAD_PAPER_REF_ID)
    if paper is None:
        raise HTTPException(status_code=404, detail="KCAD source paper not seeded")
    return ReferenceOut(
        id=paper.id,
        year=paper.year,
        authors=paper.authors,
        title=paper.title,
        journal=paper.journal,
        vol=paper.vol,
        doi=paper.doi,
        pmid=paper.pmid,
        citations=paper.citations,
        source=paper.source,
        article_id=paper.article_id,
        url=paper.url,
        tags=[],
        kcc_ids=[],
    )
