"""Annotation ↔ reference bridge (1–5 citations per study row).

The KCAD ``filtered_table.csv`` welds 1–5 distinct papers into a single row's
DOI / PMID / Citation cells. The scalar ``assay_annotations.reference_id`` FK
could only record one of them, silently truncating multi-citation rows. This
adds an ``annotation_references`` bridge that carries every cited work, ordered
by ``position`` (position 1 = the citation-bearing primary, still mirrored onto
``assay_annotations.reference_id`` for back-compat).

Also adds ``references.pages`` so enriched bibliographic metadata (from
``references_update.xlsx`` → ``enriched_references``) folds into the existing
``references`` table without a parallel key scheme — the workbook ``ref_id``
(R00001…) cross-walk lives in ``reference_identifiers`` under ``id_type='kcad_refkey'``.

Revision ID: 20260608_0007
Revises: 20260603_0006
Create Date: 2026-06-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260608_0007"
down_revision: str | None = "20260603_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("references", sa.Column("pages", sa.String(64)))

    op.create_table(
        "annotation_references",
        sa.Column(
            "annotation_id",
            sa.Integer(),
            sa.ForeignKey("assay_annotations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.SmallInteger(), primary_key=True),
        sa.Column(
            "reference_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
        sa.Column("id_type", sa.String(16), nullable=False),
    )
    op.create_index(
        "ix_annotation_reference_ref", "annotation_references", ["reference_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_annotation_reference_ref", table_name="annotation_references")
    op.drop_table("annotation_references")
    op.drop_column("references", "pages")
