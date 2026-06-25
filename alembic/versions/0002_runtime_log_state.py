"""Add runtime log decision state and test run id.

Revision ID: 0002_runtime_log_state
Revises: 0001_initial_intent_routing
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_runtime_log_state"
down_revision: str | None = "0001_initial_intent_routing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB()


def upgrade() -> None:
    op.add_column("runtime_logs", sa.Column("test_run_id", sa.Text(), nullable=True))
    op.add_column("runtime_logs", sa.Column("decision_state", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("runtime_logs", "decision_state")
    op.drop_column("runtime_logs", "test_run_id")
