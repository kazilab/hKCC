from datetime import datetime

from pydantic import BaseModel, Field


class KCCOut(BaseModel):
    id: str
    n: int
    title: str
    short: str
    description: str
    mechanism: str
    icon: str
    is_extended: bool

    model_config = {"from_attributes": True}


class DomainAssayLinkOut(BaseModel):
    """An assay that can measure a domain, with the level of claim it supports.

    ``descriptive`` observations do not satisfy a domain whose
    ``minimum_evidence`` demands a functional readout — CD5 says so explicitly.
    Returning bare assay ids discarded that distinction, so a consumer could not
    apply the domain's own exclusion rule.
    """

    assay_id: str
    evidence_level: str | None = None

    model_config = {"from_attributes": True}


class CandidateDomainOut(BaseModel):
    """A Layer-2 cross-cutting domain. Carries no score by design."""

    id: str
    code: str
    n: int
    title: str
    short: str
    definition: str
    minimum_evidence: str
    key_exclusions: str
    status: str
    source_ref_id: str | None = None
    # How the domain relates to each established KCC. `home` is the only one
    # that means "the evidence files here"; `upstream` runs the other way down
    # the causal chain, and `contrastive` marks opposing polarity and must never
    # be read as a positive.
    home_kcc_ids: list[str] = Field(default_factory=list)
    downstream_kcc_ids: list[str] = Field(default_factory=list)
    upstream_kcc_ids: list[str] = Field(default_factory=list)
    contrastive_kcc_ids: list[str] = Field(default_factory=list)
    # Deprecated: the two-value view. `primary` is `home`; `secondary` is
    # everything else, which discards the direction the fields above carry.
    primary_kcc_ids: list[str] = Field(default_factory=list)
    secondary_kcc_ids: list[str] = Field(default_factory=list)
    # Kept for compatibility; `assay_links` carries the evidence level.
    assay_ids: list[str] = Field(default_factory=list)
    assay_links: list[DomainAssayLinkOut] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AgentOut(BaseModel):
    id: str
    name: str
    cas: str | None
    iarc_group: str | None
    agent_type: str
    summary: str
    last_review: datetime | None
    sites: list[str] = Field(default_factory=list)
    monograph_volume: str | None = None
    monograph_pub_year: str | None = None
    evaluation_year: int | None = None
    source_ref_id: str | None = None

    model_config = {"from_attributes": True}


class EvidenceCellOut(BaseModel):
    kcc_id: str
    score: int
    # Direction is a separate axis from strength: "protective" means the source
    # reports the agent as *suppressing* the characteristic, and always pairs
    # with score 0. Never read a score without it.
    direction: str = "positive"
    # Which published derivation produced the score. Scores are only comparable
    # within a track: 10yr-iarc counts 3 primary model systems, vol100-kc counts
    # 4 information sources.
    source_track: str = "10yr-iarc"
    source_count: int | None = None
    # How the IARC working group used the data ("Not used" / "Supportive" /
    # "Upgrade"); only the 10-yr label track supplies it.
    data_role: str | None = None
    # The derivation, in words. The methodology states a score is not
    # self-interpreting, so this travels with it.
    curator_notes: str | None = None
    n_refs: int
    reference_ids: list[str] = Field(default_factory=list)


class AgentDetailOut(AgentOut):
    evidence: list[EvidenceCellOut] = Field(default_factory=list)


class MatrixRowOut(BaseModel):
    agent_id: str
    agent_name: str
    iarc_group: str | None
    scores: dict[str, int]
    # Non-positive directions only; absence means "positive".
    directions: dict[str, str] = Field(default_factory=dict)
    # Which derivation produced this row's scores. Never mixed within an agent.
    source_tracks: dict[str, str] = Field(default_factory=dict)
    # How the IARC working group used the mechanistic data, for every cell that
    # has a role ("Not used" / "Supportive" / "Upgrade"). A missing key means the
    # cell has no role, not that the role is unremarkable — emitting only
    # "Not used" made those two cases indistinguishable in exports.
    data_roles: dict[str, str] = Field(default_factory=dict)
    # Raw count behind the score where the source supplies one (null/absent for
    # label-derived Track A cells). Denominator is 3 systems (10yr) or 4 sources
    # (vol100); both 3 and 4 map to score 4 on vol100, so this is not lossy.
    source_counts: dict[str, int] = Field(default_factory=dict)


class MatrixOut(BaseModel):
    kcc_ids: list[str]
    rows: list[MatrixRowOut]


class AssaySubgroupOut(BaseModel):
    kcc_id: str
    subgroup: str

    model_config = {"from_attributes": True}


class AssayStudyDesignOut(BaseModel):
    kcc_id: str
    design: str
    source: str

    model_config = {"from_attributes": True}


