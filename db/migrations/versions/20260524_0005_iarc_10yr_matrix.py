"""IARC 10-year retrospective evidence matrix.

Adds two tables sourced from Rusyn et al. 2024 (Tox Sci) Supplementary Files
12 and 14 (the 10-year KCC retrospective covering IARC Monograph Vol 112–130):

1. ``iarc_monograph_kc_calls``    — per-(volume, agent, model-system, KC)
                                    Yes / No / Equivocal / Protective call.
2. ``iarc_monograph_kc_strength`` — per-(agent, KC) standardized Strong /
                                    Moderate / Weak label + IARC data role.

Each row is anchored to a Reference via ``source_ref_id`` for full provenance.

Revision ID: 20260524_0005
Revises: 20260523_0004
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260524_0005"
down_revision: str | None = "20260523_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("references", sa.Column("pdf_path", sa.String(512)))

    op.create_table(
        "iarc_monograph_kc_calls",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "agent_id",
            sa.String(64),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kcc_id",
            sa.String(32),
            sa.ForeignKey("kccs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("monograph_volume", sa.String(16), nullable=False),
        sa.Column("monograph_year", sa.SmallInteger()),
        sa.Column("model_system", sa.String(32), nullable=False),
        sa.Column("call", sa.String(16), nullable=False),
        sa.Column("raw_call", sa.String(64)),
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
        sa.UniqueConstraint(
            "agent_id",
            "kcc_id",
            "monograph_volume",
            "model_system",
            name="uq_iarc_call_quad",
        ),
    )
    op.create_index("ix_iarc_call_agent", "iarc_monograph_kc_calls", ["agent_id"])
    op.create_index("ix_iarc_call_kcc", "iarc_monograph_kc_calls", ["kcc_id"])
    op.create_index(
        "ix_iarc_call_source_ref", "iarc_monograph_kc_calls", ["source_ref_id"]
    )

    op.create_table(
        "iarc_monograph_kc_strength",
        sa.Column(
            "agent_id",
            sa.String(64),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "kcc_id",
            sa.String(32),
            sa.ForeignKey("kccs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("strength_label", sa.String(16), nullable=False),
        sa.Column("data_role", sa.String(32)),
        sa.Column("iarc_group", sa.String(8)),
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
    )
    op.create_index(
        "ix_iarc_strength_source_ref",
        "iarc_monograph_kc_strength",
        ["source_ref_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_iarc_strength_source_ref", table_name="iarc_monograph_kc_strength")
    op.drop_table("iarc_monograph_kc_strength")

    op.drop_index("ix_iarc_call_source_ref", table_name="iarc_monograph_kc_calls")
    op.drop_index("ix_iarc_call_kcc", table_name="iarc_monograph_kc_calls")
    op.drop_index("ix_iarc_call_agent", table_name="iarc_monograph_kc_calls")
    op.drop_table("iarc_monograph_kc_calls")

    op.drop_column("references", "pdf_path")
