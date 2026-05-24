"""KCAD integration: provenance columns + study annotations + agent_references.

Revision ID: 20260523_0002
Revises: 20260519_0001
Create Date: 2026-05-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260523_0002"
down_revision: str | None = "20260519_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assays",
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
    )
    op.add_column(
        "assays",
        sa.Column("granularity", sa.String(16), nullable=False, server_default="assay"),
    )
    op.create_index("ix_assays_source", "assays", ["source"])

    op.add_column("references", sa.Column("pmid", sa.String(16)))
    op.add_column(
        "references",
        sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
    )
    op.create_index("ix_references_pmid", "references", ["pmid"])
    op.create_index("ix_references_source", "references", ["source"])

    op.create_table(
        "agent_references",
        sa.Column(
            "agent_id",
            sa.String(64),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "reference_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("source", sa.String(32), nullable=False, server_default="kcad"),
    )

    op.create_table(
        "assay_annotations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "assay_id",
            sa.String(64),
            sa.ForeignKey("assays.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kcc_id",
            sa.String(32),
            sa.ForeignKey("kccs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("secondary_kcc_id", sa.String(32), sa.ForeignKey("kccs.id", ondelete="SET NULL")),
        sa.Column(
            "reference_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.id", ondelete="SET NULL")),
        sa.Column("kc_subgroup", sa.String(255)),
        sa.Column("assay_endpoint", sa.String(255)),
        sa.Column("biomarker", sa.String(255)),
        sa.Column("organism", sa.String(128)),
        sa.Column("species", sa.String(64)),
        sa.Column("tissue", sa.String(128)),
        sa.Column("cell_type", sa.String(128)),
        sa.Column("cell_format", sa.String(64)),
        sa.Column("design", sa.String(64)),
        sa.Column("monograph_num", sa.String(32)),
        sa.Column("monograph_chem", sa.String(255)),
        sa.Column("oecd_tg", sa.String(64)),
        sa.Column("source", sa.String(32), nullable=False, server_default="kcad"),
    )
    op.create_index("ix_annot_assay", "assay_annotations", ["assay_id"])
    op.create_index("ix_annot_kcc", "assay_annotations", ["kcc_id"])
    op.create_index("ix_annot_agent", "assay_annotations", ["agent_id"])
    op.create_index("ix_annot_chem", "assay_annotations", ["monograph_chem"])


def downgrade() -> None:
    op.drop_index("ix_annot_chem", table_name="assay_annotations")
    op.drop_index("ix_annot_agent", table_name="assay_annotations")
    op.drop_index("ix_annot_kcc", table_name="assay_annotations")
    op.drop_index("ix_annot_assay", table_name="assay_annotations")
    op.drop_table("assay_annotations")
    op.drop_table("agent_references")

    op.drop_index("ix_references_source", table_name="references")
    op.drop_index("ix_references_pmid", table_name="references")
    op.drop_column("references", "source")
    op.drop_column("references", "pmid")

    op.drop_index("ix_assays_source", table_name="assays")
    op.drop_column("assays", "granularity")
    op.drop_column("assays", "source")
