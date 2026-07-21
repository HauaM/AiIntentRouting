from __future__ import annotations

import base64
import json
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.api.dependencies import get_api_key_lookup
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from intent_routing.security.admin_sessions import (
    ADMIN_SESSION_COOKIE_NAME,
    hash_admin_session_token,
)
from intent_routing.security.api_keys import ApiKeyRecord

QUERY_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dify_request.json"
SPRINT_ZERO_SERVICE_ID = "it-helpdesk"


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
    assert "raw_text_rewrap_runs" in tables

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
                "('services', 'max_input_tokens'), "
                "('services', 'status'), "
                "('services', 'service_id'), "
                "('runtime_logs', 'request_id'), "
                "('runtime_logs', 'latency_ms')"
                ")"
            )
        )
    }

    assert columns[("services", "max_input_tokens")]["default"] == "256"
    assert "'active'" in columns[("services", "status")]["default"]
    assert columns[("services", "service_id")]["nullable"] == "NO"
    assert columns[("runtime_logs", "request_id")]["nullable"] == "YES"
    assert columns[("runtime_logs", "latency_ms")]["nullable"] == "NO"


def test_service_schema_drops_environment_and_default_preset(
    db_session: Session,
) -> None:
    columns = {
        row.column_name
        for row in db_session.execute(
            text(
                "select column_name from information_schema.columns "
                "where table_schema = 'public' and table_name = 'services'"
            )
        )
    }

    assert "service_id" in columns
    assert "display_name" in columns
    assert "max_input_tokens" in columns
    assert "environment" not in columns
    assert "default_threshold_preset" not in columns


def test_runtime_logs_include_environment_column(db_session: Session) -> None:
    columns = {
        row.column_name: row.data_type
        for row in db_session.execute(
            text(
                "select column_name, data_type from information_schema.columns "
                "where table_schema = 'public' and table_name = 'runtime_logs'"
            )
        )
    }

    assert columns["environment"] == "text"


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


def test_schema_contains_expected_tables_and_columns(db_session: Session) -> None:
    columns = {
        (row.table_name, row.column_name): row.data_type
        for row in db_session.execute(
            text(
                "select table_name, column_name, data_type "
                "from information_schema.columns "
                "where table_schema = 'public' "
                "and (table_name, column_name) in ("
                "('api_keys', 'secret_ciphertext'), "
                "('api_keys', 'secret_encrypted_dek'), "
                "('api_keys', 'secret_encrypted_dek_iv'), "
                "('api_keys', 'secret_encrypted_dek_auth_tag'), "
                "('api_keys', 'secret_key_id'), "
                "('api_keys', 'secret_iv'), "
                "('api_keys', 'secret_auth_tag'), "
                "('api_keys', 'secret_algorithm')"
                ")"
            )
        )
    }

    assert columns == {
        ("api_keys", "secret_ciphertext"): "bytea",
        ("api_keys", "secret_encrypted_dek"): "bytea",
        ("api_keys", "secret_encrypted_dek_iv"): "bytea",
        ("api_keys", "secret_encrypted_dek_auth_tag"): "bytea",
        ("api_keys", "secret_key_id"): "text",
        ("api_keys", "secret_iv"): "bytea",
        ("api_keys", "secret_auth_tag"): "bytea",
        ("api_keys", "secret_algorithm"): "text",
    }


def test_security_lifecycle_schema_columns_and_indexes_exist(
    db_session: Session,
) -> None:
    columns = {
        (row.table_name, row.column_name): {
            "data_type": row.data_type,
            "nullable": row.is_nullable,
        }
        for row in db_session.execute(
            text(
                "select table_name, column_name, data_type, is_nullable "
                "from information_schema.columns "
                "where table_schema = 'public' "
                "and (table_name, column_name) in ("
                "('raw_text_rewrap_runs', 'rewrap_run_id'), "
                "('raw_text_rewrap_runs', 'service_id'), "
                "('raw_text_rewrap_runs', 'target_key_id'), "
                "('raw_text_rewrap_runs', 'source_key_ids'), "
                "('raw_text_rewrap_runs', 'included_tables'), "
                "('raw_text_rewrap_runs', 'dry_run'), "
                "('raw_text_rewrap_runs', 'approval_id'), "
                "('raw_text_rewrap_runs', 'actor_id'), "
                "('raw_text_rewrap_runs', 'status'), "
                "('raw_text_rewrap_runs', 'scanned_count'), "
                "('raw_text_rewrap_runs', 'rewrapped_count'), "
                "('raw_text_rewrap_runs', 'skipped_count'), "
                "('raw_text_rewrap_runs', 'failed_count'), "
                "('raw_text_rewrap_runs', 'report'), "
                "('raw_text_rewrap_runs', 'started_at'), "
                "('raw_text_rewrap_runs', 'completed_at'), "
                "('runtime_logs', 'raw_query_deleted_at'), "
                "('runtime_logs', 'raw_query_deleted_by'), "
                "('runtime_logs', 'raw_query_delete_reason')"
                ")"
            )
        )
    }

    assert columns == {
        ("raw_text_rewrap_runs", "rewrap_run_id"): {
            "data_type": "text",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "service_id"): {
            "data_type": "text",
            "nullable": "YES",
        },
        ("raw_text_rewrap_runs", "target_key_id"): {
            "data_type": "text",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "source_key_ids"): {
            "data_type": "jsonb",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "included_tables"): {
            "data_type": "jsonb",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "dry_run"): {
            "data_type": "boolean",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "approval_id"): {
            "data_type": "text",
            "nullable": "YES",
        },
        ("raw_text_rewrap_runs", "actor_id"): {
            "data_type": "text",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "status"): {
            "data_type": "text",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "scanned_count"): {
            "data_type": "integer",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "rewrapped_count"): {
            "data_type": "integer",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "skipped_count"): {
            "data_type": "integer",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "failed_count"): {
            "data_type": "integer",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "report"): {
            "data_type": "jsonb",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "started_at"): {
            "data_type": "timestamp with time zone",
            "nullable": "NO",
        },
        ("raw_text_rewrap_runs", "completed_at"): {
            "data_type": "timestamp with time zone",
            "nullable": "YES",
        },
        ("runtime_logs", "raw_query_deleted_at"): {
            "data_type": "timestamp with time zone",
            "nullable": "YES",
        },
        ("runtime_logs", "raw_query_deleted_by"): {
            "data_type": "text",
            "nullable": "YES",
        },
        ("runtime_logs", "raw_query_delete_reason"): {
            "data_type": "text",
            "nullable": "YES",
        },
    }

    index_definitions = {
        row.indexname: row.indexdef
        for row in db_session.execute(
            text(
                """
                select indexname, indexdef
                from pg_indexes
                where schemaname = current_schema()
                  and indexname in (
                    'ix_raw_text_rewrap_runs_service_started',
                    'ix_audit_logs_service_created_at'
                  )
                """
            )
        )
    }

    assert "service_id" in index_definitions[
        "ix_raw_text_rewrap_runs_service_started"
    ]
    assert "started_at DESC" in index_definitions[
        "ix_raw_text_rewrap_runs_service_started"
    ]
    assert "service_id" in index_definitions["ix_audit_logs_service_created_at"]
    assert "created_at DESC" in index_definitions["ix_audit_logs_service_created_at"]


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


