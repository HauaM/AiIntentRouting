from sqlalchemy import text
from sqlalchemy.orm import Session


def test_pgvector_extension_and_core_tables_exist(db_session: Session) -> None:
    tables = {
        row[0]
        for row in db_session.execute(
            text(
                "select table_name from information_schema.tables "
                "where table_schema = 'public'"
            )
        )
    }

    assert "services" in tables
    assert "api_keys" in tables
    assert "intents" in tables
    assert "intent_examples" in tables
    assert "policy_versions" in tables
    assert "intent_catalog_versions" in tables
    assert "test_runs" in tables
    assert "releases" in tables
    assert "runtime_logs" in tables
    assert "audit_logs" in tables

    extension_count = db_session.execute(
        text("select count(*) from pg_extension where extname = 'vector'")
    ).scalar_one()
    assert extension_count == 1


def test_representative_task_text_columns_use_postgresql_text(db_session: Session) -> None:
    column_types = {
        (row.table_name, row.column_name): row.data_type
        for row in db_session.execute(
            text(
                "select table_name, column_name, data_type "
                "from information_schema.columns "
                "where table_schema = 'public' "
                "and (table_name, column_name) in ("
                "('services', 'service_id'), "
                "('intents', 'route_key'), "
                "('runtime_logs', 'trace_id')"
                ")"
            )
        )
    }

    assert column_types == {
        ("services", "service_id"): "text",
        ("intents", "route_key"): "text",
        ("runtime_logs", "trace_id"): "text",
    }


def test_representative_column_defaults_and_nullability(db_session: Session) -> None:
    columns = {
        (row.table_name, row.column_name): {
            "default": row.column_default,
            "nullable": row.is_nullable,
        }
        for row in db_session.execute(
            text(
                "select table_name, column_name, column_default, is_nullable "
                "from information_schema.columns "
                "where table_schema = 'public' "
                "and (table_name, column_name) in ("
                "('services', 'default_threshold_preset'), "
                "('services', 'max_input_tokens'), "
                "('services', 'status'), "
                "('services', 'service_id'), "
                "('runtime_logs', 'request_id'), "
                "('runtime_logs', 'latency_ms')"
                ")"
            )
        )
    }

    assert "'balanced'" in columns[("services", "default_threshold_preset")]["default"]
    assert columns[("services", "max_input_tokens")]["default"] == "256"
    assert "'active'" in columns[("services", "status")]["default"]
    assert columns[("services", "service_id")]["nullable"] == "NO"
    assert columns[("runtime_logs", "request_id")]["nullable"] == "YES"
    assert columns[("runtime_logs", "latency_ms")]["nullable"] == "NO"


def test_raw_text_envelope_metadata_columns_exist(db_session: Session) -> None:
    columns = {
        (row.table_name, row.column_name): row.data_type
        for row in db_session.execute(
            text(
                "select table_name, column_name, data_type "
                "from information_schema.columns "
                "where table_schema = 'public' "
                "and (table_name, column_name) in ("
                "('intent_examples', 'text_raw_ciphertext'), "
                "('intent_examples', 'text_raw_encrypted_dek'), "
                "('intent_examples', 'text_raw_encrypted_dek_iv'), "
                "('intent_examples', 'text_raw_encrypted_dek_auth_tag'), "
                "('intent_examples', 'text_raw_key_id'), "
                "('intent_examples', 'text_raw_iv'), "
                "('intent_examples', 'text_raw_auth_tag'), "
                "('intent_examples', 'text_raw_algorithm'), "
                "('runtime_logs', 'query_raw_ciphertext'), "
                "('runtime_logs', 'query_raw_encrypted_dek'), "
                "('runtime_logs', 'query_raw_encrypted_dek_iv'), "
                "('runtime_logs', 'query_raw_encrypted_dek_auth_tag'), "
                "('runtime_logs', 'query_raw_key_id'), "
                "('runtime_logs', 'query_raw_iv'), "
                "('runtime_logs', 'query_raw_auth_tag'), "
                "('runtime_logs', 'query_raw_algorithm')"
                ")"
            )
        )
    }

    assert columns == {
        ("intent_examples", "text_raw_ciphertext"): "bytea",
        ("intent_examples", "text_raw_encrypted_dek"): "bytea",
        ("intent_examples", "text_raw_encrypted_dek_iv"): "bytea",
        ("intent_examples", "text_raw_encrypted_dek_auth_tag"): "bytea",
        ("intent_examples", "text_raw_key_id"): "text",
        ("intent_examples", "text_raw_iv"): "bytea",
        ("intent_examples", "text_raw_auth_tag"): "bytea",
        ("intent_examples", "text_raw_algorithm"): "text",
        ("runtime_logs", "query_raw_ciphertext"): "bytea",
        ("runtime_logs", "query_raw_encrypted_dek"): "bytea",
        ("runtime_logs", "query_raw_encrypted_dek_iv"): "bytea",
        ("runtime_logs", "query_raw_encrypted_dek_auth_tag"): "bytea",
        ("runtime_logs", "query_raw_key_id"): "text",
        ("runtime_logs", "query_raw_iv"): "bytea",
        ("runtime_logs", "query_raw_auth_tag"): "bytea",
        ("runtime_logs", "query_raw_algorithm"): "text",
    }


def test_representative_foreign_key_and_vector_type_exist(db_session: Session) -> None:
    api_key_fk_exists = db_session.execute(
        text(
            "select exists ("
            "select 1 from information_schema.referential_constraints rc "
            "join information_schema.key_column_usage kcu "
            "on rc.constraint_schema = kcu.constraint_schema "
            "and rc.constraint_name = kcu.constraint_name "
            "join information_schema.constraint_column_usage ccu "
            "on rc.unique_constraint_schema = ccu.constraint_schema "
            "and rc.unique_constraint_name = ccu.constraint_name "
            "where kcu.table_schema = 'public' "
            "and kcu.table_name = 'api_keys' "
            "and kcu.column_name = 'service_id' "
            "and ccu.table_schema = 'public' "
            "and ccu.table_name = 'services' "
            "and ccu.column_name = 'service_id'"
            ")"
        )
    ).scalar_one()
    assert api_key_fk_exists is True

    embedding_type = db_session.execute(
        text(
            "select format_type(a.atttypid, a.atttypmod) "
            "from pg_attribute a "
            "join pg_class c on c.oid = a.attrelid "
            "join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' "
            "and c.relname = 'intent_examples' "
            "and a.attname = 'embedding'"
        )
    ).scalar_one()
    assert embedding_type == "vector(1024)"


def test_no_hnsw_indexes_exist(db_session: Session) -> None:
    hnsw_index_count = db_session.execute(
        text(
            "select count(*) from pg_indexes "
            "where schemaname = 'public' "
            "and indexdef ilike '%USING hnsw%'"
        )
    ).scalar_one()
    assert hnsw_index_count == 0