class AssayOut(BaseModel):
    id: str
    name: str
    name_alt: str | None = None
    type: str
    target: str
    throughput: str
    oecd_tg: str | None
    notes: str | None
    source: str = "manual"
    granularity: str = "assay"
    source_ref_id: str | None = None
    kcc_ids: list[str] = Field(default_factory=list)
    subgroups: list[AssaySubgroupOut] = Field(default_factory=list)
    study_designs: list[AssayStudyDesignOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ReferenceOut(BaseModel):
    id: str
    year: int | None
    authors: str
    title: str
    journal: str
    vol: str | None
    doi: str | None
    pmid: str | None = None
    citations: int | None
    source: str = "manual"
    article_id: str | None = None
    url: str | None = None
    tags: list[str] = Field(default_factory=list)
    kcc_ids: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @classmethod
    def from_reference(
        cls,
        ref,
        *,
        tags: list[str] | None = None,
        kcc_ids: list[str] | None = None,
    ) -> "ReferenceOut":
        """Serialize a Reference, emitting a single canonical DOI/PMID.

        Legacy KCAD rows may still hold a space-joined multi-DOI blob in ``doi``;
        this collapses it to the first normalized identifier so the frontend always
        renders one working link. New imports already store single values.
        """
        from hkcc.db.references import normalized_dois, normalized_pmids

        dois = normalized_dois(ref.doi)
        pmids = normalized_pmids(ref.pmid)
        return cls(
            id=ref.id,
            year=ref.year,
            authors=ref.authors,
            title=ref.title,
            journal=ref.journal,
            vol=ref.vol,
            doi=dois[0] if dois else None,
            pmid=pmids[0] if pmids else None,
            citations=ref.citations,
            source=ref.source,
            article_id=ref.article_id,
            url=ref.url,
            tags=list(tags or []),
            kcc_ids=list(kcc_ids or []),
        )


class IarcMonographKcCallOut(BaseModel):
    id: int
    agent_id: str
    kcc_id: str
    monograph_volume: str
    monograph_year: int | None
    model_system: str
    call: str
    raw_call: str | None
    source_ref_id: str | None

    model_config = {"from_attributes": True}


class IarcMonographKcStrengthOut(BaseModel):
    agent_id: str
    kcc_id: str
    strength_label: str
    data_role: str | None
    iarc_group: str | None
    source_ref_id: str | None

    model_config = {"from_attributes": True}


class IarcMonographMatrixCellOut(BaseModel):
    """Compact pivot-shaped cell for the IARC Monograph KC heat-map UI."""

    agent_id: str
    kcc_id: str
    model_system: str
    call: str
    raw_call: str | None = None
    monograph_volume: str


class AnnotationPageOut(BaseModel):
    """One page of assay annotations.

    The endpoint previously returned a bare list capped at 500 rows with no
    cursor, so any consumer of a large assay was silently truncated. `total`
    makes the truncation visible; `next_cursor` makes it recoverable.
    """

    total: int
    count: int
    next_cursor: int | None = None
    items: list["AssayAnnotationOut"] = Field(default_factory=list)


class AnnotationReferenceOut(BaseModel):
    position: int
    reference_id: str | None = None
    id_type: str

    model_config = {"from_attributes": True}


class AssayAnnotationOut(BaseModel):
    id: int
    assay_id: str
    kcc_id: str
    # Single FK, kept for compatibility: it holds only the first KC when the
    # source cell names several ("3  9"). Filter on `secondary_kcc_ids`.
    secondary_kcc_id: str | None = None
    secondary_kcc_ids: list[str] = Field(default_factory=list)
    secondary_kc_raw: str | None = None
    # Denormalized position-1 primary citation (back-compat); full set in `references`.
    reference_id: str | None = None
    references: list[AnnotationReferenceOut] = []
    agent_id: str | None = None
    # KC classification
    kc_subgroup: str | None = None
    kc_subgroup2: str | None = None
    effect: str | None = None
    # Assay endpoints / method
    assay_endpoint: str | None = None
    assay_endpoint2: str | None = None
    assay_endpoint3: str | None = None
    biomarker: str | None = None
    method2: str | None = None
    stimulant_activation_agent: str | None = None
    target_cell: str | None = None
    # Biology
    organism: str | None = None
    species: str | None = None
    mammalian: str | None = None
    tissue: str | None = None
    tissue2: str | None = None
    cell_type: str | None = None
    immortalized: str | None = None
    # Study design
    cell_format: str | None = None
    design: str | None = None
    design_transgenic: str | None = None
    # Provenance
    monograph_num: str | None = None
    monograph_chem: str | None = None
    oecd_tg: str | None = None
    cebp_ref_idx: str | None = None
    source_ref_id: str | None = None

    model_config = {"from_attributes": True}


class AgentReferenceOut(BaseModel):
    agent_id: str
    reference_id: str
    source: str = "kcad"

    model_config = {"from_attributes": True}


class KcadAbbreviationOut(BaseModel):
    abbreviation: str
    expansion: str
    source_ref_id: str | None = None

    model_config = {"from_attributes": True}


class KcadColumnDefinitionOut(BaseModel):
    column_name: str
    # Verbatim from Supplementary Table 2, typos included.
    definition: str
    # Present only where the published definition does not describe what the
    # column actually holds in hKCC (three columns; see the model docstring).
    hkcc_note: str | None = None
    source_ref_id: str | None = None

    model_config = {"from_attributes": True}


class ContributeIn(BaseModel):
    """A proposed score change.

    No contact details are collected. ``submitter_email`` was previously
    accepted, validated and then silently discarded; asking for personal data
    that is never stored (and would land in a CC-BY export if it were) is worse
    than not asking. Attribution, when curation goes live, belongs on an
    authenticated curator record instead.
    """

    model_config = {"extra": "forbid"}

    agent_id: str = Field(min_length=1, max_length=64)
    kcc_id: str = Field(min_length=1, max_length=32)
    proposed_score: int = Field(ge=0, le=4)
    rationale: str = Field(min_length=10, max_length=4000)
    submitter_name: str | None = Field(
        default=None,
        max_length=255,
        description="Optional attribution. Stored alongside the proposal, not in the rationale text.",
    )


class ContributeOut(BaseModel):
    revision_id: int
    status: str
    message: str