def test_catalog_snapshot_normalizes_current_editable_intents_and_examples(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    clear_embedding_provider_cache()
    client = _client(db_session)
    service_id = f"svc-release-{uuid4().hex}"
    _create_service(client, service_id)
    active_intent = _create_intent(
        client,
        service_id,
        intent_id="intent-active",
        route_key="it.release.active",
        include_keywords=["release", "active"],
        exclude_keywords=["billing"],
    )
    _patch_intent(client, service_id, "intent-active", {"status": "active"})
    _create_intent(
        client,
        service_id,
        intent_id="intent-draft",
        route_key="it.release.draft",
    )
    approved_example = _create_example(client, service_id, "intent-active", "release me")
    _approve_example(client, service_id, approved_example["example_id"])
    unapproved_example = _create_example(
        client,
        service_id,
        "intent-active",
        "do not snapshot",
    )

    response = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(),
        json={"description": "Release flow catalog version"},
    )

    body = response.json()
    assert response.status_code == 201
    assert body["intent_catalog_version"].startswith(f"cat-{service_id}-")
    assert body["service_id"] == service_id
    assert body["created_by"] == "admin-user"
    snapshot_intents = body["snapshot"]["intents"]
    assert [intent["intent_id"] for intent in snapshot_intents] == [
        active_intent["intent_id"],
        "intent-draft",
    ]
    assert all(intent["status"] == "active" for intent in snapshot_intents)
    snapshot_examples = [
        example
        for intent in snapshot_intents
        for example in intent["examples"]
    ]
    assert {example["example_id"] for example in snapshot_examples} == {
        approved_example["example_id"],
        unapproved_example["example_id"],
    }
    assert all(example["approved"] is True for example in snapshot_examples)
    persisted = db_session.get(models.IntentCatalogVersion, body["intent_catalog_version"])
    assert persisted is not None
    assert persisted.snapshot == body["snapshot"]
    audit_log = _audit_log(db_session, "catalog_version.created", body["intent_catalog_version"])
    assert audit_log is not None
    assert audit_log.after_state == body


