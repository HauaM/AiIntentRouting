"""Add account auth and service-scoped RBAC schema.

Revision ID: 0005_account_auth_service_rbac
Revises: 0004_security_lifecycle_ops
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_account_auth_service_rbac"
down_revision: str | None = "0004_security_lifecycle_ops"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("user_id", sa.Text(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("email_normalized", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False),
        sa.Column("last_login_at", TIMESTAMPTZ, nullable=True),
        sa.CheckConstraint(
            "status in ('active', 'disabled')",
            name="ck_admin_users_status",
        ),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("email_normalized"),
    )
    op.create_table(
        "admin_sessions",
        sa.Column("session_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.Column("expires_at", TIMESTAMPTZ, nullable=False),
        sa.Column("revoked_at", TIMESTAMPTZ, nullable=True),
        sa.Column("last_seen_at", TIMESTAMPTZ, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.user_id"]),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "admin_user_roles",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("assigned_by", sa.Text(), nullable=False),
        sa.Column("assigned_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.user_id"]),
        sa.CheckConstraint(
            "role in ('system_admin')",
            name="ck_admin_user_roles_role",
        ),
        sa.PrimaryKeyConstraint("user_id", "role"),
    )
    op.create_table(
        "user_service_roles",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("assigned_by", sa.Text(), nullable=False),
        sa.Column("assigned_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.user_id"]),
        sa.ForeignKeyConstraint(["service_id"], ["services.service_id"]),
        sa.CheckConstraint(
            "role in ('service_owner', 'service_developer', 'service_operator', 'auditor')",
            name="ck_user_service_roles_role",
        ),
        sa.PrimaryKeyConstraint("user_id", "service_id", "role"),
    )
    op.create_index(
        "ix_user_service_roles_user_id",
        "user_service_roles",
        ["user_id"],
    )
    op.create_index(
        "ix_user_service_roles_service_id",
        "user_service_roles",
        ["service_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_service_roles_service_id", table_name="user_service_roles")
    op.drop_index("ix_user_service_roles_user_id", table_name="user_service_roles")
    op.drop_table("user_service_roles")
    op.drop_table("admin_user_roles")
    op.drop_table("admin_sessions")
    op.drop_table("admin_users")
