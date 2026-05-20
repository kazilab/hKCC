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


class AssayOut(BaseModel):
    id: str
    name: str
    type: str
    target: str
    throughput: str
    oecd_tg: str | None
    notes: str | None
    kcc_ids: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ReferenceOut(BaseModel):
    id: str
    year: int | None
    authors: str
    title: str
    journal: str
    vol: str | None
    doi: str | None
    citations: int | None
    tags: list[str] = Field(default_factory=list)
    kcc_ids: list[str] = Field(default_factory=list)

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