def test_policy_version_is_immutable_after_creation(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-release-{uuid4().hex}"
    policy_version = _create_service_and_policy(client, service_id)
    before = _policy_state(db_session, policy_version)

    response = client.patch(
        f"/admin/v1/services/{service_id}/policy-versions/{policy_version}",
        headers=_admin_headers(),
        json={"clarify_margin": 0.99},
    )

    assert response.status_code in {404, 405}
    assert _policy_state(db_session, policy_version) == before


def test_intent_catalog_version_is_immutable_after_creation(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    clear_embedding_provider_cache()
    client = _client(db_session)
    service_id = f"svc-release-{uuid4().hex}"
    _create_service(client, service_id)
    _create_active_intent_with_approved_example(client, service_id)
    catalog_version = _create_catalog_version(client, service_id)
    before = _catalog_state(db_session, catalog_version)

    response = client.patch(
        f"/admin/v1/services/{service_id}/catalog-versions/{catalog_version}",
        headers=_admin_headers(),
        json={"snapshot": {"intents": []}},
    )

    assert response.status_code in {404, 405}
    assert _catalog_state(db_session, catalog_version) == before


def test_release_creation_rejects_missing_test_run(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=f"tr-missing-{uuid4().hex}",
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_release_creation_rejects_failed_gate(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=False,
        risk_pass_rate=Decimal("1.0"),
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
    )

    assert response.status_code == 400
    assert "gate" in response.json()["error"]["message"].casefold()


def test_release_creation_rejects_non_perfect_risk_pass_rate(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("0.99"),
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
    )

    assert response.status_code == 400
    assert "risk" in response.json()["error"]["message"].casefold()


def test_release_creation_succeeds_when_gate_and_versions_match(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    monkeypatch.setattr(
        "intent_routing.api.admin.get_embedding_provider",
        lambda: _ReleaseEmbeddingProvider("emb-fake-v1"),
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
    )

    body = response.json()
    assert response.status_code == 201
    released_day = _date_segment(body["released_at"])
    assert body["release_version"] == f"rel-{service_id}-{released_day}-001"
    assert body["service_id"] == service_id
    assert body["environment"] == "prod"
    assert body["policy_version"] == policy_version
    assert body["intent_catalog_version"] == catalog_version
    assert body["model_version"] == "emb-fake-v1"
    assert body["vector_index_version"] == f"vec-{catalog_version}-emb-fake-v1-001"
    assert body["test_run_id"] == test_run_id
    assert body["pass_rate"] == pytest.approx(1.0)
    assert body["risk_pass_rate"] == pytest.approx(1.0)
    assert body["active"] is False
    assert body["released_by"] == "admin-user"
    assert body["rollback_target"] is None
    assert db_session.get(models.VectorIndexVersion, body["vector_index_version"]) is not None
    audit_log = _audit_log(db_session, "release.created", body["release_version"])
    assert audit_log is not None
    release_after_state = audit_log.after_state
    assert release_after_state is not None
    assert release_after_state["release_version"] == body["release_version"]
    assert release_after_state["policy_version"] == policy_version
    assert release_after_state["intent_catalog_version"] == catalog_version
    assert release_after_state["test_run_id"] == test_run_id
    assert release_after_state["pass_rate"] == pytest.approx(1.0)
    assert release_after_state["risk_pass_rate"] == pytest.approx(1.0)
    assert release_after_state["rollback_target"] is None

    next_test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )
    next_response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=next_test_run_id,
    )

    next_body = next_response.json()
    assert next_response.status_code == 201
    next_released_day = _date_segment(next_body["released_at"])
    assert next_released_day == released_day
    assert next_body["release_version"] == f"rel-{service_id}-{released_day}-002"
    assert next_body["model_version"] == "emb-fake-v1"
    assert next_body["vector_index_version"] == body["vector_index_version"]


def test_one_passed_test_run_can_create_releases_per_environment_once(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )

    for environment in ("dev", "qa", "prod"):
        response = _create_release_response(
            client,
            service_id,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            test_run_id=test_run_id,
            environment=environment,
        )
        assert response.status_code == 201
        assert response.json()["environment"] == environment

    duplicate = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
        environment="dev",
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["error"]["message"] == (
        "Test run already has a release for this environment."
    )


def test_release_creation_rejects_when_provider_model_has_no_ready_catalog_index(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    monkeypatch.setattr(
        "intent_routing.api.admin.get_embedding_provider",
        lambda: _ReleaseEmbeddingProvider("emb-fake/v2"),
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
    )

    assert response.status_code == 400
    assert "ready vector index" in response.json()["error"]["message"].casefold()


def test_release_creation_rejects_test_run_vector_metadata_mismatch(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    monkeypatch.setattr(
        "intent_routing.api.admin.get_embedding_provider",
        lambda: _ReleaseEmbeddingProvider("emb-fake-v1"),
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
        model_version="emb-fake-v1",
        vector_index_version=f"vec-{catalog_version}-emb-fake-v1-stale",
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
    )

    assert response.status_code == 400
    assert "test run" in response.json()["error"]["message"].casefold()
    assert "vector index" in response.json()["error"]["message"].casefold()


def test_release_creation_acquires_sequence_locks_in_deterministic_order(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    monkeypatch.setattr(
        "intent_routing.api.admin.get_embedding_provider",
        lambda: _ReleaseEmbeddingProvider("emb-fake-v1"),
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )
    acquired_lock_keys: list[str] = []

    def capture_lock(
        self: IntentRoutingRepository,
        lock_key: str,
    ) -> None:
        del self
        acquired_lock_keys.append(lock_key)

    monkeypatch.setattr(
        IntentRoutingRepository,
        "acquire_advisory_xact_lock",
        capture_lock,
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
    )

    body = response.json()
    released_day = _date_segment(body["released_at"])
    expected_lock_keys = sorted(
        [
            f"catalog-version:{service_id}",
            f"release-version:{service_id}:{released_day}",
            f"vector-index-version:{catalog_version}:emb-fake-v1",
        ]
    )
    assert response.status_code == 201
    assert acquired_lock_keys == expected_lock_keys


def test_release_creation_rejects_inactive_catalog_version(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )
    deactivated = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions/{catalog_version}:deactivate",
        headers=_admin_headers(),
    )
    assert deactivated.status_code == 200

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
    )

    assert response.status_code == 400
    assert "inactive" in response.text


def test_release_creation_strips_environment_whitespace(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
        environment=" prod ",
    )

    assert response.status_code == 201
    assert response.json()["environment"] == "prod"


def test_release_creation_rejects_unsupported_environment(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )

    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=test_run_id,
        environment="staging",
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["error"]["message"] == "Release environment must be one of dev, qa, prod."


def test_release_activation_deactivates_previous_active_release(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    first = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )
    second = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )

    first_activation = client.post(
        f"/admin/v1/services/{service_id}/releases/{first}:activate",
        headers=_admin_headers(),
    )
    second_activation = client.post(
        f"/admin/v1/services/{service_id}/releases/{second}:activate",
        headers=_admin_headers(),
    )

    assert first_activation.status_code == 200
    assert second_activation.status_code == 200
    db_session.expire_all()
    first_release = db_session.get(models.Release, first)
    second_release = db_session.get(models.Release, second)
    assert first_release is not None
    assert second_release is not None
    assert first_release.active is False
    assert second_release.active is True
    active_response = client.get(
        f"/admin/v1/services/{service_id}/releases/active?environment=prod",
        headers=_admin_headers(),
    )
    assert active_response.status_code == 200
    assert active_response.json()["release_version"] == second
    audit_log = _audit_log(db_session, "release.activated", second)
    assert audit_log is not None
    activation_before_state = audit_log.before_state
    activation_after_state = audit_log.after_state
    assert activation_before_state is not None
    assert activation_after_state is not None
    assert activation_before_state["active"] is False
    assert activation_after_state["active"] is True


def test_release_rollback_activates_rollback_target(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    rollback_target = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )
    current = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
        rollback_target=rollback_target,
    )
    assert client.post(
        f"/admin/v1/services/{service_id}/releases/{current}:activate",
        headers=_admin_headers(),
    ).status_code == 200

    response = client.post(
        f"/admin/v1/services/{service_id}/releases/{current}:rollback",
        headers=_admin_headers(),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["release_version"] == rollback_target
    db_session.expire_all()
    assert cast(models.Release, db_session.get(models.Release, rollback_target)).active is True
    assert cast(models.Release, db_session.get(models.Release, current)).active is False
    audit_log = _audit_log(db_session, "release.rollback", current)
    assert audit_log is not None
    rollback_after_state = audit_log.after_state
    assert rollback_after_state is not None
    assert rollback_after_state["release_version"] == rollback_target
    assert rollback_after_state["rollback_from"] == current


def test_application_admin_service_owner_can_manage_assigned_service_releases(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    other_service_id = f"svc-release-other-{uuid4().hex}"
    app_admin_user_id: str | None = None
    try:
        _create_service(client, other_service_id)
        cookies, app_admin_user_id = _application_admin_session_cookies(
            db_session,
            service_id,
            role="service_owner",
        )
        rollback_target_test_run_id = _seed_test_run(
            db_session,
            service_id=service_id,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            gate_passed=True,
            risk_pass_rate=Decimal("1.0"),
        )
        rollback_target_response = _create_release_response(
            client,
            service_id,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            test_run_id=rollback_target_test_run_id,
            cookies=cookies,
        )
        assert rollback_target_response.status_code == 201
        rollback_target = rollback_target_response.json()["release_version"]
        assert rollback_target_response.json()["released_by"] == app_admin_user_id

        current_test_run_id = _seed_test_run(
            db_session,
            service_id=service_id,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            gate_passed=True,
            risk_pass_rate=Decimal("1.0"),
        )
        current_response = _create_release_response(
            client,
            service_id,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            test_run_id=current_test_run_id,
            rollback_target=rollback_target,
            cookies=cookies,
        )
        assert current_response.status_code == 201
        current = current_response.json()["release_version"]

        activate_response = client.post(
            f"/admin/v1/services/{service_id}/releases/{current}:activate",
            cookies=cookies,
        )
        rollback_response = client.post(
            f"/admin/v1/services/{service_id}/releases/{current}:rollback",
            cookies=cookies,
        )
        denied_other_create = _create_release_response(
            client,
            other_service_id,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            test_run_id=current_test_run_id,
            cookies=cookies,
        )
        denied_other_activate = client.post(
            f"/admin/v1/services/{other_service_id}/releases/{current}:activate",
            cookies=cookies,
        )
        denied_other_rollback = client.post(
            f"/admin/v1/services/{other_service_id}/releases/{current}:rollback",
            cookies=cookies,
        )

        assert activate_response.status_code == 200
        assert activate_response.json()["active"] is True
        assert rollback_response.status_code == 200
        assert rollback_response.json()["release_version"] == rollback_target
        for denied in (
            denied_other_create,
            denied_other_activate,
            denied_other_rollback,
        ):
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
    finally:
        if app_admin_user_id is not None:
            _purge_admin_user(db_session, app_admin_user_id)
        _purge_service_rows(db_session, service_id)
        _purge_service_rows(db_session, other_service_id)


def test_application_admin_read_only_service_role_cannot_manage_releases(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    app_admin_user_id: str | None = None
    try:
        cookies, app_admin_user_id = _application_admin_session_cookies(
            db_session,
            service_id,
            role="service_operator",
        )
        test_run_id = _seed_test_run(
            db_session,
            service_id=service_id,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            gate_passed=True,
            risk_pass_rate=Decimal("1.0"),
        )

        response = _create_release_response(
            client,
            service_id,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            test_run_id=test_run_id,
            cookies=cookies,
        )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
    finally:
        if app_admin_user_id is not None:
            _purge_admin_user(db_session, app_admin_user_id)
        _purge_service_rows(db_session, service_id)


def test_runtime_uses_active_release_versions_after_activation(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    api_key_payload = {
        "service_id": service_id,
        "environment": "prod",
        "app_id": "dify-platform",
        "allowed_intents": [],
        "allowed_route_keys": [],
        "expires_in_days": 30,
    }
    missing_release_response = client.post(
        "/admin/v1/api-keys",
        headers=_admin_headers(),
        json=api_key_payload,
    )
    assert missing_release_response.status_code == 422
    assert (
        missing_release_response.json()["error"]["message"]
        == "released catalog is required for scoped API key creation."
    )
    test_run_id = _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )
    release_version = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
        test_run_id=test_run_id,
    )
    assert client.post(
        f"/admin/v1/services/{service_id}/releases/{release_version}:activate",
        headers=_admin_headers(),
    ).status_code == 200
    secret_response = client.post(
        "/admin/v1/api-keys",
        headers=_admin_headers(),
        json=api_key_payload,
    )
    assert secret_response.status_code == 201
    secret_body = secret_response.json()

    runtime_response = client.post(
        "/v1/intent-route",
        headers={
            "Authorization": f"Bearer {secret_body['api_key']}",
            "X-Key-Id": secret_body["key_id"],
            "X-App-Id": "dify-platform",
            "X-Service-Id": service_id,
            "X-Request-Id": "req-release-flow-runtime",
        },
        json={"query": "api timeout gateway incident latency"},
    )

    body = runtime_response.json()
    assert runtime_response.status_code == 200
    assert body["release_version"] == release_version
    runtime_log = db_session.scalar(
        select(models.RuntimeLog).where(models.RuntimeLog.trace_id == body["trace_id"])
    )
    assert runtime_log is not None
    assert runtime_log.release_version == release_version
    assert runtime_log.policy_version == policy_version
    assert runtime_log.intent_catalog_version == catalog_version
    assert runtime_log.test_run_id == test_run_id


def test_sprint_zero_vertical_slice(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv("INTENT_ROUTING_ENVIRONMENT", "prod")
    clear_embedding_provider_cache()
    lock_connection = _acquire_sprint_zero_lock(db_session)
    try:
        _purge_service_rows(db_session, SPRINT_ZERO_SERVICE_ID)
        client = _client(db_session)

        _create_service(client, SPRINT_ZERO_SERVICE_ID)

        intent_examples = {
            "it_api_timeout": {
                "route_key": "it.helpdesk.api_timeout",
                "include_keywords": ["api", "timeout", "500", "에러"],
                "positive": [
                    "API Timeout이 발생해요",
                    "보험금 청구 화면에서 500 에러가 나요",
                    "api timeout gateway incident latency",
                ],
                "negative": ["비밀번호 재설정 요청", "계정 잠금 해제 필요"],
            },
            "it_password_reset": {
                "route_key": "it.helpdesk.password_reset",
                "include_keywords": ["password", "비밀번호", "reset", "재설정"],
                "positive": ["비밀번호 재설정 요청", "password reset help"],
                "negative": ["API Timeout이 발생해요", "계정 잠금 해제 필요"],
            },
            "it_account_unlock": {
                "route_key": "it.helpdesk.account_unlock",
                "include_keywords": ["account", "unlock", "계정", "잠금"],
                "positive": ["계정 잠금 해제 필요", "account unlock request"],
                "negative": ["API Timeout이 발생해요", "비밀번호 재설정 요청"],
            },
        }
        expected_example_count = _sprint_zero_example_count(intent_examples)
        for intent_id, config in intent_examples.items():
            _create_intent(
                client,
                SPRINT_ZERO_SERVICE_ID,
                intent_id=intent_id,
                route_key=str(config["route_key"]),
                include_keywords=cast("list[str]", config["include_keywords"]),
            )
            _patch_intent(client, SPRINT_ZERO_SERVICE_ID, intent_id, {"status": "active"})
            for example_type in ("positive", "negative"):
                for text_raw in cast("list[str]", config[example_type]):
                    example = _create_example(
                        client,
                        SPRINT_ZERO_SERVICE_ID,
                        intent_id,
                        text_raw,
                        example_type=example_type,
                    )
                    _approve_example(
                        client,
                        SPRINT_ZERO_SERVICE_ID,
                        example["example_id"],
                    )

        _assert_approved_examples_have_fake_embeddings(
            db_session,
            SPRINT_ZERO_SERVICE_ID,
            expected_count=expected_example_count,
        )
        policy_version = _create_sprint_zero_policy_version(client, SPRINT_ZERO_SERVICE_ID)
        catalog_version = _create_catalog_version(client, SPRINT_ZERO_SERVICE_ID)
        test_run_body = _run_sprint_zero_csv(
            client,
            SPRINT_ZERO_SERVICE_ID,
            policy_version=policy_version,
            catalog_version=catalog_version,
        )
        assert test_run_body["gate_passed"] is True
        assert test_run_body["pass_rate"] >= 0.70

        release_response = _create_release_response(
            client,
            SPRINT_ZERO_SERVICE_ID,
            policy_version=policy_version,
            intent_catalog_version=catalog_version,
            test_run_id=str(test_run_body["test_run_id"]),
        )
        assert release_response.status_code == 201
        release_body = release_response.json()
        release_version = str(release_body["release_version"])
        activate_response = client.post(
            f"/admin/v1/services/{SPRINT_ZERO_SERVICE_ID}/releases/{release_version}:activate",
            headers=_admin_headers(),
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["active"] is True
        api_key_response = client.post(
            "/admin/v1/api-keys",
            headers=_admin_headers(),
            json={
                "service_id": SPRINT_ZERO_SERVICE_ID,
                "environment": "prod",
                "app_id": "dify-platform",
                "allowed_intents": [],
                "allowed_route_keys": [],
                "expires_in_days": 30,
            },
        )
        assert api_key_response.status_code == 201
        api_key_body = api_key_response.json()

        raw_query = "api timeout gateway incident latency 전화 010-1234-5678"
        route_response = client.post(
            "/v1/intent-route",
            headers={
                "Authorization": f"Bearer {api_key_body['api_key']}",
                "X-Key-Id": api_key_body["key_id"],
                "X-App-Id": "dify-platform",
                "X-Service-Id": SPRINT_ZERO_SERVICE_ID,
                "X-Request-Id": "req-sprint-zero-vertical-slice",
            },
            json=_dify_request(query=raw_query),
        )
        assert route_response.status_code == 200
        route_body = route_response.json()
        assert route_body["trace_id"]
        assert route_body["decision"] == "confident"
        assert route_body["route_key"] == "it.helpdesk.api_timeout"
        assert route_body["release_version"] == release_version

        trace_id = str(route_body["trace_id"])
        log_response = client.get(
            f"/admin/v1/services/{SPRINT_ZERO_SERVICE_ID}/runtime-logs/{trace_id}",
            headers=_operator_headers(SPRINT_ZERO_SERVICE_ID),
        )
        assert log_response.status_code == 200
        log_body = log_response.json()
        serialized_log_body = json.dumps(log_body, ensure_ascii=False)
        assert log_body["trace_id"] == trace_id
        assert log_body["query_masked"] == (
            "api timeout gateway incident latency 전화 010-****-5678"
        )
        assert "query_raw" not in serialized_log_body
        assert raw_query not in serialized_log_body
        assert "010-1234-5678" not in serialized_log_body

        view_reason = "Sprint 0 acceptance audit ticket INC-20260626-001"
        raw_query_view_token = _approved_raw_query_view_token(
            client,
            service_id=SPRINT_ZERO_SERVICE_ID,
            trace_id=trace_id,
            view_reason=view_reason,
        )
        decrypt_response = client.post(
            f"/admin/v1/services/{SPRINT_ZERO_SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
            headers=_auditor_headers(SPRINT_ZERO_SERVICE_ID),
            json={
                "view_reason": view_reason,
                "raw_query_view_token": raw_query_view_token,
            },
        )
        assert decrypt_response.status_code == 200
        decrypt_body = decrypt_response.json()
        assert decrypt_body["query_raw"] == raw_query
        audit_log = db_session.scalar(
            select(models.AuditLog)
            .where(models.AuditLog.event_type == "raw_query.viewed")
            .where(models.AuditLog.trace_id == trace_id)
            .where(models.AuditLog.actor_id == "auditor-user")
        )
        assert audit_log is not None
        assert audit_log.service_id == SPRINT_ZERO_SERVICE_ID
        assert audit_log.view_reason == "governed workflow reason supplied"
    finally:
        db_session.rollback()
        _purge_service_rows(db_session, SPRINT_ZERO_SERVICE_ID)
        _release_sprint_zero_lock(lock_connection)


def test_release_list_and_audit_logs_cover_catalog_release_activation_and_rollback(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    rollback_target = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )
    current = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
        rollback_target=rollback_target,
    )
    assert client.post(
        f"/admin/v1/services/{service_id}/releases/{current}:activate",
        headers=_admin_headers(),
    ).status_code == 200
    assert client.post(
        f"/admin/v1/services/{service_id}/releases/{current}:rollback",
        headers=_admin_headers(),
    ).status_code == 200

    list_response = client.get(
        f"/admin/v1/services/{service_id}/releases?environment=prod",
        headers=_admin_headers(),
    )

    assert list_response.status_code == 200
    release_versions = {release["release_version"] for release in list_response.json()}
    assert {rollback_target, current}.issubset(release_versions)
    events = {
        audit.event_type: audit
        for audit in db_session.scalars(
            select(models.AuditLog).where(models.AuditLog.service_id == service_id)
        )
    }
    assert "catalog_version.created" in events
    assert "release.created" in events
    assert "release.activated" in events
    assert "release.rollback" in events
    for event_type in ("release.created", "release.activated", "release.rollback"):
        after_state = events[event_type].after_state
        assert after_state is not None
        assert after_state["release_version"]
        assert after_state["policy_version"] == policy_version
        assert after_state["intent_catalog_version"] == catalog_version
        assert after_state["test_run_id"]
        assert "pass_rate" in after_state
        assert after_state["risk_pass_rate"] == pytest.approx(1.0)
        assert "rollback_target" in after_state


def test_release_list_and_active_lookup_reject_unsupported_environment_filter(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, _, _, client = _release_setup(db_session, monkeypatch)

    list_response = client.get(
        f"/admin/v1/services/{service_id}/releases",
        headers=_admin_headers(),
        params={"environment": "pilot"},
    )
    active_response = client.get(
        f"/admin/v1/services/{service_id}/releases/active",
        headers=_admin_headers(),
        params={"environment": "pilot"},
    )

    assert list_response.status_code == 422
    assert list_response.json()["error"]["code"] == "INVALID_REQUEST"
    assert (
        list_response.json()["error"]["message"]
        == "environment must be one of dev, qa, prod."
    )
    assert active_response.status_code == 422
    assert active_response.json()["error"]["code"] == "INVALID_REQUEST"
    assert (
        active_response.json()["error"]["message"]
        == "environment must be one of dev, qa, prod."
    )


def test_security_lifecycle_repository_methods_filter_count_and_redact(
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    later = now + timedelta(seconds=1)
    already_deleted_at = now - timedelta(hours=1)
    service_id = f"svc-lifecycle-{uuid4().hex}"
    other_service_id = f"svc-lifecycle-other-{uuid4().hex}"
    repository = IntentRoutingRepository(db_session)
    try:
        for candidate_service_id in (service_id, other_service_id):
            repository.create_service(
                service_id=candidate_service_id,
                display_name="Lifecycle repository service",
                max_input_tokens=256,
                status="active",
                created_by="lifecycle-test",
                created_at=now,
                updated_at=now,
            )
            repository.create_intent(
                service_id=candidate_service_id,
                intent_id="intent-lifecycle",
                domain="it",
                display_name="Lifecycle intent",
                description="Exercise security lifecycle repositories.",
                route_key=f"it.lifecycle.{candidate_service_id[-8:]}",
                status="active",
                include_keywords=[],
                exclude_keywords=[],
                created_by="lifecycle-test",
                updated_by="lifecycle-test",
                created_at=now,
                updated_at=now,
            )

        run = repository.create_raw_text_rewrap_run(
            rewrap_run_id=f"rewrap-{uuid4().hex}",
            service_id=service_id,
            target_key_id="key-new",
            source_key_ids=["key-old"],
            included_tables=["intent_examples", "runtime_logs"],
            dry_run=False,
            approval_id="approval-123",
            actor_id="security-admin",
            status="running",
            scanned_count=0,
            rewrapped_count=0,
            skipped_count=0,
            failed_count=0,
            report={},
            started_at=now,
            completed_at=None,
        )
        completed = repository.complete_raw_text_rewrap_run(
            run,
            status="completed",
            scanned_count=4,
            rewrapped_count=3,
            skipped_count=1,
            failed_count=0,
            report={"dry_run": False},
            completed_at=now,
        )

        first_example = repository.create_example(
            service_id=service_id,
            intent_id="intent-lifecycle",
            example_type="positive",
            text_raw_ciphertext=b"example-ciphertext-1",
            text_raw_encrypted_dek=b"example-dek-1",
            text_raw_encrypted_dek_iv=b"example-dek-iv-1",
            text_raw_encrypted_dek_auth_tag=b"example-dek-auth-tag-1",
            text_raw_key_id="key-old",
            text_raw_iv=b"example-iv-1",
            text_raw_auth_tag=b"example-auth-tag-1",
            text_raw_algorithm="AES-GCM",
            text_masked="masked example 1",
            embedding=None,
            source="lifecycle-test",
            test_case_id=None,
            approved=True,
            created_by="lifecycle-test",
            created_at=now,
        )
        repository.create_example(
            service_id=service_id,
            intent_id="intent-lifecycle",
            example_type="positive",
            text_raw_ciphertext=b"example-ciphertext-2",
            text_raw_encrypted_dek=b"example-dek-2",
            text_raw_encrypted_dek_iv=b"example-dek-iv-2",
            text_raw_encrypted_dek_auth_tag=b"example-dek-auth-tag-2",
            text_raw_key_id="key-new",
            text_raw_iv=b"example-iv-2",
            text_raw_auth_tag=b"example-auth-tag-2",
            text_raw_algorithm="AES-GCM",
            text_masked="masked example 2",
            embedding=None,
            source="lifecycle-test",
            test_case_id=None,
            approved=True,
            created_by="lifecycle-test",
            created_at=later,
        )
        repository.create_example(
            service_id=other_service_id,
            intent_id="intent-lifecycle",
            example_type="positive",
            text_raw_ciphertext=b"other-example-ciphertext",
            text_raw_encrypted_dek=b"other-example-dek",
            text_raw_encrypted_dek_iv=b"other-example-dek-iv",
            text_raw_encrypted_dek_auth_tag=b"other-example-dek-auth-tag",
            text_raw_key_id="key-old",
            text_raw_iv=b"other-example-iv",
            text_raw_auth_tag=b"other-example-auth-tag",
            text_raw_algorithm="AES-GCM",
            text_masked="masked other example",
            embedding=None,
            source="lifecycle-test",
            test_case_id=None,
            approved=True,
            created_by="lifecycle-test",
            created_at=now,
        )

        first_log = repository.insert_runtime_log(
            trace_id=f"trace-lifecycle-{uuid4().hex}",
            service_id=service_id,
            latency_ms=10,
            query_raw_ciphertext=b"query-ciphertext-1",
            query_raw_encrypted_dek=b"query-dek-1",
            query_raw_encrypted_dek_iv=b"query-dek-iv-1",
            query_raw_encrypted_dek_auth_tag=b"query-dek-auth-tag-1",
            query_raw_key_id="key-old",
            query_raw_iv=b"query-iv-1",
            query_raw_auth_tag=b"query-auth-tag-1",
            query_raw_algorithm="AES-GCM",
            query_masked="masked query 1",
            created_at=now,
        )
        second_log = repository.insert_runtime_log(
            trace_id=f"trace-lifecycle-{uuid4().hex}",
            service_id=service_id,
            latency_ms=11,
            query_raw_ciphertext=b"query-ciphertext-2",
            query_raw_encrypted_dek=b"query-dek-2",
            query_raw_encrypted_dek_iv=b"query-dek-iv-2",
            query_raw_encrypted_dek_auth_tag=b"query-dek-auth-tag-2",
            query_raw_key_id="key-new",
            query_raw_iv=b"query-iv-2",
            query_raw_auth_tag=b"query-auth-tag-2",
            query_raw_algorithm="AES-GCM",
            query_masked="masked query 2",
            created_at=later,
        )
        already_redacted_log = repository.insert_runtime_log(
            trace_id=f"trace-lifecycle-redacted-{uuid4().hex}",
            service_id=service_id,
            latency_ms=12,
            query_masked="masked redacted query",
            raw_query_deleted_at=already_deleted_at,
            raw_query_deleted_by="retention-job",
            raw_query_delete_reason="expired",
            created_at=now,
        )
        rawless_log = repository.insert_runtime_log(
            trace_id=f"trace-lifecycle-rawless-{uuid4().hex}",
            service_id=service_id,
            latency_ms=12,
            query_masked="masked rawless query",
            created_at=now,
        )
        partial_envelope_log = repository.insert_runtime_log(
            trace_id=f"trace-lifecycle-partial-{uuid4().hex}",
            service_id=service_id,
            latency_ms=12,
            query_raw_key_id="key-old",
            query_masked="masked partial query",
            created_at=now,
        )
        other_log = repository.insert_runtime_log(
            trace_id=f"trace-lifecycle-other-{uuid4().hex}",
            service_id=other_service_id,
            latency_ms=13,
            query_raw_ciphertext=b"other-query-ciphertext",
            query_raw_encrypted_dek=b"other-query-dek",
            query_raw_encrypted_dek_iv=b"other-query-dek-iv",
            query_raw_encrypted_dek_auth_tag=b"other-query-dek-auth-tag",
            query_raw_key_id="key-old",
            query_raw_iv=b"other-query-iv",
            query_raw_auth_tag=b"other-query-auth-tag",
            query_raw_algorithm="AES-GCM",
            query_masked="masked other query",
            created_at=now,
        )
        audit_old = repository.insert_audit_log(
            event_type="raw_query.viewed",
            actor_id="auditor",
            service_id=service_id,
            trace_id=first_log.trace_id,
            target_type="runtime_log",
            target_id=first_log.trace_id,
            view_reason="incident review",
            source_ip="127.0.0.1",
            before_state=None,
            after_state={"viewed": True},
            created_at=now,
        )
        audit_new = repository.insert_audit_log(
            event_type="raw_query.redacted",
            actor_id="security-admin",
            service_id=service_id,
            trace_id=second_log.trace_id,
            target_type="runtime_log",
            target_id=second_log.trace_id,
            view_reason=None,
            source_ip="127.0.0.1",
            before_state=None,
            after_state={"redacted": True},
            created_at=later,
        )

        examples = repository.list_intent_examples_for_rewrap(
            service_id,
            key_ids=["key-old"],
        )
        logs = repository.list_runtime_logs_for_rewrap(service_id, key_ids=["key-old"])
        limited_logs = repository.list_runtime_logs_for_rewrap(service_id, limit=1)
        counts = repository.count_raw_text_key_ids(service_id)
        audit_logs = repository.list_audit_logs(
            service_id,
            limit=10,
            event_type="raw_query.viewed",
            trace_id=first_log.trace_id,
        )
        redacted_count = repository.redact_runtime_raw_queries(
            service_id,
            trace_ids=[
                first_log.trace_id,
                already_redacted_log.trace_id,
                rawless_log.trace_id,
                partial_envelope_log.trace_id,
                other_log.trace_id,
            ],
            actor_id="security-admin",
            reason="retention expired",
            deleted_at=now,
        )
        second_redacted_count = repository.redact_runtime_raw_queries(
            service_id,
            trace_ids=[
                first_log.trace_id,
                already_redacted_log.trace_id,
                rawless_log.trace_id,
                partial_envelope_log.trace_id,
                other_log.trace_id,
            ],
            actor_id="second-admin",
            reason="second pass",
            deleted_at=later,
        )
        db_session.expire_all()

        assert completed.status == "completed"
        assert completed.rewrapped_count == 3
        assert completed.report == {"dry_run": False}
        assert examples == [first_example]
        assert repository.list_intent_examples_for_rewrap(service_id, limit=1) == [
            first_example
        ]
        assert logs == [first_log]
        assert limited_logs == [first_log]
        assert counts == {
            "intent_examples": {"key-new": 1, "key-old": 1},
            "runtime_logs": {"key-new": 1, "key-old": 1},
            "runtime_logs_redacted": 1,
        }
        assert audit_logs == [audit_old]
        assert audit_new not in audit_logs
        assert repository.list_audit_logs(service_id, limit=1) == [audit_new]
        assert redacted_count == 2
        assert second_redacted_count == 0
        assert first_log.query_raw_ciphertext is None
        assert first_log.query_raw_encrypted_dek is None
        assert first_log.query_raw_encrypted_dek_iv is None
        assert first_log.query_raw_encrypted_dek_auth_tag is None
        assert first_log.query_raw_key_id is None
        assert first_log.query_raw_iv is None
        assert first_log.query_raw_auth_tag is None
        assert first_log.query_raw_algorithm is None
        assert first_log.raw_query_deleted_at == now
        assert first_log.raw_query_deleted_by == "security-admin"
        assert first_log.raw_query_delete_reason == "retention expired"
        assert already_redacted_log.raw_query_deleted_at == already_deleted_at
        assert already_redacted_log.raw_query_deleted_by == "retention-job"
        assert already_redacted_log.raw_query_delete_reason == "expired"
        assert rawless_log.raw_query_deleted_at is None
        assert rawless_log.raw_query_deleted_by is None
        assert rawless_log.raw_query_delete_reason is None
        assert partial_envelope_log.query_raw_key_id is None
        assert partial_envelope_log.raw_query_deleted_at == now
        assert partial_envelope_log.raw_query_deleted_by == "security-admin"
        assert partial_envelope_log.raw_query_delete_reason == "retention expired"
        assert other_log.query_raw_key_id == "key-old"
        assert other_log.raw_query_deleted_at is None
    finally:
        db_session.rollback()
        _purge_service_rows(db_session, service_id)
        _purge_service_rows(db_session, other_service_id)


def _client(db_session: Session) -> TestClient:
    clear_embedding_provider_cache()
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    def runtime_lookup(key_id: str) -> ApiKeyRecord | None:
        model = IntentRoutingRepository(db_session).get_api_key_by_id(key_id)
        if model is None:
            return None
        return ApiKeyRecord(
            key_id=model.key_id,
            key_hash=model.key_hash,
            key_fingerprint=model.key_fingerprint,
            environment=model.environment,
            app_id=model.app_id,
            service_id=model.service_id,
            allowed_intents=list(model.allowed_intents or []),
            allowed_route_keys=list(model.allowed_route_keys or []),
            status=model.status,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
        )

    @contextmanager
    def override_runtime_log_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    runtime_module = __import__("intent_routing.api.runtime", fromlist=["get_runtime_session"])
    app.dependency_overrides[runtime_module.get_runtime_session] = override_session
    app.dependency_overrides[get_api_key_lookup] = lambda: runtime_lookup
    app.state.runtime_log_session_factory = override_runtime_log_session
    return TestClient(app, raise_server_exceptions=False)


def _admin_headers(**overrides: str) -> dict[str, str]:
    headers = {
        "X-Admin-Token": "local-admin-token",
        "X-Actor-Id": "admin-user",
        "X-Actor-Roles": "system_admin",
    }
    headers.update(overrides)
    return headers


def _raw_text_kek() -> str:
    return base64.b64encode(b"0" * 32).decode("ascii")


def _service_payload(service_id: str) -> dict[str, object]:
    return {
        "service_id": service_id,
        "display_name": "Release flow service",
        "max_input_tokens": 256,
    }


def _create_service(client: TestClient, service_id: str) -> None:
    response = client.post(
        "/admin/v1/services",
        headers=_admin_headers(),
        json=_service_payload(service_id),
    )
    assert response.status_code == 201


def _create_intent(
    client: TestClient,
    service_id: str,
    *,
    intent_id: str = "intent-api-timeout",
    route_key: str = "it.helpdesk.api_timeout",
    include_keywords: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/admin/v1/services/{service_id}/intents",
        headers=_admin_headers(),
        json={
            "intent_id": intent_id,
            "domain": "it",
            "display_name": f"Intent {intent_id}",
            "description": "Route release traffic.",
            "route_key": route_key,
            "include_keywords": include_keywords or [
                "api",
                "timeout",
                "gateway",
                "incident",
                "latency",
            ],
            "exclude_keywords": exclude_keywords or [],
        },
    )
    assert response.status_code == 201
    return cast("dict[str, object]", response.json())


def _patch_intent(
    client: TestClient,
    service_id: str,
    intent_id: str,
    payload: dict[str, object],
) -> None:
    response = client.patch(
        f"/admin/v1/services/{service_id}/intents/{intent_id}",
        headers=_admin_headers(),
        json=payload,
    )
    assert response.status_code == 200


def _create_example(
    client: TestClient,
    service_id: str,
    intent_id: str,
    text_raw: str,
    *,
    example_type: str = "positive",
) -> dict[str, Any]:
    response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent_id}/examples",
        headers=_admin_headers(),
        json={
            "example_type": example_type,
            "text_raw": text_raw,
            "source": "release-flow-test",
            "test_case_id": None,
        },
    )
    assert response.status_code == 201
    return cast("dict[str, Any]", response.json())


def _approve_example(client: TestClient, service_id: str, example_id: str) -> None:
    response = client.patch(
        f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
        headers=_admin_headers(),
    )
    assert response.status_code == 200


def _create_active_intent_with_approved_example(
    client: TestClient,
    service_id: str,
) -> None:
    _create_intent(client, service_id)
    _patch_intent(client, service_id, "intent-api-timeout", {"status": "active"})
    example = _create_example(
        client,
        service_id,
        "intent-api-timeout",
        "api timeout gateway incident latency",
    )
    _approve_example(client, service_id, example["example_id"])


def _policy_payload() -> dict[str, object]:
    return {
        "threshold_preset": "balanced",
        "clarify_margin": 0.08,
        "min_candidate_score": 0.55,
        "fallback_score": 0.45,
        "risk_policy": {"enabled": True},
        "off_topic_policy": {
            "enabled": True,
            "keywords": ["weather"],
            "message": "That request is outside the service policy.",
            "fallback_policy": {
                "type": "fixed_message",
                "retryable": False,
                "recommended_action": "handoff_to_default_channel",
            },
        },
    }


def _create_service_and_policy(client: TestClient, service_id: str) -> str:
    _create_service(client, service_id)
    response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_admin_headers(),
        json=_policy_payload(),
    )
    assert response.status_code == 201
    return str(response.json()["policy_version"])


def _create_catalog_version(client: TestClient, service_id: str) -> str:
    response = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(),
        json={"description": "Release flow catalog version"},
    )
    assert response.status_code == 201
    return str(response.json()["intent_catalog_version"])


def _create_sprint_zero_policy_version(client: TestClient, service_id: str) -> str:
    response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_admin_headers(),
        json={
            "threshold_preset": "balanced",
            "clarify_margin": 0.08,
            "min_candidate_score": 0.55,
            "fallback_score": 0.45,
            "risk_policy": {"enabled": True},
            "off_topic_policy": {
                "enabled": True,
                "keywords": ["날씨", "점심"],
                "message": "서비스 범위 밖 문의입니다.",
                "fallback_policy": {
                    "type": "fixed_message",
                    "retryable": False,
                    "recommended_action": "handoff_to_default_channel",
                },
            },
        },
    )
    assert response.status_code == 201
    return str(response.json()["policy_version"])


def _run_sprint_zero_csv(
    client: TestClient,
    service_id: str,
    *,
    policy_version: str,
    catalog_version: str,
) -> dict[str, Any]:
    response = client.post(
        f"/admin/v1/services/{service_id}/test-runs",
        headers=_admin_headers(),
        json={
            "policy_version": policy_version,
            "intent_catalog_version": catalog_version,
            "source_filename": "sprint0_cases.csv",
            "csv_text": _sprint0_csv_text(),
        },
    )
    assert response.status_code == 201
    return cast("dict[str, Any]", response.json())


def _sprint0_csv_text() -> str:
    return (
        Path(__file__).resolve().parents[1] / "fixtures" / "sprint0_cases.csv"
    ).read_text()


def _dify_request(*, query: str) -> dict[str, object]:
    payload = cast("dict[str, object]", json.loads(QUERY_FIXTURE.read_text()))
    payload["query"] = query
    return payload


def _operator_headers(service_id: str) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": "operator-user",
            "X-Actor-Roles": "service_operator",
            "X-Service-Scope": service_id,
        }
    )


