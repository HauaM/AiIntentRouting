"""release owned environment

Revision ID: 0012_release_owned_environment
Revises: 0011_api_key_optional_expiry
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0012_release_owned_environment"
down_revision: str | None = "0011_api_key_optional_expiry"
branch_labels: str | None = None
depends_on: str | None = None


def _raise_if_duplicate_release_test_runs() -> None:
    duplicate_rows = op.get_bind().execute(
        sa.text(
            """
            SELECT service_id, environment, test_run_id, COUNT(*) AS duplicate_count
            FROM releases
            GROUP BY service_id, environment, test_run_id
            HAVING COUNT(*) > 1
            ORDER BY service_id, environment, test_run_id
            """
        )
    ).mappings().all()
    if not duplicate_rows:
        return

    details = "; ".join(
        f"service_id={row['service_id']}, environment={row['environment']}, "
        f"test_run_id={row['test_run_id']}, count={row['duplicate_count']}"
        for row in duplicate_rows
    )
    raise RuntimeError(
        "Duplicate release rows block upgrade to 0012_release_owned_environment: "
        f"{details}. Clean up duplicate releases, then delete or re-register "
        "the affected services/releases before retrying the migration."
    )


def upgrade() -> None:
    op.drop_column("services", "default_threshold_preset")
    op.drop_column("services", "environment")
    op.add_column("runtime_logs", sa.Column("environment", sa.Text(), nullable=True))
    op.create_index(
        "ix_runtime_logs_service_environment_created",
        "runtime_logs",
        ["service_id", "environment", "created_at"],
    )
    _raise_if_duplicate_release_test_runs()
    op.create_unique_constraint(
        "uq_releases_service_environment_test_run",
        "releases",
        ["service_id", "environment", "test_run_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_releases_service_environment_test_run",
        "releases",
        type_="unique",
    )
    op.drop_index("ix_runtime_logs_service_environment_created", table_name="runtime_logs")
    op.drop_column("runtime_logs", "environment")
    op.add_column(
        "services",
        sa.Column("environment", sa.Text(), nullable=False, server_default="dev"),
    )
    op.add_column(
        "services",
        sa.Column(
            "default_threshold_preset",
            sa.Text(),
            nullable=False,
            server_default="balanced",
        ),
    )
