from __future__ import annotations

import base64
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.api.dependencies import get_api_key_lookup, get_runtime_environment
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from intent_routing.security.api_keys import ApiKeyRecord


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


def test_catalog_snapshot_includes_active_intents_and_approved_examples(
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
    _create_example(client, service_id, "intent-active", "do not snapshot")

    response = client.post(
        f"/admin/v1/services/{service_id}/catalog-versions",
        headers=_admin_headers(),
    )

    body = response.json()
    assert response.status_code == 201
    assert body["intent_catalog_version"].startswith(f"cat-{service_id}-")
    assert body["service_id"] == service_id
    assert body["created_by"] == "admin-user"
    assert body["snapshot"] == {
        "service_id": service_id,
        "intents": [
            {
                "intent_id": active_intent["intent_id"],
                "domain": "it",
                "display_name": "Intent intent-active",
                "description": "Route release traffic.",
                "route_key": "it.release.active",
                "status": "active",
                "include_keywords": ["release", "active"],
                "exclude_keywords": ["billing"],
                "examples": [
                    {
                        "example_id": approved_example["example_id"],
                        "example_type": "positive",
                        "text_masked": "release me",
                        "approved": True,
                    }
                ],
            }
        ],
    }
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
        lambda: _ReleaseEmbeddingProvider("emb-fake/v1"),
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
    assert body["model_version"] == "emb-fake/v1"
    assert body["vector_index_version"] == f"vec-{catalog_version}-emb-fake/v1-001"
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
    assert (
        next_body["vector_index_version"]
        == f"vec-{catalog_version}-emb-fake/v1-002"
    )


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
        lambda: _ReleaseEmbeddingProvider("emb-fake/v1"),
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
            f"release-version:{service_id}:{released_day}",
            f"vector-index-version:{catalog_version}:emb-fake/v1",
        ]
    )
    assert response.status_code == 201
    assert acquired_lock_keys == expected_lock_keys


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


def test_release_creation_rejects_environment_mismatch(
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
    assert body["error"]["message"] == "Release environment must match service environment."


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


def test_runtime_uses_active_release_versions_after_activation(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    secret_response = client.post(
        "/admin/v1/api-keys",
        headers=_admin_headers(),
        json={
            "service_id": service_id,
            "environment": "prod",
            "app_id": "dify-platform",
            "allowed_intents": [],
            "allowed_route_keys": [],
            "expires_in_days": 30,
        },
    )
    assert secret_response.status_code == 201
    secret_body = secret_response.json()
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
    app.dependency_overrides[get_runtime_environment] = lambda: "prod"
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
        "environment": "prod",
        "default_threshold_preset": "balanced",
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
) -> dict[str, Any]:
    response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent_id}/examples",
        headers=_admin_headers(),
        json={
            "example_type": "positive",
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
    )
    assert response.status_code == 201
    return str(response.json()["intent_catalog_version"])


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
    repository.create_test_run_with_results(
        {
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
        },
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
) -> Any:
    return client.post(
        f"/admin/v1/services/{service_id}/releases",
        headers=_admin_headers(),
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