def _auditor_headers(service_id: str) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": "auditor-user",
            "X-Actor-Roles": "auditor",
            "X-Service-Scope": service_id,
        }
    )


def _approved_raw_query_view_token(
    client: TestClient,
    *,
    service_id: str,
    trace_id: str,
    view_reason: str,
) -> str:
    created = client.post(
        f"/admin/v1/services/{service_id}/runtime-logs/{trace_id}/raw-query-view-requests",
        headers=_auditor_headers(service_id),
        json={"reason": view_reason},
    )
    assert created.status_code == 201
    request_id = str(created.json()["request_id"])
    approved = client.post(
        f"/admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:approve",
        headers=_admin_headers(actor_id="system-approver"),
        json={"reason": "Sprint 0 governed raw query review approved"},
    )
    assert approved.status_code == 200
    issued = client.post(
        f"/admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:issue-token",
        headers=_auditor_headers(service_id),
        json={},
    )
    assert issued.status_code == 200
    return str(issued.json()["token"])


def _sprint_zero_example_count(
    intent_examples: Mapping[str, Mapping[str, Sequence[str]]],
) -> int:
    return sum(
        len(config["positive"])
        + len(config["negative"])
        for config in intent_examples.values()
    )


def _assert_approved_examples_have_fake_embeddings(
    db_session: Session,
    service_id: str,
    *,
    expected_count: int,
) -> None:
    examples = db_session.scalars(
        select(models.IntentExample).where(
            models.IntentExample.service_id == service_id,
            models.IntentExample.approved.is_(True),
        )
    ).all()
    assert len(examples) == expected_count
    for example in examples:
        assert example.embedding is not None
        assert len(example.embedding) == 1024


