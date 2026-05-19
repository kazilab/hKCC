"""Initial hKCC schema.

Revision ID: 20260519_0001
Revises:
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260519_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kccs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("n", sa.SmallInteger(), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("short", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("mechanism", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(32), nullable=False),
        sa.Column("is_extended", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "agents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("cas", sa.String(32)),
        sa.Column("iarc_group", sa.String(8)),
        sa.Column("agent_type", sa.String(128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("last_review", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "agent_sites",
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("site", sa.String(255), primary_key=True),
    )
    op.create_table(
        "references",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("year", sa.SmallInteger()),
        sa.Column("authors", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("journal", sa.String(255), nullable=False),
        sa.Column("vol", sa.String(128)),
        sa.Column("doi", sa.String(128)),
        sa.Column("citations", sa.Integer()),
    )
    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kcc_id", sa.String(32), sa.ForeignKey("kccs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("n_refs", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("curator_notes", sa.Text()),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("score >= 0 AND score <= 4", name="ck_evidence_score"),
        sa.UniqueConstraint("agent_id", "kcc_id", name="uq_evidence_agent_kcc"),
    )
    op.create_table(
        "evidence_citations",
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("reference_id", sa.String(64), sa.ForeignKey("references.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "assays",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("target", sa.String(128), nullable=False),
        sa.Column("throughput", sa.String(32), nullable=False),
        sa.Column("oecd_tg", sa.String(64)),
        sa.Column("notes", sa.Text()),
    )
    op.create_table(
        "assay_kccs",
        sa.Column("assay_id", sa.String(64), sa.ForeignKey("assays.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("kcc_id", sa.String(32), sa.ForeignKey("kccs.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "reference_tags",
        sa.Column("reference_id", sa.String(64), sa.ForeignKey("references.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag", sa.String(64), primary_key=True),
    )
    op.create_table(
        "reference_kccs",
        sa.Column("reference_id", sa.String(64), sa.ForeignKey("references.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("kcc_id", sa.String(32), sa.ForeignKey("kccs.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "curators",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("orcid", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("affiliation", sa.String(255)),
        sa.Column("role", sa.String(32), nullable=False, server_default="curator"),
    )
    op.create_table(
        "revisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False),
        sa.Column("curator_id", sa.Integer(), sa.ForeignKey("curators.id", ondelete="SET NULL")),
        sa.Column("proposed_score", sa.SmallInteger(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "dataset_releases",
        sa.Column("tag", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("zenodo_doi", sa.String(128)),
        sa.Column("notes", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("dataset_releases")
    op.drop_table("revisions")
    op.drop_table("curators")
    op.drop_table("reference_kccs")
    op.drop_table("reference_tags")
    op.drop_table("assay_kccs")
    op.drop_table("assays")
    op.drop_table("evidence_citations")
    op.drop_table("evidence")
    op.drop_table("references")
    op.drop_table("agent_sites")
    op.drop_table("agents")
    op.drop_table("kccs")
