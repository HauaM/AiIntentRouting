from pathlib import Path


def test_api_key_optional_expiry_migration_makes_downgrade_deterministic() -> None:
    migration = Path("alembic/versions/0011_api_key_optional_expiry.py").read_text()

    assert 'down_revision: str | None = "0010_test_run_vector_metadata"' in migration
    assert 'op.alter_column("api_keys", "expires_at", nullable=True)' in migration

    downgrade = migration.split("def downgrade() -> None:", 1)[1]
    assert "UPDATE api_keys" in downgrade
    assert "WHERE expires_at IS NULL" in downgrade
    assert "9999-12-31 23:59:59+00:00" in downgrade
    assert 'op.alter_column("api_keys", "expires_at", nullable=False)' in downgrade