def _acquire_sprint_zero_lock(db_session: Session) -> Connection:
    bind = cast("Engine", db_session.get_bind())
    connection = bind.connect()
    connection.execute(
        text("select pg_advisory_lock(hashtext(:lock_key)::bigint)"),
        {"lock_key": "test:sprint-zero-vertical-slice"},
    )
    connection.commit()
    return connection


def _release_sprint_zero_lock(connection: Connection) -> None:
    try:
        connection.execute(
            text("select pg_advisory_unlock(hashtext(:lock_key)::bigint)"),
            {"lock_key": "test:sprint-zero-vertical-slice"},
        )
        connection.commit()
    finally:
        connection.close()


def _purge_service_rows(db_session: Session, service_id: str) -> None:
    db_session.execute(
        text("delete from raw_text_rewrap_runs where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text(
            """
            delete from audit_logs
            where service_id = :service_id
               or target_id in (
                   select release_version from releases where service_id = :service_id
               )
               or target_id in (
                   select intent_catalog_version
                   from intent_catalog_versions
                   where service_id = :service_id
               )
            """
        ),
        {"service_id": service_id},
    )
    db_session.execute(
        text(
            """
            delete from test_results
            where test_run_id in (
                select test_run_id from test_runs where service_id = :service_id
            )
            """
        ),
        {"service_id": service_id},
    )
    db_session.execute(
        text(
            """
            delete from test_cases
            where test_dataset_version in (
                select test_dataset_version
                from test_datasets
                where service_id = :service_id
            )
            """
        ),
        {"service_id": service_id},
    )
    for table_name in (
        "raw_query_view_tokens",
        "governed_action_requests",
        "runtime_logs",
        "releases",
        "test_runs",
        "test_datasets",
        "catalog_version_example_embeddings",
        "vector_index_versions",
        "intent_catalog_versions",
        "policy_versions",
        "intent_examples",
        "intents",
        "api_keys",
        "services",
    ):
        db_session.execute(
            text(f"delete from {table_name} where service_id = :service_id"),
            {"service_id": service_id},
        )
    db_session.commit()


