"""SQLAlchemy models for hKCC."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
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
    is_extended: Mapped[bool] = mapped_column(default=False, nullable=False)

    evidence_rows: Mapped[list["Evidence"]] = relationship(back_populates="kcc")
    assay_links: Mapped[list["AssayKCC"]] = relationship(back_populates="kcc")
    reference_links: Mapped[list["ReferenceKCC"]] = relationship(back_populates="kcc")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cas: Mapped[str | None] = mapped_column(String(32))
    iarc_group: Mapped[str | None] = mapped_column(String(8))
    agent_type: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sites: Mapped[list["AgentSite"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    evidence_rows: Mapped[list["Evidence"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    reference_links: Mapped[list["AgentReference"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


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
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    n_refs: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    curator_notes: Mapped[str | None] = mapped_column(Text)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped["Agent"] = relationship(back_populates="evidence_rows")
    kcc: Mapped["KCC"] = relationship(back_populates="evidence_rows")
    citations: Mapped[list["EvidenceCitation"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )
    revisions: Mapped[list["Revision"]] = relationship(back_populates="evidence")


class EvidenceCitation(Base):
    __tablename__ = "evidence_citations"

    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True
    )
    reference_id: Mapped[str] = mapped_column(
        ForeignKey("references.id", ondelete="CASCADE"), primary_key=True
    )

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
    # Provenance: "mockup" (data.js demo), "kcad" (Rigutto et al. 2025), future imports add their own tag.
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="mockup", server_default="mockup")
    # "assay" for concrete methods; "category" for KCAD coarse method labels that curators may later split.
    granularity: Mapped[str] = mapped_column(String(16), nullable=False, default="assay", server_default="assay")

    kcc_links: Mapped[list["AssayKCC"]] = relationship(back_populates="assay", cascade="all, delete-orphan")
    annotations: Mapped[list["AssayAnnotation"]] = relationship(
        back_populates="assay", cascade="all, delete-orphan"
    )


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
    doi: Mapped[str | None] = mapped_column(String(128))
    pmid: Mapped[str | None] = mapped_column(String(16))
    citations: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="mockup", server_default="mockup")

    tags: Mapped[list["ReferenceTag"]] = relationship(back_populates="reference", cascade="all, delete-orphan")
    kcc_links: Mapped[list["ReferenceKCC"]] = relationship(
        back_populates="reference", cascade="all, delete-orphan"
    )
    evidence_links: Mapped[list["EvidenceCitation"]] = relationship(back_populates="reference")
    agent_links: Mapped[list["AgentReference"]] = relationship(
        back_populates="reference", cascade="all, delete-orphan"
    )


class ReferenceTag(Base):
    __tablename__ = "reference_tags"

    reference_id: Mapped[str] = mapped_column(
        ForeignKey("references.id", ondelete="CASCADE"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(String(64), primary_key=True)

    reference: Mapped["Reference"] = relationship(back_populates="tags")


class ReferenceKCC(Base):
    __tablename__ = "reference_kccs"

    reference_id: Mapped[str] = mapped_column(
        ForeignKey("references.id", ondelete="CASCADE"), primary_key=True
    )
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

    Populated by `pipelines.import_kcad` from `Monograph_chem → agent` mapping.
    Lets the Agent Detail / Carcinogens page surface KCAD-cited literature even
    when no curator-scored Evidence row exists yet.
    """

    __tablename__ = "agent_references"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    reference_id: Mapped[str] = mapped_column(
        ForeignKey("references.id", ondelete="CASCADE"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="kcad", server_default="kcad")

    agent: Mapped["Agent"] = relationship(back_populates="reference_links")
    reference: Mapped["Reference"] = relationship(back_populates="agent_links")


class AssayAnnotation(Base):
    """One row per KCAD study-level annotation (`filtered_table.csv`).

    Keeps the queryable structure (tissue × design × organism × monograph chem ×
    PMID) that gets lost if we collapse KCAD into the flat `Assay.notes` column.
    """

    __tablename__ = "assay_annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assay_id: Mapped[str] = mapped_column(ForeignKey("assays.id", ondelete="CASCADE"), nullable=False, index=True)
    kcc_id: Mapped[str] = mapped_column(ForeignKey("kccs.id", ondelete="CASCADE"), nullable=False, index=True)
    secondary_kcc_id: Mapped[str | None] = mapped_column(ForeignKey("kccs.id", ondelete="SET NULL"))
    reference_id: Mapped[str | None] = mapped_column(ForeignKey("references.id", ondelete="SET NULL"))
    agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), index=True
    )

    kc_subgroup: Mapped[str | None] = mapped_column(String(255))
    assay_endpoint: Mapped[str | None] = mapped_column(String(255))
    biomarker: Mapped[str | None] = mapped_column(String(255))
    organism: Mapped[str | None] = mapped_column(String(128))
    species: Mapped[str | None] = mapped_column(String(64))
    tissue: Mapped[str | None] = mapped_column(String(128))
    cell_type: Mapped[str | None] = mapped_column(String(128))
    cell_format: Mapped[str | None] = mapped_column(String(64))
    design: Mapped[str | None] = mapped_column(String(64))
    monograph_num: Mapped[str | None] = mapped_column(String(32))
    monograph_chem: Mapped[str | None] = mapped_column(String(255), index=True)
    oecd_tg: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="kcad", server_default="kcad")

    assay: Mapped["Assay"] = relationship(back_populates="annotations")
