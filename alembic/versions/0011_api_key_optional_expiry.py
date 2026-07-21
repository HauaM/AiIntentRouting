"""allow api keys without expiry

Revision ID: 0011_api_key_optional_expiry
Revises: 0010_test_run_vector_metadata
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0011_api_key_optional_expiry"
down_revision: str | None = "0010_test_run_vector_metadata"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column("api_keys", "expires_at", nullable=True)


def downgrade() -> None:
    # The pre-0011 schema requires expires_at to be present, so downgrade
    # normalizes no-expiry keys to a far-future UTC sentinel before restoring
    # the old NOT NULL contract.
    op.execute(
        sa.text(
            """
            UPDATE api_keys
            SET expires_at = TIMESTAMPTZ '9999-12-31 23:59:59+00:00'
            WHERE expires_at IS NULL
            """
        )
    )
    op.alter_column("api_keys", "expires_at", nullable=False)