def _release_setup(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    *,
    service_id: str | None = None,
) -> tuple[str, str, str, TestClient]:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv("INTENT_ROUTING_ENVIRONMENT", "prod")
    clear_embedding_provider_cache()
    client = _client(db_session)
    resolved_service_id = service_id or f"svc-release-{uuid4().hex}"
    policy_version = _create_service_and_policy(client, resolved_service_id)
    _create_active_intent_with_approved_example(client, resolved_service_id)
    catalog_version = _create_catalog_version(client, resolved_service_id)
    return resolved_service_id, policy_version, catalog_version, client


def _seed_test_run(
    db_session: Session,
    *,
    service_id: str,
    policy_version: str,
    intent_catalog_version: str,
    gate_passed: bool,
    risk_pass_rate: Decimal,
    model_version: str | None = None,
    vector_index_version: str | None = None,
) -> str:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    dataset_version = f"tds-{service_id}-{uuid4().hex[:8]}"
    test_run_id = f"tr-{service_id}-{uuid4().hex[:8]}"
    repository.create_test_dataset(
        {
            "test_dataset_version": dataset_version,
            "service_id": service_id,
            "source_filename": "release-flow.csv",
            "content_sha256": f"sha256-{uuid4().hex}",
            "created_by": "release-flow-test",
            "created_at": now,
        }
    )
    test_run_values = {
        "test_run_id": test_run_id,
        "service_id": service_id,
        "test_dataset_version": dataset_version,
        "policy_version": policy_version,
        "intent_catalog_version": intent_catalog_version,
        "threshold_preset": "balanced",
        "threshold_value": Decimal("0.8"),
        "pass_rate": Decimal("1.0"),
        "review_rate": Decimal("0.0"),
        "risk_pass_rate": risk_pass_rate,
        "gate_passed": gate_passed,
        "created_by": "release-flow-test",
        "created_at": now,
    }
    if model_version is not None:
        test_run_values["model_version"] = model_version
    if vector_index_version is not None:
        test_run_values["vector_index_version"] = vector_index_version
    repository.create_test_run_with_results(
        test_run_values,
        [],
    )
    db_session.commit()
    return test_run_id


