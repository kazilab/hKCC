"""Candidate mechanistic domains — Layer 2 of the annotation model.

Domains are *not* key characteristics. Each one parents onto one or more of the
ten established KCCs, which remain the reference ontology, and carries the
evidence bar and exclusions that must be met before an annotation counts.

They deliberately have no `evidence.score`: an observation is scored once,
against its KCC. Counting a domain as an additional independent positive would
double-count the same experiment.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from hkcc.api.schemas import CandidateDomainOut, DomainAssayLinkOut
from hkcc.db.models import CandidateDomain
from hkcc.db.session import get_db

router = APIRouter(prefix="/domains", tags=["domains"])

_LOAD = (
    selectinload(CandidateDomain.kcc_links),
    selectinload(CandidateDomain.assay_links),
    selectinload(CandidateDomain.reference_links),
)


def _out(d: CandidateDomain) -> CandidateDomainOut:
    return CandidateDomainOut(
        id=d.id,
        code=d.code,
        n=d.n,
        title=d.title,
        short=d.short,
        definition=d.definition,
        minimum_evidence=d.minimum_evidence,
        key_exclusions=d.key_exclusions,
        status=d.status,
        source_ref_id=d.source_ref_id,
        primary_kcc_ids=sorted(lk.kcc_id for lk in d.kcc_links if lk.relation == "primary"),
        secondary_kcc_ids=sorted(lk.kcc_id for lk in d.kcc_links if lk.relation == "secondary"),
        assay_ids=sorted(lk.assay_id for lk in d.assay_links),
        assay_links=sorted(
            (
                DomainAssayLinkOut(assay_id=lk.assay_id, evidence_level=lk.evidence_level)
                for lk in d.assay_links
            ),
            key=lambda link: link.assay_id,
        ),
        reference_ids=sorted(lk.reference_id for lk in d.reference_links),
    )


@router.get("", response_model=list[CandidateDomainOut])
def list_domains(db: Session = Depends(get_db)) -> list[CandidateDomainOut]:
    rows = db.scalars(select(CandidateDomain).options(*_LOAD).order_by(CandidateDomain.n)).all()
    return [_out(d) for d in rows]


@router.get("/{domain_id}", response_model=CandidateDomainOut)
def get_domain(domain_id: str, db: Session = Depends(get_db)) -> CandidateDomainOut:
    d = db.scalar(select(CandidateDomain).where(CandidateDomain.id == domain_id).options(*_LOAD))
    if not d:
        raise HTTPException(status_code=404, detail="Candidate domain not found")
    return _out(d)
