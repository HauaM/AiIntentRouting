"""catalog version management

Revision ID: 0009_catalog_version_mgmt
Revises: 0008_application_admin_approval_rbac
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

from alembic import op

revision: str = "0009_catalog_version_mgmt"
down_revision: str | None = "0008_application_admin_approval_rbac"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("intent_catalog_versions", sa.Column("display_version", sa.Text(), nullable=True))
    op.add_column("intent_catalog_versions", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "intent_catalog_versions",
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
    )
    op.add_column(
        "intent_catalog_versions",
        sa.Column("reproducibility_status", sa.Text(), nullable=False, server_default="complete"),
    )
    op.add_column(
        "intent_catalog_versions", sa.Column("source_catalog_version", sa.Text(), nullable=True)
    )
    op.add_column(
        "intent_catalog_versions",
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "intent_catalog_versions",
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_intent_catalog_versions_service_display",
        "intent_catalog_versions",
        ["service_id", "display_version"],
    )
    op.create_check_constraint(
        "ck_intent_catalog_versions_status",
        "intent_catalog_versions",
        "status in ('active', 'inactive')",
    )

    op.create_table(
        "catalog_version_example_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("intent_catalog_version", sa.Text(), nullable=False),
        sa.Column("service_id", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("vector_index_version", sa.Text(), nullable=False),
        sa.Column("intent_id", sa.Text(), nullable=False),
        sa.Column("example_id", sa.Uuid(), nullable=True),
        sa.Column("example_type", sa.Text(), nullable=False),
        sa.Column("text_raw_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_encrypted_dek", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_encrypted_dek_iv", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_encrypted_dek_auth_tag", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_key_id", sa.Text(), nullable=False),
        sa.Column("text_raw_iv", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_auth_tag", sa.LargeBinary(), nullable=False),
        sa.Column("text_raw_algorithm", sa.Text(), nullable=False),
        sa.Column("text_masked", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column("embedding_status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["intent_catalog_version"],
            ["intent_catalog_versions.intent_catalog_version"],
        ),
        sa.ForeignKeyConstraint(
            ["vector_index_version"],
            ["vector_index_versions.vector_index_version"],
        ),
        sa.CheckConstraint(
            "example_type in ('positive', 'negative')",
            name="ck_catalog_version_example_embeddings_type",
        ),
        sa.CheckConstraint(
            "embedding_status in ('active', 'inactive')",
            name="ck_catalog_version_example_embeddings_status",
        ),
    )
    op.create_index(
        "ix_catalog_version_example_embeddings_version_status",
        "catalog_version_example_embeddings",
        ["intent_catalog_version", "model_version", "embedding_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalog_version_example_embeddings_version_status",
        table_name="catalog_version_example_embeddings",
    )
    op.drop_table("catalog_version_example_embeddings")
    op.drop_constraint(
        "ck_intent_catalog_versions_status", "intent_catalog_versions", type_="check"
    )
    op.drop_constraint(
        "uq_intent_catalog_versions_service_display", "intent_catalog_versions", type_="unique"
    )
    op.drop_column("intent_catalog_versions", "deactivated_at")
    op.drop_column("intent_catalog_versions", "activated_at")
    op.drop_column("intent_catalog_versions", "source_catalog_version")
    op.drop_column("intent_catalog_versions", "reproducibility_status")
    op.drop_column("intent_catalog_versions", "status")
    op.drop_column("intent_catalog_versions", "description")
    op.drop_column("intent_catalog_versions", "display_version")
