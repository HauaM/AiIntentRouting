"""Add runtime log service and creation time index.

Revision ID: 0003_runtime_log_idx
Revises: 0002_runtime_log_state
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_runtime_log_idx"
down_revision: str | None = "0002_runtime_log_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_runtime_logs_service_created_at_trace",
        "runtime_logs",
        [
            "service_id",
            sa.text("created_at DESC"),
            "trace_id",
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_logs_service_created_at_trace",
        table_name="runtime_logs",
    )
