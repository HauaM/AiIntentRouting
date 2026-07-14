"""Add organization directory schema.

Revision ID: 0007_organization_directory
Revises: 0006_governed_workflow_requests
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_organization_directory"
down_revision: str | None = "0006_governed_workflow_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dept_number", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("use_yn", sa.Text(), nullable=False, server_default=sa.text("'Y'")),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False),
        sa.CheckConstraint("use_yn in ('Y', 'N')", name="ck_departments_use_yn"),
        sa.UniqueConstraint("dept_number", name="uq_departments_dept_number"),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_number", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("use_yn", sa.Text(), nullable=False, server_default=sa.text("'Y'")),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.CheckConstraint("use_yn in ('Y', 'N')", name="ck_users_use_yn"),
        sa.UniqueConstraint("user_number", name="uq_users_user_number"),
    )
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.add_column(
        "admin_users",
        sa.Column("organization_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_admin_users_organization_user_id",
        "admin_users",
        ["organization_user_id"],
    )
    op.create_foreign_key(
        "fk_admin_users_organization_user_id_users",
        "admin_users",
        "users",
        ["organization_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_admin_users_organization_user_id_users",
        "admin_users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_admin_users_organization_user_id",
        "admin_users",
        type_="unique",
    )
    op.drop_column("admin_users", "organization_user_id")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_table("users")
    op.drop_table("departments")
