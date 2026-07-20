from pathlib import Path


def test_catalog_version_management_migration_defines_lifecycle_and_embeddings() -> None:
    migration = Path("alembic/versions/0009_catalog_version_management.py").read_text()

    assert "display_version" in migration
    assert "description" in migration
    assert "status" in migration
    assert "source_catalog_version" in migration
    assert "reproducibility_status" in migration
    assert "catalog_version_example_embeddings" in migration
    assert "intent_catalog_version" in migration
    assert "model_version" in migration
    assert "vector_index_version" in migration
    assert "text_raw_ciphertext" in migration
    assert "embedding_status" in migration
    assert "Vector" in migration or "vector(1024)" in migration

    downgrade = migration.split("def downgrade() -> None:", 1)[1]
    assert 'op.drop_column("intent_catalog_versions", "reproducibility_status")' in downgrade


def test_catalog_version_management_models_are_declared() -> None:
    models = Path("src/intent_routing/db/models.py").read_text()

    assert "display_version" in models
    assert "description" in models
    assert "status" in models
    assert "class CatalogVersionExampleEmbedding" in models
    assert '__tablename__ = "catalog_version_example_embeddings"' in models
