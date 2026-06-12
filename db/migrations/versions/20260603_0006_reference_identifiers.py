"""Normalized reference identifiers + conflation flags.

Replaces the multi-valued ``references.doi`` / ``references.pmid`` blobs (where a
KCAD source cell could hold several space-separated DOIs) with a child table that
holds exactly one identifier per row:

    reference_identifiers(reference_id, id_type, id_value, is_canonical)

with ``(id_type, id_value)`` globally unique, so an identifier resolves to exactly
one reference. Two bookkeeping columns are added to ``references``:

- ``needs_split``  — flags rows that conflated several distinct citations (the
                     auto-split worklist for curators).
- ``raw_citation`` — verbatim source identifier text, kept so splitting is lossless.

Backfill of the new table from existing rows is handled out-of-band by
``pipelines.normalize_references`` (it also performs the auto-split), not in this
migration, to keep the schema change reversible and side-effect free.

Revision ID: 20260603_0006
Revises: 20260524_0005
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0006"
down_revision: str | None = "20260524_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "references",
        sa.Column(
            "needs_split", sa.Boolean(), nullable=False, server_default="0"
        ),
    )
    op.add_column("references", sa.Column("raw_citation", sa.Text()))

    op.create_table(
        "reference_identifiers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "reference_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("id_type", sa.String(16), nullable=False),
        sa.Column("id_value", sa.String(255), nullable=False),
        sa.Column(
            "is_canonical", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.UniqueConstraint("id_type", "id_value", name="uq_reference_identifier"),
    )
    op.create_index(
        "ix_reference_identifier_ref", "reference_identifiers", ["reference_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reference_identifier_ref", table_name="reference_identifiers"
    )
    op.drop_table("reference_identifiers")
    op.drop_column("references", "raw_citation")
    op.drop_column("references", "needs_split")
