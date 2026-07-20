"""test run vector metadata

Revision ID: 0010_test_run_vector_metadata
Revises: 0009_catalog_version_mgmt
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0010_test_run_vector_metadata"
down_revision: str | None = "0009_catalog_version_mgmt"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("test_runs", sa.Column("model_version", sa.Text(), nullable=True))
    op.add_column("test_runs", sa.Column("vector_index_version", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("test_runs", "vector_index_version")
    op.drop_column("test_runs", "model_version")
