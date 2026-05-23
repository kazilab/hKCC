"""KCAD paper anchor + supplementary-table extensions.

Adds:

1. Paper-anchor FKs (``source_ref_id``) on ``agents``, ``assays``, ``assay_annotations``
   so every KCAD-derived row points back to the canonical publication record
   (``kcad-paper-rigutto-2025`` → Rigutto et al. 2025, ``10.1093/database/baaf026``).
2. IARC metadata columns on ``agents`` populated from ``KCManuscript_STable1``:
   ``monograph_volume``, ``monograph_pub_year``, ``evaluation_year``.
3. Article identifier and URL on ``references`` (``article_id``, ``url``).
4. ``assays.name_alt`` for canonical-name reconciliation (STable4/5 punctuation
   fix without losing the original CSV form).
5. Four new tables for the supplementary-table data:
   - ``assay_kc_subgroups``      — one paper-authoritative subgroup per (assay, KC).
   - ``assay_study_designs``     — in_vivo/ex_vivo/in_vitro/in_silico per (assay, KC).
   - ``kcad_abbreviations``      — 49-row glossary (STable3).
   - ``kcad_column_definitions`` — 28-row data dictionary (STable2).

Revision ID: 20260523_0004
Revises: 20260523_0003
Create Date: 2026-05-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260523_0004"
down_revision: str | None = "20260523_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. Reference extensions ──────────────────────────────────────────────
    op.add_column("references", sa.Column("article_id", sa.String(64)))
    op.add_column("references", sa.Column("url", sa.String(512)))

    # ── 2. Agent extensions: IARC metadata + paper anchor ───────────────────
    op.add_column("agents", sa.Column("monograph_volume", sa.String(64)))
    op.add_column("agents", sa.Column("monograph_pub_year", sa.String(32)))
    op.add_column("agents", sa.Column("evaluation_year", sa.SmallInteger()))
    op.add_column(
        "agents",
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
    )
    op.create_index("ix_agents_source_ref", "agents", ["source_ref_id"])

    # ── 3. Assay paper anchor + alt-name slot ────────────────────────────────
    op.add_column(
        "assays",
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
    )
    op.add_column("assays", sa.Column("name_alt", sa.String(255)))
    op.create_index("ix_assays_source_ref", "assays", ["source_ref_id"])

    # ── 4. Annotation paper anchor ───────────────────────────────────────────
    op.add_column(
        "assay_annotations",
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
    )
    op.create_index(
        "ix_annot_source_ref", "assay_annotations", ["source_ref_id"]
    )

    # ── 5. STable4/5: paper-authoritative subgroup taxonomy ──────────────────
    op.create_table(
        "assay_kc_subgroups",
        sa.Column(
            "assay_id",
            sa.String(64),
            sa.ForeignKey("assays.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "kcc_id",
            sa.String(32),
            sa.ForeignKey("kccs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("subgroup", sa.String(255), nullable=False),
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
    )

    # ── 6. STable4/5: study-design tagging ───────────────────────────────────
    op.create_table(
        "assay_study_designs",
        sa.Column(
            "assay_id",
            sa.String(64),
            sa.ForeignKey("assays.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "kcc_id",
            sa.String(32),
            sa.ForeignKey("kccs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("design", sa.String(16), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
    )

    # ── 7. STable3: abbreviations glossary ───────────────────────────────────
    op.create_table(
        "kcad_abbreviations",
        sa.Column("abbreviation", sa.String(64), primary_key=True),
        sa.Column("expansion", sa.Text(), nullable=False),
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
    )

    # ── 8. STable2: column dictionary ────────────────────────────────────────
    op.create_table(
        "kcad_column_definitions",
        sa.Column("column_name", sa.String(64), primary_key=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column(
            "source_ref_id",
            sa.String(64),
            sa.ForeignKey("references.id", ondelete="SET NULL"),
        ),
    )


def downgrade() -> None:
    op.drop_table("kcad_column_definitions")
    op.drop_table("kcad_abbreviations")
    op.drop_table("assay_study_designs")
    op.drop_table("assay_kc_subgroups")

    op.drop_index("ix_annot_source_ref", table_name="assay_annotations")
    op.drop_column("assay_annotations", "source_ref_id")

    op.drop_index("ix_assays_source_ref", table_name="assays")
    op.drop_column("assays", "name_alt")
    op.drop_column("assays", "source_ref_id")

    op.drop_index("ix_agents_source_ref", table_name="agents")
    op.drop_column("agents", "source_ref_id")
    op.drop_column("agents", "evaluation_year")
    op.drop_column("agents", "monograph_pub_year")
    op.drop_column("agents", "monograph_volume")

    op.drop_column("references", "url")
    op.drop_column("references", "article_id")
