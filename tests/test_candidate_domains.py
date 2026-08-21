"""Layer separation between the ten KCCs and the candidate domains.

hKCC previously presented 14 key characteristics as a flat, equal list. The
annotation model it implements (Kazi et al., "Four Cross-Cutting Mechanistic
Domains for Evidence Mapping with the Key Characteristics of Carcinogens")
requires two layers instead:

* Layer 1 — the ten established KCCs, the reference ontology.
* Layer 2 — cross-cutting candidate domains, each parented onto one or more
  KCCs, carrying no score of their own.

The paper is explicit that a candidate-domain annotation "must not be counted as
an additional independent positive in a weight-of-evidence summary". These tests
enforce that structurally: a domain has no route to `evidence.score` at all.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from hkcc.db.models import (
    DOMAIN_KCC_RELATIONS,
    KCC,
    CandidateDomain,
    CandidateDomainAssay,
    CandidateDomainKCC,
    CandidateDomainReference,
    Evidence,
)
from hkcc.db.session import SessionLocal

ESTABLISHED_KCCS = 10
PAPER_DOMAINS = {"EMD1", "EMD2", "EMD3", "EMD4"}


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_reference_ontology_is_exactly_the_ten(db):
    """kccs holds the established set only; the extended four became domains."""
    kccs = list(db.scalars(select(KCC).order_by(KCC.n)))
    assert len(kccs) == ESTABLISHED_KCCS
    assert [k.n for k in kccs] == list(range(1, 11))
    assert not any(k.is_extended for k in kccs), "no KCC may be flagged extended any more"


def test_evidence_only_ever_references_an_established_kcc(db):
    """The scoring layer must not reach into Layer 2."""
    kcc_ids = {k.id for k in db.scalars(select(KCC))}
    stray = {e.kcc_id for e in db.scalars(select(Evidence))} - kcc_ids
    assert not stray, f"evidence rows pointing outside the ten KCCs: {stray}"


def test_domains_carry_no_score_route(db):
    """A candidate domain has no score column and no evidence rows keyed to it.

    This is the structural guarantee against double counting: there is nowhere
    for a domain annotation to become an independent positive.
    """
    domain_ids = {d.id for d in db.scalars(select(CandidateDomain))}
    assert domain_ids, "no candidate domains defined"
    assert not hasattr(CandidateDomain, "score")
    collisions = {e.kcc_id for e in db.scalars(select(Evidence))} & domain_ids
    assert not collisions, f"evidence scored against a domain: {collisions}"


def test_every_domain_parents_onto_at_least_one_kcc(db):
    """A domain with no parent would be a fourteenth characteristic by stealth."""
    orphans = []
    for d in db.scalars(select(CandidateDomain)):
        n = db.scalar(
            select(func.count()).select_from(CandidateDomainKCC).where(CandidateDomainKCC.domain_id == d.id)
        )
        if not n:
            orphans.append(d.code)
    assert not orphans, f"candidate domains with no parent KCC: {orphans}"


def test_parent_links_resolve_and_use_a_known_relation(db):
    kcc_ids = {k.id for k in db.scalars(select(KCC))}
    bad_kcc, bad_rel = [], []
    for link in db.scalars(select(CandidateDomainKCC)):
        if link.kcc_id not in kcc_ids:
            bad_kcc.append((link.domain_id, link.kcc_id))
        if link.relation not in set(DOMAIN_KCC_RELATIONS):
            bad_rel.append((link.domain_id, link.relation))
    assert not bad_kcc, f"parent links to unknown KCCs: {bad_kcc}"
    assert not bad_rel, f"unknown relation values: {bad_rel}"


def test_every_domain_has_exactly_one_kind_of_home(db):
    """A domain with no ``home`` has nowhere to file its evidence.

    ``downstream``/``upstream``/``contrastive`` all describe how a domain touches
    a KCC, not where its observations belong. Only ``home`` does that, so a
    domain carrying none of them would again be a characteristic by stealth -
    the same failure ``test_every_domain_parents_onto_at_least_one_kcc`` guards,
    one level more specific.
    """
    homeless = []
    for d in db.scalars(select(CandidateDomain)):
        n = db.scalar(
            select(func.count())
            .select_from(CandidateDomainKCC)
            .where(CandidateDomainKCC.domain_id == d.id, CandidateDomainKCC.relation == "home")
        )
        if not n:
            homeless.append(d.code)
    assert not homeless, f"candidate domains with no home KCC: {homeless}"


def test_contrastive_links_are_rare_and_deliberate(db):
    """``contrastive`` inverts the sign of a link, so it must not spread quietly.

    It exists for EMD4-KCC9: the domain measures induction of senescence and the
    characteristic is defined as bypass of it. Anything else claiming opposing
    polarity is a mapping decision that belongs in the manuscript first.
    """
    links = [
        (lk.domain_id, lk.kcc_id)
        for lk in db.scalars(select(CandidateDomainKCC).where(CandidateDomainKCC.relation == "contrastive"))
    ]
    assert links == [("emd4", "kcc-09")], f"unexpected contrastive links: {links}"


def test_every_domain_declares_its_evidence_bar(db):
    """The exclusions are the point: they stop a weak assay becoming a positive."""
    thin = [
        d.code
        for d in db.scalars(select(CandidateDomain))
        if len(d.minimum_evidence.strip()) < 30 or len(d.key_exclusions.strip()) < 20
    ]
    assert not thin, f"domains without a usable evidence bar or exclusions: {thin}"


def test_paper_domains_are_attributed_to_the_paper(db):
    """EMD1-4 cite the manuscript; anything else must cite its own source."""
    by_code = {d.code: d for d in db.scalars(select(CandidateDomain))}
    assert PAPER_DOMAINS <= set(by_code), f"missing paper domains: {PAPER_DOMAINS - set(by_code)}"
    for code in PAPER_DOMAINS:
        assert by_code[code].source_ref_id == "kazi2026-emd", (
            f"{code} should be attributed to the source manuscript"
        )
    extra = set(by_code) - PAPER_DOMAINS
    for code in extra:
        ref = by_code[code].source_ref_id
        assert ref and ref != "kazi2026-emd", (
            f"{code} is not one of the paper's four domains and must carry its own provenance"
        )


def test_domain_status_is_candidate(db):
    """Nothing has passed the validation benchmarks yet."""
    promoted = [d.code for d in db.scalars(select(CandidateDomain)) if d.status != "candidate"]
    assert not promoted, f"domains marked established without validation: {promoted}"


def test_migrated_links_survived(db):
    """The extended KCCs' assay and reference links moved rather than vanished."""
    n_assays = db.scalar(select(func.count()).select_from(CandidateDomainAssay))
    n_refs = db.scalar(select(func.count()).select_from(CandidateDomainReference))
    assert n_assays >= 8, f"expected the 8 migrated assay links, found {n_assays}"
    assert n_refs >= 12, f"expected the 12 migrated reference links, found {n_refs}"


def test_api_exposes_the_two_layers_separately(client):
    """/kccs is the reference ontology; /domains is the annotation layer."""
    kccs = client.get("/api/v1/kccs").json()
    domains = client.get("/api/v1/domains").json()
    assert isinstance(kccs, list) and isinstance(domains, list)
    for d in domains:
        assert "score" not in d, "a domain must not expose a score"
        assert d["primary_kcc_ids"] or d["secondary_kcc_ids"], f"{d['code']} has no parent KCC"