def _create_release_response(
    client: TestClient,
    service_id: str,
    *,
    policy_version: str,
    intent_catalog_version: str,
    test_run_id: str,
    rollback_target: str | None = None,
    environment: str = "prod",
    headers: Mapping[str, str] | None = None,
    cookies: Mapping[str, str] | None = None,
) -> Any:
    return client.post(
        f"/admin/v1/services/{service_id}/releases",
        headers=headers or _admin_headers(),
        cookies=cookies,
        json={
            "environment": environment,
            "policy_version": policy_version,
            "intent_catalog_version": intent_catalog_version,
            "test_run_id": test_run_id,
            "rollback_target": rollback_target,
        },
    )


def _create_valid_release(
    db_session: Session,
    client: TestClient,
    service_id: str,
    *,
    policy_version: str,
    catalog_version: str,
    test_run_id: str | None = None,
    rollback_target: str | None = None,
) -> str:
    resolved_test_run_id = test_run_id or _seed_test_run(
        db_session,
        service_id=service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        gate_passed=True,
        risk_pass_rate=Decimal("1.0"),
    )
    response = _create_release_response(
        client,
        service_id,
        policy_version=policy_version,
        intent_catalog_version=catalog_version,
        test_run_id=resolved_test_run_id,
        rollback_target=rollback_target,
    )
    assert response.status_code == 201
    return str(response.json()["release_version"])


