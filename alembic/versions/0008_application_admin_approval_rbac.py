"""Add application admin approval RBAC.

Revision ID: 0008_application_admin_approval_rbac
Revises: 0007_organization_directory
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_application_admin_approval_rbac"
down_revision: str | None = "0007_organization_directory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.alter_column("alembic_version", "version_num", type_=sa.Text())
    bind = op.get_bind()
    system_admin_count = bind.execute(
        sa.text("select count(*) from admin_user_roles where role = 'system_admin'")
    ).scalar_one()
    if system_admin_count > 1:
        raise RuntimeError(
            "Cannot add single-system-admin constraint while multiple system_admin "
            "rows exist. Resolve duplicates before migration."
        )

    op.drop_constraint(
        "ck_admin_user_roles_role",
        "admin_user_roles",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_user_roles_role",
        "admin_user_roles",
        "role in ('system_admin', 'application_admin')",
    )
    op.create_index(
        "uq_admin_user_roles_single_system_admin",
        "admin_user_roles",
        ["role"],
        unique=True,
        postgresql_where=sa.text("role = 'system_admin'"),
    )
    op.add_column(
        "admin_users",
        sa.Column(
            "admin_access_reason",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'legacy account'"),
        ),
    )
    op.create_table(
        "admin_access_requests",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_number", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("email_normalized", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("access_reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("requested_at", TIMESTAMPTZ, nullable=False),
        sa.Column("decided_at", TIMESTAMPTZ, nullable=True),
        sa.Column("decided_by", sa.Text(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_admin_user_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["created_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_admin_user_id"], ["admin_users.user_id"]),
        sa.CheckConstraint(
            "status in ('pending', 'approved', 'rejected')",
            name="ck_admin_access_requests_status",
        ),
    )
    op.create_unique_constraint(
        "uq_admin_access_requests_pending_email",
        "admin_access_requests",
        ["email_normalized", "status"],
    )
    op.create_index(
        "ix_admin_access_requests_status_requested_at",
        "admin_access_requests",
        ["status", "requested_at"],
    )
    op.alter_column("admin_users", "admin_access_reason", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_admin_access_requests_status_requested_at",
        table_name="admin_access_requests",
    )
    op.drop_constraint(
        "uq_admin_access_requests_pending_email",
        "admin_access_requests",
        type_="unique",
    )
    op.drop_table("admin_access_requests")
    op.drop_column("admin_users", "admin_access_reason")
    op.drop_index(
        "uq_admin_user_roles_single_system_admin",
        table_name="admin_user_roles",
    )
    op.drop_constraint(
        "ck_admin_user_roles_role",
        "admin_user_roles",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_user_roles_role",
        "admin_user_roles",
        "role in ('system_admin')",
    )
