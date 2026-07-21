"""store encrypted api key secrets

Revision ID: 0013_api_key_encrypted_secret
Revises: 0012_release_owned_environment
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0013_api_key_encrypted_secret"
down_revision: str | None = "0012_release_owned_environment"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("secret_ciphertext", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "api_keys",
        sa.Column("secret_encrypted_dek", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "api_keys",
        sa.Column("secret_encrypted_dek_iv", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "api_keys",
        sa.Column("secret_encrypted_dek_auth_tag", sa.LargeBinary(), nullable=True),
    )
    op.add_column("api_keys", sa.Column("secret_key_id", sa.Text(), nullable=True))
    op.add_column("api_keys", sa.Column("secret_iv", sa.LargeBinary(), nullable=True))
    op.add_column(
        "api_keys",
        sa.Column("secret_auth_tag", sa.LargeBinary(), nullable=True),
    )
    op.add_column("api_keys", sa.Column("secret_algorithm", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("api_keys", "secret_algorithm")
    op.drop_column("api_keys", "secret_auth_tag")
    op.drop_column("api_keys", "secret_iv")
    op.drop_column("api_keys", "secret_key_id")
    op.drop_column("api_keys", "secret_encrypted_dek_auth_tag")
    op.drop_column("api_keys", "secret_encrypted_dek_iv")
    op.drop_column("api_keys", "secret_encrypted_dek")
    op.drop_column("api_keys", "secret_ciphertext")