def _application_admin_session_cookies(
    db_session: Session,
    service_id: str,
    *,
    role: str,
) -> tuple[dict[str, str], str]:
    now = datetime.now(UTC)
    user_id = f"release-app-admin-{uuid4().hex}"
    raw_token = f"raw-session-{user_id}"
    repository = IntentRoutingRepository(db_session)
    repository.create_admin_user(
        user_id=user_id,
        email=f"{user_id}@example.com",
        display_name="Release Application Admin",
        password_hash="password-hash",
        status="active",
        admin_access_reason="integration test release application admin",
        created_at=now,
        updated_at=now,
    )
    repository.assign_admin_user_role(
        user_id=user_id,
        role="application_admin",
        assigned_by="integration-test",
        assigned_at=now,
    )
    repository.assign_user_service_role(
        user_id=user_id,
        service_id=service_id,
        role=role,
        assigned_by="integration-test",
        assigned_at=now,
    )
    repository.create_admin_session(
        session_id=f"session-{user_id}",
        user_id=user_id,
        token_hash=hash_admin_session_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(hours=1),
        revoked_at=None,
        last_seen_at=None,
    )
    db_session.commit()
    return {ADMIN_SESSION_COOKIE_NAME: raw_token}, user_id


def _purge_admin_user(db_session: Session, user_id: str) -> None:
    db_session.execute(
        text("delete from admin_sessions where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from user_service_roles where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from admin_user_roles where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.commit()


def _audit_log(
    db_session: Session,
    event_type: str,
    target_id: str,
) -> models.AuditLog | None:
    return db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.event_type == event_type)
        .where(models.AuditLog.target_id == target_id)
        .order_by(models.AuditLog.created_at.desc())
    )


def _policy_state(db_session: Session, policy_version: str) -> dict[str, Any]:
    policy = db_session.get(models.PolicyVersion, policy_version)
    assert policy is not None
    return {
        "threshold_preset": policy.threshold_preset,
        "threshold_value": str(policy.threshold_value),
        "clarify_margin": str(policy.clarify_margin),
        "min_candidate_score": str(policy.min_candidate_score),
        "fallback_score": str(policy.fallback_score),
        "risk_policy": policy.risk_policy,
        "off_topic_policy": policy.off_topic_policy,
    }


def _catalog_state(db_session: Session, catalog_version: str) -> dict[str, Any]:
    catalog = db_session.get(models.IntentCatalogVersion, catalog_version)
    assert catalog is not None
    return {"snapshot": catalog.snapshot}


def _date_segment(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y%m%d")


class _ReleaseEmbeddingProvider:
    dimension = 1024

    def __init__(self, model_version: str) -> None:
        self.model_version = model_version

    def embed_texts(self, texts: list[str], *, max_tokens: int) -> list[list[float]]:
        del texts, max_tokens
        return [[1.0] + [0.0] * 1023]
