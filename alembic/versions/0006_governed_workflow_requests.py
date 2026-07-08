"""Add governed workflow request storage.

Revision ID: 0006_governed_workflow_requests
Revises: 0005_account_auth_service_rbac
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_governed_workflow_requests"
down_revision: str | None = "0005_account_auth_service_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "governed_action_requests",
        sa.Column("request_id", sa.Text(), primary_key=True),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("requested_by", sa.Text(), nullable=False),
        sa.Column("requested_at", TIMESTAMPTZ, nullable=False),
        sa.Column("decided_by", sa.Text(), nullable=True),
        sa.Column("decided_at", TIMESTAMPTZ, nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
        sa.CheckConstraint(
            "resource_type in "
            "('intent', 'example', 'release', 'runtime_log', 'raw_query', 'export')",
            name="ck_governed_action_requests_resource_type",
        ),
        sa.CheckConstraint(
            "action in "
            "('request', 'approve', 'reject', 'activate', 'rollback', 'decrypt', "
            "'export')",
            name="ck_governed_action_requests_action",
        ),
        sa.CheckConstraint(
            "status in "
            "('pending', 'approved', 'rejected', 'activated', 'rolled_back', "
            "'token_issued', 'viewed', 'expired', 'completed')",
            name="ck_governed_action_requests_status",
        ),
    )
    op.create_index(
        "ix_governed_action_requests_service_id",
        "governed_action_requests",
        ["service_id"],
    )
    op.create_index(
        "ix_governed_action_requests_status",
        "governed_action_requests",
        ["status"],
    )
    op.create_index(
        "ix_governed_action_requests_resource_type",
        "governed_action_requests",
        ["resource_type"],
    )

    op.create_table(
        "raw_query_view_tokens",
        sa.Column("token_id", sa.Text(), primary_key=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", TIMESTAMPTZ, nullable=False),
        sa.Column("issued_by", sa.Text(), nullable=False),
        sa.Column("issued_at", TIMESTAMPTZ, nullable=False),
        sa.Column("viewed_at", TIMESTAMPTZ, nullable=True),
        sa.Column("expired_at", TIMESTAMPTZ, nullable=True),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["governed_action_requests.request_id"],
        ),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_raw_query_view_tokens_service_id",
        "raw_query_view_tokens",
        ["service_id"],
    )
    op.create_index(
        "ix_raw_query_view_tokens_expires_at",
        "raw_query_view_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_raw_query_view_tokens_expires_at",
        table_name="raw_query_view_tokens",
    )
    op.drop_index(
        "ix_raw_query_view_tokens_service_id",
        table_name="raw_query_view_tokens",
    )
    op.drop_table("raw_query_view_tokens")
    op.drop_index(
        "ix_governed_action_requests_resource_type",
        table_name="governed_action_requests",
    )
    op.drop_index(
        "ix_governed_action_requests_status",
        table_name="governed_action_requests",
    )
    op.drop_index(
        "ix_governed_action_requests_service_id",
        table_name="governed_action_requests",
    )
    op.drop_table("governed_action_requests")
