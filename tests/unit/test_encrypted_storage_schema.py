from pathlib import Path

from intent_routing.db import models


def test_intent_examples_store_complete_envelope_metadata() -> None:
    columns = set(models.IntentExample.__table__.columns.keys())

    assert {
        "text_raw_ciphertext",
        "text_raw_encrypted_dek",
        "text_raw_encrypted_dek_iv",
        "text_raw_encrypted_dek_auth_tag",
        "text_raw_key_id",
        "text_raw_iv",
        "text_raw_auth_tag",
        "text_raw_algorithm",
    }.issubset(columns)


def test_runtime_logs_store_complete_query_envelope_metadata() -> None:
    columns = set(models.RuntimeLog.__table__.columns.keys())

    assert {
        "query_raw_ciphertext",
        "query_raw_encrypted_dek",
        "query_raw_encrypted_dek_iv",
        "query_raw_encrypted_dek_auth_tag",
        "query_raw_key_id",
        "query_raw_iv",
        "query_raw_auth_tag",
        "query_raw_algorithm",
    }.issubset(columns)


def test_initial_migration_creates_complete_envelope_metadata_columns() -> None:
    migration = Path("alembic/versions/0001_initial_intent_routing.py").read_text()

    assert (
        'sa.Column("text_raw_encrypted_dek_iv", sa.LargeBinary(), nullable=False)'
        in migration
    )
    assert (
        'sa.Column("text_raw_encrypted_dek_auth_tag", sa.LargeBinary(), nullable=False)'
        in migration
    )
    assert 'sa.Column("query_raw_encrypted_dek_iv", sa.LargeBinary(), nullable=True)' in migration
    assert (
        'sa.Column("query_raw_encrypted_dek_auth_tag", '
        "sa.LargeBinary(), nullable=True)"
        in migration
    )
