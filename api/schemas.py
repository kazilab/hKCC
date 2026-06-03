from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


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
    n_refs: int
    reference_ids: list[str] = Field(default_factory=list)


class AgentDetailOut(AgentOut):
    evidence: list[EvidenceCellOut] = Field(default_factory=list)


class MatrixRowOut(BaseModel):
    agent_id: str
    agent_name: str
    iarc_group: str | None
    scores: dict[str, int]


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
    pdf_path: str | None = None
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
        from db.references import normalized_dois, normalized_pmids

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
            pdf_path=getattr(ref, "pdf_path", None),
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


class AssayAnnotationOut(BaseModel):
    id: int
    assay_id: str
    kcc_id: str
    secondary_kcc_id: str | None = None
    secondary_kc_raw: str | None = None
    reference_id: str | None = None
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
    definition: str
    source_ref_id: str | None = None

    model_config = {"from_attributes": True}


class ContributeIn(BaseModel):
    agent_id: str = Field(min_length=1, max_length=64)
    kcc_id: str = Field(min_length=1, max_length=32)
    proposed_score: int = Field(ge=0, le=4)
    rationale: str = Field(min_length=10, max_length=4000)
    submitter_name: str | None = Field(default=None, max_length=255)
    submitter_email: EmailStr | None = None


class ContributeOut(BaseModel):
    revision_id: int
    status: str
    message: str
