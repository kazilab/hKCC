"""SQLAlchemy models for hKCC."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class KCC(Base):
    __tablename__ = "kccs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    n: Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mechanism: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(String(32), nullable=False)
    # Retained for backward compatibility; always False. The four "extended"
    # characteristics became candidate annotation domains (see CandidateDomain)
    # once the ten established KCCs were fixed as the reference ontology.
    is_extended: Mapped[bool] = mapped_column(default=False, nullable=False)

    evidence_rows: Mapped[list["Evidence"]] = relationship(back_populates="kcc")
    assay_links: Mapped[list["AssayKCC"]] = relationship(back_populates="kcc")
    reference_links: Mapped[list["ReferenceKCC"]] = relationship(back_populates="kcc")


class CandidateDomain(Base):
    """A cross-cutting mechanistic domain — Layer 2 of the annotation model.

    Candidate domains are *not* key characteristics. They qualify how an
    observation arose (by what mechanistic route, at what evidence level) and
    always parent onto one or more of the ten established KCCs, which remain the
    reference ontology. They must never be counted as additional independent
    positives in a weight-of-evidence summary; see docs/KCC_EVIDENCE_RULES.md.
    """

    __tablename__ = "candidate_domains"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    n: Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short: Mapped[str] = mapped_column(String(64), nullable=False)
    # What exposure-linked event the domain is meant to capture.
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    # What must be shown before an annotation counts, and what is explicitly
    # insufficient (e.g. "global m6A abundance alone does not qualify").
    minimum_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    key_exclusions: Mapped[str] = mapped_column(Text, nullable=False)
    # "candidate" for every domain today; "established" is reserved for one that
    # passes the validation benchmarks and is promoted.
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="candidate")
    icon: Mapped[str] = mapped_column(String(32), nullable=False, default="circle")
    # Publication proposing the domain. Domains proposed outside the source
    # paper carry their own reference, so provenance stays separable.
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), index=True)

    kcc_links: Mapped[list["CandidateDomainKCC"]] = relationship(back_populates="domain", cascade="all, delete-orphan")
    assay_links: Mapped[list["CandidateDomainAssay"]] = relationship(
        back_populates="domain", cascade="all, delete-orphan"
    )
    reference_links: Mapped[list["CandidateDomainReference"]] = relationship(
        back_populates="domain", cascade="all, delete-orphan"
    )
    validation_examples: Mapped[list["CandidateDomainValidationExample"]] = relationship(
        back_populates="domain",
        cascade="all, delete-orphan",
        order_by="CandidateDomainValidationExample.sort_order",
    )


#: How a candidate domain relates to one of the ten established KCCs. Four
#: values, because the old primary/secondary pair was carrying four meanings and
#: could express neither direction (section 3 requires it) nor opposing polarity.
#:
#: ``home``        the KCC an observation files under, in essentially every
#:                 instance of the domain - the only relation that reads as
#:                 "the domain belongs here"
#: ``downstream``  a KCC endpoint the domain can produce; case-dependent
#: ``upstream``    a KCC that induces or enables the domain (arrow reversed)
#: ``contrastive`` a KCC of opposing polarity: evidentially adjacent, and never
#:                 a positive (EMD4 measures induction of senescence; KCC9 is
#:                 defined as *bypass* of it)
DOMAIN_KCC_RELATIONS = ("home", "downstream", "upstream", "contrastive")


class CandidateDomainKCC(Base):
    """Parent-KCC link. ``relation`` is one of :data:`DOMAIN_KCC_RELATIONS`."""

    __tablename__ = "candidate_domain_kccs"
    __table_args__ = (
        CheckConstraint(
            "relation IN ('home','downstream','upstream','contrastive')",
            name="ck_domain_kcc_relation",
        ),
    )

    domain_id: Mapped[str] = mapped_column(ForeignKey("candidate_domains.id", ondelete="CASCADE"), primary_key=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), primary_key=True)
    relation: Mapped[str] = mapped_column(String(16), nullable=False, default="home")

    domain: Mapped["CandidateDomain"] = relationship(back_populates="kcc_links")
    kcc: Mapped["KCC"] = relationship()


class CandidateDomainAssay(Base):
    """Assays that can measure a candidate domain."""

    __tablename__ = "candidate_domain_assays"

    domain_id: Mapped[str] = mapped_column(ForeignKey("candidate_domains.id", ondelete="CASCADE"), primary_key=True)
    assay_id: Mapped[str] = mapped_column(ForeignKey("assays.id", ondelete="CASCADE"), primary_key=True)
    # "functional" evidence carries weight; "descriptive" alone does not.
    evidence_level: Mapped[str] = mapped_column(String(16), nullable=False, default="descriptive")

    domain: Mapped["CandidateDomain"] = relationship(back_populates="assay_links")
    assay: Mapped["Assay"] = relationship()


class CandidateDomainReference(Base):
    """Anchor literature for a candidate domain."""

    __tablename__ = "candidate_domain_references"

    domain_id: Mapped[str] = mapped_column(ForeignKey("candidate_domains.id", ondelete="CASCADE"), primary_key=True)
    reference_id: Mapped[str] = mapped_column(ForeignKey("references.id", ondelete="CASCADE"), primary_key=True)

    domain: Mapped["CandidateDomain"] = relationship(back_populates="reference_links")
    reference: Mapped["Reference"] = relationship()


#: What kind of thing a validation example is. Deliberately *not* ordered: a
#: `structural` result is not weaker than a `data-constrained` one, it answers a
#: different question. Free text here would make the "no implied strength scale"
#: rule in the UI unenforceable, so the vocabulary is closed.
VALIDATION_EVIDENTIARY_STATUS = (
    "data-constrained",    # fitted or digitised against measured quantities
    "design-constrained",  # magnitudes assigned to match a study design, not fitted
    "structural",          # a property of the model wiring or algebra
    "illustrative",        # plausible magnitudes chosen to demonstrate a relationship
    "prior-dominated",     # anchored to published observation, magnitudes mostly chosen
    "predictive",          # a held-out model output, not matched empirical validation
)


class CandidateDomainValidationExample(Base):
    """A simulation-derived annotation rule for a candidate domain.

    These say what is *insufficient* to support a domain annotation, what
    competing explanation has to be excluded, and which measurement discriminates
    between them. They come from the systems models in the EMD simulation paper.

    They are guidance, not evidence. There is deliberately no ``score`` column
    and no foreign key from ``evidence``: a model result is not an independent
    mechanistic positive, and counting one would double-count the very
    observations used to constrain the model. See docs/KCC_EVIDENCE_RULES.md.
    """

    __tablename__ = "candidate_domain_validation_examples"
    __table_args__ = (
        UniqueConstraint("domain_id", "sort_order", name="uq_domain_validation_sort"),
        CheckConstraint("sort_order > 0", name="ck_domain_validation_sort"),
        CheckConstraint(
            "evidentiary_status IN ('data-constrained','design-constrained','structural',"
            "'illustrative','prior-dominated','predictive')",
            name="ck_domain_validation_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_domains.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Which parent KCC the example is about. Nullable because an example can be
    # about the domain as a whole; when set, the (domain, kcc) pair must already
    # be a link in `candidate_domain_kccs` - the example annotates a relation
    # that exists, it does not create one.
    kcc_id: Mapped[str | None] = mapped_column(ForeignKey("kccs.id", ondelete="SET NULL"), index=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # The four fields that make the example usable rather than decorative: what
    # else could explain the observation, what does not settle it, what does,
    # and what the model actually showed.
    alternative_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    insufficient_measurement: Mapped[str] = mapped_column(Text, nullable=False)
    discriminating_measurement: Mapped[str] = mapped_column(Text, nullable=False)
    simulation_finding: Mapped[str] = mapped_column(Text, nullable=False)
    annotation_implication: Mapped[str] = mapped_column(Text, nullable=False)

    #: One of :data:`VALIDATION_EVIDENTIARY_STATUS`.
    evidentiary_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidentiary_note: Mapped[str | None] = mapped_column(Text)
    # Where the result was fragile, and where it was not. Kept because dropping
    # it would turn a heuristic sensitivity count into an unqualified claim.
    robustness_note: Mapped[str | None] = mapped_column(Text)
    # The individual validation check, which the reference cannot identify.
    source_locator: Mapped[str | None] = mapped_column(String(255))
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), index=True)

    domain: Mapped["CandidateDomain"] = relationship(back_populates="validation_examples")
    kcc: Mapped["KCC"] = relationship()


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cas: Mapped[str | None] = mapped_column(String(32))
    iarc_group: Mapped[str | None] = mapped_column(String(8))
    agent_type: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # KCAD/IARC extensions, from Supplementary Table 1 of the KCAD paper.
    monograph_volume: Mapped[str | None] = mapped_column(String(64))
    monograph_pub_year: Mapped[str | None] = mapped_column(String(32))
    evaluation_year: Mapped[int | None] = mapped_column(SmallInteger)
    # FK to the publication this row was sourced from (Rigutto et al. 2025 for KCAD rows).
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), index=True)

    sites: Mapped[list["AgentSite"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    evidence_rows: Mapped[list["Evidence"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    reference_links: Mapped[list["AgentReference"]] = relationship(back_populates="agent", cascade="all, delete-orphan")


class AgentSite(Base):
    __tablename__ = "agent_sites"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    site: Mapped[str] = mapped_column(String(255), primary_key=True)

    agent: Mapped["Agent"] = relationship(back_populates="sites")


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("agent_id", "kcc_id", name="uq_evidence_agent_kcc"),
        CheckConstraint("score >= 0 AND score <= 4", name="ck_evidence_score"),
        CheckConstraint(
            "direction IN ('positive','protective','equivocal','negative','unspecified')",
            name="ck_evidence_direction",
        ),
        # A cell reported as suppressing the characteristic cannot also carry
        # positive evidence of it.
        CheckConstraint("NOT (direction = 'protective' AND score > 0)", name="ck_protective_not_positive"),
        CheckConstraint("source_track IN ('10yr-iarc','vol100-kc')", name="ck_evidence_source_track"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    # Direction is a separate axis from strength. A source can report that an
    # agent *suppresses* a characteristic ("Protective"); scoring that on the
    # positive scale would invert its meaning. Values: positive, protective,
    # equivocal, negative, unspecified.
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="positive")
    # Which published derivation produced this score. The two tracks put
    # different things on the same 0-4 scale, so a score is only comparable to
    # another score from the same track.
    source_track: Mapped[str] = mapped_column(String(16), nullable=False, default="10yr-iarc")
    # The count the score was derived from, where the source supplies one. The
    # denominator differs by track: out of 3 primary model systems for
    # 10yr-iarc (call track), out of 4 information sources for vol100-kc.
    # NULL where the source gave a label rather than a count.
    source_count: Mapped[int | None] = mapped_column(SmallInteger)
    # How the IARC working group actually used the mechanistic data: "Not used",
    # "Supportive" or "Upgrade". Only the 10yr label track carries this, and a
    # high score with data_role="Not used" means IARC did not rely on it.
    data_role: Mapped[str | None] = mapped_column(String(16))
    n_refs: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    curator_notes: Mapped[str | None] = mapped_column(Text)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped["Agent"] = relationship(back_populates="evidence_rows")
    kcc: Mapped["KCC"] = relationship(back_populates="evidence_rows")
    citations: Mapped[list["EvidenceCitation"]] = relationship(back_populates="evidence", cascade="all, delete-orphan")
    revisions: Mapped[list["Revision"]] = relationship(back_populates="evidence")


class EvidenceCitation(Base):
    __tablename__ = "evidence_citations"

    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True)
    reference_id: Mapped[str] = mapped_column(ForeignKey("references.id", ondelete="CASCADE"), primary_key=True)

    evidence: Mapped["Evidence"] = relationship(back_populates="citations")
    reference: Mapped["Reference"] = relationship(back_populates="evidence_links")


class Assay(Base):
    __tablename__ = "assays"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(String(128), nullable=False)
    throughput: Mapped[str] = mapped_column(String(32), nullable=False)
    oecd_tg: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    # Provenance: "kcad" (Rigutto et al. 2025), "manual", or future importer tags.
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", server_default="manual")
    # "assay" for concrete methods; "category" for KCAD coarse method labels that curators may later split.
    granularity: Mapped[str] = mapped_column(String(16), nullable=False, default="assay", server_default="assay")
    # FK to the publication this assay was sourced from (Rigutto et al. 2025 for KCAD rows).
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), index=True)
    # Cleaned/canonical alternative spelling of `name` (preserves search compatibility
    # when Supplementary Tables 4/5 give the primary name its proper punctuation).
    name_alt: Mapped[str | None] = mapped_column(String(255))

    kcc_links: Mapped[list["AssayKCC"]] = relationship(back_populates="assay", cascade="all, delete-orphan")
    annotations: Mapped[list["AssayAnnotation"]] = relationship(back_populates="assay", cascade="all, delete-orphan")
    kc_subgroups: Mapped[list["AssayKcSubgroup"]] = relationship(back_populates="assay", cascade="all, delete-orphan")
    study_designs: Mapped[list["AssayStudyDesign"]] = relationship(back_populates="assay", cascade="all, delete-orphan")


class AssayKCC(Base):
    __tablename__ = "assay_kccs"

    assay_id: Mapped[str] = mapped_column(ForeignKey("assays.id", ondelete="CASCADE"), primary_key=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), primary_key=True)

    assay: Mapped["Assay"] = relationship(back_populates="kcc_links")
    kcc: Mapped["KCC"] = relationship(back_populates="assay_links")


class Reference(Base):
    __tablename__ = "references"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    year: Mapped[int | None] = mapped_column(SmallInteger)
    authors: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    journal: Mapped[str] = mapped_column(String(255), nullable=False)
    vol: Mapped[str | None] = mapped_column(String(128))
    pages: Mapped[str | None] = mapped_column(String(64))
    doi: Mapped[str | None] = mapped_column(String(128))
    pmid: Mapped[str | None] = mapped_column(String(16))
    citations: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", server_default="manual")
    # OUP / journal-specific article identifier (e.g. "baaf026" for the KCAD paper).
    article_id: Mapped[str | None] = mapped_column(String(64))
    # Optional URL pointing to the canonical hosted version (DOI page, journal PDF, etc.).
    url: Mapped[str | None] = mapped_column(String(512))
    # Set when the source row conflated several distinct citations into one record
    # (e.g. a KCAD DOI cell holding multiple space-separated DOIs). Such rows are
    # auto-split into child references by `pipelines.normalize_references`; the
    # original is retained, flagged here, for curator review of the inbound links.
    needs_split: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    # Verbatim citation/identifier text as it arrived from the source, preserved so
    # parsing/splitting is never lossy and provenance is always traceable.
    raw_citation: Mapped[str | None] = mapped_column(Text)

    identifiers: Mapped[list["ReferenceIdentifier"]] = relationship(
        back_populates="reference", cascade="all, delete-orphan"
    )
    tags: Mapped[list["ReferenceTag"]] = relationship(back_populates="reference", cascade="all, delete-orphan")
    kcc_links: Mapped[list["ReferenceKCC"]] = relationship(back_populates="reference", cascade="all, delete-orphan")
    evidence_links: Mapped[list["EvidenceCitation"]] = relationship(back_populates="reference")
    agent_links: Mapped[list["AgentReference"]] = relationship(back_populates="reference", cascade="all, delete-orphan")


class ReferenceIdentifier(Base):
    """One external identifier (DOI, PMID, PMCID, …) for a single reference.

    Replaces the old practice of stuffing several space-separated identifiers into
    the flat ``references.doi`` / ``references.pmid`` columns. A reference may carry
    several identifiers (e.g. a preprint DOI + a published DOI + a PMID); each gets
    its own row. ``id_value`` is stored normalized (lowercased DOI, digits-only
    PMID) so it can be joined/looked up directly by the resolver — the human-facing
    original still lives on ``references.doi`` / ``references.pmid``.

    The ``(id_type, id_value)`` pair is globally unique: an identifier resolves to
    exactly one reference, which is what makes deterministic linking possible.
    """

    __tablename__ = "reference_identifiers"
    __table_args__ = (
        UniqueConstraint("id_type", "id_value", name="uq_reference_identifier"),
        Index("ix_reference_identifier_ref", "reference_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference_id: Mapped[str] = mapped_column(ForeignKey("references.id", ondelete="CASCADE"), nullable=False)
    # "doi" | "pmid" | "pmcid" | "url" | future schemes.
    id_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Normalized identifier value (lowercase DOI, digits-only PMID).
    id_value: Mapped[str] = mapped_column(String(255), nullable=False)
    # The single identifier displayed/cited as canonical for the reference.
    is_canonical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    reference: Mapped["Reference"] = relationship(back_populates="identifiers")


class ReferenceTag(Base):
    __tablename__ = "reference_tags"

    reference_id: Mapped[str] = mapped_column(ForeignKey("references.id", ondelete="CASCADE"), primary_key=True)
    tag: Mapped[str] = mapped_column(String(64), primary_key=True)

    reference: Mapped["Reference"] = relationship(back_populates="tags")


class ReferenceKCC(Base):
    __tablename__ = "reference_kccs"

    reference_id: Mapped[str] = mapped_column(ForeignKey("references.id", ondelete="CASCADE"), primary_key=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), primary_key=True)

    reference: Mapped["Reference"] = relationship(back_populates="kcc_links")
    kcc: Mapped["KCC"] = relationship(back_populates="reference_links")


class Curator(Base):
    __tablename__ = "curators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    orcid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    affiliation: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="curator")

    revisions: Mapped[list["Revision"]] = relationship(back_populates="curator")


class Revision(Base):
    __tablename__ = "revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False)
    curator_id: Mapped[int | None] = mapped_column(ForeignKey("curators.id", ondelete="SET NULL"))
    proposed_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional self-declared attribution for an unauthenticated proposal. Kept
    # in its own column so the rationale stays the scientific argument alone.
    submitted_by: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evidence: Mapped["Evidence"] = relationship(back_populates="revisions")
    curator: Mapped["Curator | None"] = relationship(back_populates="revisions")


class DatasetRelease(Base):
    """Tagged dataset versions for export and Zenodo archive."""

    __tablename__ = "dataset_releases"

    tag: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    zenodo_doi: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)


class AgentReference(Base):
    """Direct agent ↔ reference links (independent of evidence scores).

    Derived from the KCAD `Monograph_chem → agent` mapping.
    Lets the Agent Detail / Carcinogens page surface KCAD-cited literature even
    when no curator-scored Evidence row exists yet.
    """

    __tablename__ = "agent_references"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    reference_id: Mapped[str] = mapped_column(ForeignKey("references.id", ondelete="CASCADE"), primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="kcad", server_default="kcad")

    agent: Mapped["Agent"] = relationship(back_populates="reference_links")
    reference: Mapped["Reference"] = relationship(back_populates="agent_links")


class AssayAnnotation(Base):
    """One row per KCAD study-level annotation.

    Keeps the queryable structure (tissue × design × organism × monograph chem ×
    PMID) that gets lost if we collapse KCAD into the flat `Assay.notes` column.
    """

    __tablename__ = "assay_annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assay_id: Mapped[str] = mapped_column(ForeignKey("assays.id", ondelete="CASCADE"), nullable=False, index=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), nullable=False, index=True)
    secondary_kcc_id: Mapped[str | None] = mapped_column(ForeignKey("kccs.id", ondelete="SET NULL"))
    # Raw `Secondary KC` cell as-is; covers KCAD cells listing multiple KCs (e.g. "3  9") that
    # cannot be normalised to a single FK without losing information.
    secondary_kc_raw: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"))
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), index=True)

    kc_subgroup: Mapped[str | None] = mapped_column(String(255))
    kc_subgroup2: Mapped[str | None] = mapped_column(String(255))
    effect: Mapped[str | None] = mapped_column(String(64))
    assay_endpoint: Mapped[str | None] = mapped_column(String(255))
    assay_endpoint2: Mapped[str | None] = mapped_column(String(255))
    assay_endpoint3: Mapped[str | None] = mapped_column(String(128))
    biomarker: Mapped[str | None] = mapped_column(String(255))
    method2: Mapped[str | None] = mapped_column(Text)
    stimulant_activation_agent: Mapped[str | None] = mapped_column(String(255))
    target_cell: Mapped[str | None] = mapped_column(String(128))
    organism: Mapped[str | None] = mapped_column(String(128))
    species: Mapped[str | None] = mapped_column(String(64))
    mammalian: Mapped[str | None] = mapped_column(String(16))
    tissue: Mapped[str | None] = mapped_column(String(128))
    tissue2: Mapped[str | None] = mapped_column(String(64))
    cell_type: Mapped[str | None] = mapped_column(String(128))
    immortalized: Mapped[str | None] = mapped_column(String(16))
    cell_format: Mapped[str | None] = mapped_column(String(64))
    design: Mapped[str | None] = mapped_column(String(64))
    design_transgenic: Mapped[str | None] = mapped_column(String(64))
    monograph_num: Mapped[str | None] = mapped_column(String(32))
    monograph_chem: Mapped[str | None] = mapped_column(String(255), index=True)
    oecd_tg: Mapped[str | None] = mapped_column(String(64))
    cebp_ref_idx: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="kcad", server_default="kcad")
    # FK to the publication this annotation was sourced from (Rigutto et al. 2025 for KCAD rows).
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), index=True)

    @property
    def secondary_kcc_ids(self) -> list[str]:
        """Every KC named in ``secondary_kc_raw``, not just the first.

        ``secondary_kcc_id`` is a single FK, so a KCAD cell reading "3  9" or
        "10  9?" kept only its first KC and silently dropped the other — a
        filter on secondary KC would undercount those pairs. Four annotations
        are affected, in two distinct patterns, so the value is derived here
        rather than given a junction table.

        A "?" in the source marks an uncertain assignment. The KC is included
        (the cell does name it) and the qualifier stays visible in
        ``secondary_kc_raw``, which is exposed alongside this field.
        """
        raw = (self.secondary_kc_raw or "").strip()
        if not raw:
            return [self.secondary_kcc_id] if self.secondary_kcc_id else []
        ids = []
        for token in raw.replace(",", " ").split():
            digits = token.rstrip("?").strip()
            if digits.isdigit():
                kcc_id = f"kcc-{int(digits):02d}"
                if kcc_id not in ids:
                    ids.append(kcc_id)
        return ids or ([self.secondary_kcc_id] if self.secondary_kcc_id else [])

    assay: Mapped["Assay"] = relationship(back_populates="annotations")
    # Full citation set for this study row. The scalar `reference_id` above is kept
    # as a denormalized position-1 "primary" pointer for back-compat; this bridge
    # carries every work the row cites (a KCAD row may cite 1–5 papers).
    references: Mapped[list["AnnotationReference"]] = relationship(
        back_populates="annotation",
        cascade="all, delete-orphan",
        order_by="AnnotationReference.position",
    )


class AnnotationReference(Base):
    """Bridge: one row per (annotation, cited work).

    Replaces the single-citation limitation of ``AssayAnnotation.reference_id`` —
    a KCAD annotation row can weld 1–5 distinct papers into its DOI /
    PMID / Citation cells. ``position`` preserves the source ordering (position 1
    is the citation-bearing primary, mirrored onto ``AssayAnnotation.reference_id``).
    ``id_type`` records which identifier resolved the link (``doi`` / ``pmid`` /
    ``citation``); ``citation`` rows are best-effort author+year matches and may be
    absent when no canonical reference could be resolved.
    """

    __tablename__ = "annotation_references"

    annotation_id: Mapped[int] = mapped_column(ForeignKey("assay_annotations.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    reference_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), index=True)
    id_type: Mapped[str] = mapped_column(String(16), nullable=False)

    annotation: Mapped["AssayAnnotation"] = relationship(back_populates="references")
    reference: Mapped["Reference | None"] = relationship()


class AssayKcSubgroup(Base):
    """Paper-authoritative subgroup label per (assay, KC) pair.

    Sourced from Supplementary Tables 4 and 5: each assay row sits under a subgroup
    header (e.g. "DNA adducts", "Protein Adducts", "Activates or antagonizes receptors").
    A single subgroup per (assay_id, kcc_id) pair — confirmed by the layout.
    """

    __tablename__ = "assay_kc_subgroups"

    assay_id: Mapped[str] = mapped_column(ForeignKey("assays.id", ondelete="CASCADE"), primary_key=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), primary_key=True)
    subgroup: Mapped[str] = mapped_column(String(255), nullable=False)
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"))

    assay: Mapped["Assay"] = relationship(back_populates="kc_subgroups")


class AssayStudyDesign(Base):
    """Study designs an assay supports for a given KC (Supplementary Tables 4/5).

    Designs: ``in_vivo``, ``ex_vivo`` (Supplementary Table 4), ``in_vitro``,
    ``in_silico`` (Supplementary Table 5). Multiple designs per (assay_id,
    kcc_id) are common.
    """

    __tablename__ = "assay_study_designs"

    assay_id: Mapped[str] = mapped_column(ForeignKey("assays.id", ondelete="CASCADE"), primary_key=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), primary_key=True)
    design: Mapped[str] = mapped_column(String(16), primary_key=True)
    # 'stable4' or 'stable5' — which supplementary table this row came from.
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"))

    assay: Mapped["Assay"] = relationship(back_populates="study_designs")


class KcadAbbreviation(Base):
    """Abbreviation glossary, from Supplementary Table 3 of the KCAD paper."""

    __tablename__ = "kcad_abbreviations"

    abbreviation: Mapped[str] = mapped_column(String(64), primary_key=True)
    expansion: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"))


class KcadColumnDefinition(Base):
    """Column-by-column data dictionary, from Supplementary Table 2.

    Documents what each KCAD annotation column means. Surfaced on the
    Methodology page and via ``GET /schema/columns``.
    """

    __tablename__ = "kcad_column_definitions"

    column_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Verbatim from Supplementary Table 2, including its typos. Never rewritten:
    # this is the published record and must stay quotable.
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    # What the column actually holds in this database, where the published
    # definition does not describe it. Three columns are affected:
    # `Monograph_num` and `Monograph_chem` carry each other's definitions, and
    # `Biomarker` repeats the text belonging to `Stimulant_activation_agent`.
    # The corrections live beside the source text rather than replacing it.
    hkcc_note: Mapped[str | None] = mapped_column(Text)
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"))


class IarcMonographKcCall(Base):
    """Per-(volume, agent, model-system) Yes/No/Equivocal/Protective call for one KC.

    Sourced from Rusyn et al. 2024 (Tox Sci) Supplementary File 12 — the 10-year
    KCC retrospective. One row per non-blank cell in the 19 IARC-Monograph-volume
    sheets (Vol 112–130). Cell values are paper-verbatim:

    - ``Yes``        — convincing evidence the agent exhibits this KC
    - ``No``         — convincing evidence the agent does NOT exhibit this KC
    - ``Equivocal``  — mixed / inconclusive evidence
    - ``Protective`` — agent ACTIVELY SUPPRESSES this KC (subsumes Antioxidant /
                      Antiinflammatory variants seen in Vol 116). The raw verbatim
                      label is preserved in ``raw_call``.

    See :doc:`KCC_EVIDENCE_RULES` for the score-aggregation algorithm that
    derives ``Evidence.score`` from these rows.
    """

    __tablename__ = "iarc_monograph_kc_calls"
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "kcc_id",
            "monograph_volume",
            "model_system",
            name="uq_iarc_call_quad",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), nullable=False, index=True)
    monograph_volume: Mapped[str] = mapped_column(String(16), nullable=False)
    monograph_year: Mapped[int | None] = mapped_column(SmallInteger)
    model_system: Mapped[str] = mapped_column(String(32), nullable=False)
    call: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_call: Mapped[str | None] = mapped_column(String(64))
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), index=True)


class IarcMonographKcStrength(Base):
    """Standardized qualitative strength label per (agent, KC).

    Sourced from Rusyn et al. 2024 Supplementary File 14 (Supp Table 4 —
    standardized terms). 73 agents × 10 KCs with values in
    {``Strong``, ``Moderate``, ``Weak``}. Each row also records the IARC
    Working-Group ``data_role`` (``Supportive``, ``Upgrade``, ``Not used``)
    indicating how that KC profile fed into the final monograph evaluation.

    Stored as a sibling table (rather than columns on ``Evidence``) so that
    the paper-specific provenance stays clean: an Evidence row may aggregate
    multiple sources, but a strength label belongs to exactly one publication.
    """

    __tablename__ = "iarc_monograph_kc_strength"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), primary_key=True)
    strength_label: Mapped[str] = mapped_column(String(16), nullable=False)
    data_role: Mapped[str | None] = mapped_column(String(32))
    iarc_group: Mapped[str | None] = mapped_column(String(8))
    source_ref_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"), index=True)
