"""Capture the 12 KCAD filtered_table columns we previously dropped.

Round-trip: every row × every column in `suppl_data/filtered_table.csv` is now
persisted in `assay_annotations` (or `references`).

Revision ID: 20260523_0003
Revises: 20260523_0002
Create Date: 2026-05-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260523_0003"
down_revision: str | None = "20260523_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_COLUMNS = (
    ("effect", sa.String(64)),
    ("kc_subgroup2", sa.String(255)),
    ("assay_endpoint2", sa.String(255)),
    ("assay_endpoint3", sa.String(128)),
    ("method2", sa.Text()),
    ("stimulant_activation_agent", sa.String(255)),
    ("target_cell", sa.String(128)),
    ("design_transgenic", sa.String(64)),
    ("mammalian", sa.String(16)),
    ("tissue2", sa.String(64)),
    ("immortalized", sa.String(16)),
    ("cebp_ref_idx", sa.String(32)),
    # Raw verbatim value of the `Secondary KC` cell — covers multi-KC cells
    # like "3  9" or "10  9?" that don't parse to a single FK.
    ("secondary_kc_raw", sa.String(32)),
)


def upgrade() -> None:
    for name, type_ in _NEW_COLUMNS:
        op.add_column("assay_annotations", sa.Column(name, type_))


def downgrade() -> None:
    for name, _ in reversed(_NEW_COLUMNS):
        op.drop_column("assay_annotations", name)
