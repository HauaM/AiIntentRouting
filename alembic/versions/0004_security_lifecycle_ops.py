"""Add security lifecycle operational schema.

Revision ID: 0004_security_lifecycle_ops
Revises: 0003_runtime_log_idx
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_security_lifecycle_ops"
down_revision: str | None = "0003_runtime_log_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "raw_text_rewrap_runs",
        sa.Column("rewrap_run_id", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=True),
        sa.Column("target_key_id", sa.Text(), nullable=False),
        sa.Column("source_key_ids", postgresql.JSONB(), nullable=False),
        sa.Column("included_tables", postgresql.JSONB(), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("scanned_count", sa.Integer(), nullable=False),
        sa.Column("rewrapped_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("report", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", TIMESTAMPTZ, nullable=False),
        sa.Column("completed_at", TIMESTAMPTZ, nullable=True),
    )
    op.add_column(
        "runtime_logs",
        sa.Column("raw_query_deleted_at", TIMESTAMPTZ, nullable=True),
    )
    op.add_column(
        "runtime_logs",
        sa.Column("raw_query_deleted_by", sa.Text(), nullable=True),
    )
    op.add_column(
        "runtime_logs",
        sa.Column("raw_query_delete_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_raw_text_rewrap_runs_service_started",
        "raw_text_rewrap_runs",
        ["service_id", sa.text("started_at DESC")],
    )
    op.create_index(
        "ix_audit_logs_service_created_at",
        "audit_logs",
        ["service_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_service_created_at", table_name="audit_logs")
    op.drop_index(
        "ix_raw_text_rewrap_runs_service_started",
        table_name="raw_text_rewrap_runs",
    )
    op.drop_column("runtime_logs", "raw_query_delete_reason")
    op.drop_column("runtime_logs", "raw_query_deleted_by")
    op.drop_column("runtime_logs", "raw_query_deleted_at")
    op.drop_table("raw_text_rewrap_runs")
