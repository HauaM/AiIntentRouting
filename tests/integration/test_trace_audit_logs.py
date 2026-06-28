from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, or_, select, text
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.api.dependencies import get_api_key_lookup, get_runtime_environment
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.fake import FakeEmbeddingProvider
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from intent_routing.security.api_keys import ApiKeyRecord, fingerprint_secret, hash_secret
from intent_routing.security.encryption import EnvelopeEncryptor
from intent_routing.security.pii import mask_pii

QUERY_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dify_request.json"
APP_ID = "trace-audit-app"
KEY_ID = "key-live-trace-audit"
RELEASE_VERSION = "rel-trace-audit-20260625-001"
SERVICE_ID = "svc-trace-audit"
OTHER_SERVICE_ID = "svc-trace-audit-other"
RAW_QUERY = "api timeout gateway incident latency 전화 010-1234-5678"
VIEW_REASON = "장애 분석 ticket INC-20260625-001"


def test_runtime_call_stores_masked_and_encrypted_raw_query(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _client(db_session, monkeypatch)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-trace-audit-store-1"),
        json=_dify_request(query=RAW_QUERY),
    )

    body = response.json()
    assert response.status_code == 200
    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.query_masked == "api timeout gateway incident latency 전화 010-****-5678"
    assert persisted.query_raw_ciphertext is not None
    assert persisted.query_raw_encrypted_dek is not None
    assert RAW_QUERY.encode("utf-8") not in persisted.query_raw_ciphertext


def test_masked_runtime_log_endpoints_never_return_raw_query_fields(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)
    headers = _operator_headers(SERVICE_ID)
    expected_fields = {
        "trace_id",
        "request_id",
        "app_id",
        "service_id",
        "release_version",
        "policy_version",
        "intent_catalog_version",
        "decision",
        "intent_id",
        "confidence",
        "margin",
        "threshold_preset",
        "threshold_value",
        "route_key",
        "error_code",
        "error_category",
        "error_layer",
        "http_status",
        "retryable",
        "latency_ms",
        "query_masked",
        "created_at",
    }

    list_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs",
        headers=headers,
    )
    detail_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    list_body = list_response.json()
    detail_body = detail_response.json()
    assert list_body
    assert set(list_body[0]) == expected_fields
    assert set(detail_body) == expected_fields
    serialized = json.dumps({"list": list_body, "detail": detail_body}, ensure_ascii=False)
    assert "query_raw" not in serialized
    assert RAW_QUERY not in serialized
    assert detail_body["trace_id"] == trace_id
    assert detail_body["query_masked"] == mask_pii(RAW_QUERY)


def test_masked_runtime_log_repository_methods_do_not_select_raw_query_fields(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    repository = IntentRoutingRepository(db_session)

    listed = repository.list_masked_runtime_logs(SERVICE_ID, limit=10)
    detailed = repository.get_masked_runtime_log(SERVICE_ID, trace_id)

    assert listed
    assert detailed is not None
    for row in (listed[0], detailed):
        assert not isinstance(row, models.RuntimeLog)
        assert "query_masked" in row
        assert "query_raw_ciphertext" not in row
        assert not any(key.startswith("query_raw_") for key in row)


def test_runtime_log_list_limit_defaults_and_can_be_overridden(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_ids = _create_runtime_traces(db_session, monkeypatch, count=3)
    client = _client(db_session, monkeypatch)

    default_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs",
        headers=_operator_headers(SERVICE_ID),
    )
    limited_response = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs",
        headers=_operator_headers(SERVICE_ID),
        params={"limit": 2},
    )

    assert default_response.status_code == 200
    assert len(default_response.json()) == len(trace_ids)
    assert limited_response.status_code == 200
    assert len(limited_response.json()) == 2


def test_runtime_log_list_limit_is_validated(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_runtime_state(db_session)
    client = _client(db_session, monkeypatch)

    too_small = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs",
        headers=_operator_headers(SERVICE_ID),
        params={"limit": 0},
    )
    too_large = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs",
        headers=_operator_headers(SERVICE_ID),
        params={"limit": 501},
    )

    assert too_small.status_code == 422
    assert too_small.json()["status"] == "error"
    assert too_large.status_code == 422
    assert too_large.json()["error"]["code"] == "INVALID_REQUEST"


def test_runtime_logs_have_service_created_at_trace_index(db_session: Session) -> None:
    index_definition = db_session.scalar(
        text(
            """
            select indexdef
            from pg_indexes
            where schemaname = current_schema()
              and tablename = 'runtime_logs'
              and indexname = 'ix_runtime_logs_service_created_at_trace'
            """
        )
    )

    assert isinstance(index_definition, str)
    assert "service_id" in index_definition
    assert "created_at DESC" in index_definition
    assert "trace_id" in index_definition


def test_service_operator_can_query_logs_only_for_scoped_service(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    allowed = client.get(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs",
        headers=_operator_headers(SERVICE_ID),
    )
    forbidden = client.get(
        f"/admin/v1/services/{OTHER_SERVICE_ID}/runtime-logs",
        headers=_operator_headers(SERVICE_ID),
    )

    assert allowed.status_code == 200
    assert forbidden.status_code == 403
    assert forbidden.json()["status"] == "error"
    assert forbidden.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_raw_decrypt_requires_view_reason(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    missing = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_auditor_headers(SERVICE_ID),
        json={},
    )
    too_short = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_auditor_headers(SERVICE_ID),
        json={"view_reason": "short"},
    )

    assert missing.status_code == 422
    assert missing.json()["status"] == "error"
    assert too_short.status_code == 422
    assert too_short.json()["error"]["code"] == "INVALID_REQUEST"


def test_raw_decrypt_returns_plaintext_to_auditor_or_system_admin_and_writes_audit_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    auditor_response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_auditor_headers(SERVICE_ID, actor_id="auditor-user"),
        json={"view_reason": VIEW_REASON},
    )
    admin_response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_admin_headers(actor_id="system-user"),
        json={"view_reason": "장애 분석 ticket INC-20260625-002"},
    )

    assert auditor_response.status_code == 200
    assert auditor_response.json()["query_raw"] == RAW_QUERY
    assert auditor_response.json()["trace_id"] == trace_id
    assert auditor_response.json()["service_id"] == SERVICE_ID
    assert auditor_response.json()["viewed_by"] == "auditor-user"
    assert "viewed_at" in auditor_response.json()
    assert admin_response.status_code == 200
    assert admin_response.json()["query_raw"] == RAW_QUERY
    audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.event_type == "raw_query.viewed")
        .where(models.AuditLog.actor_id == "auditor-user")
        .where(models.AuditLog.trace_id == trace_id)
    )
    assert audit_log is not None
    assert audit_log.service_id == SERVICE_ID
    assert audit_log.view_reason == VIEW_REASON
    assert audit_log.source_ip == "testclient"
    assert audit_log.target_type == "runtime_log"
    assert audit_log.target_id == trace_id
    assert audit_log.after_state == {
        "trace_id": trace_id,
        "service_id": SERVICE_ID,
        "query_raw_viewed": True,
    }


def test_raw_decrypt_returns_gone_for_redacted_raw_query_without_view_audit_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    repository = IntentRoutingRepository(db_session)
    redacted_count = repository.redact_runtime_raw_queries(
        SERVICE_ID,
        trace_ids=[trace_id],
        actor_id="retention-job",
        reason="raw query retention policy 30 days",
        deleted_at=datetime.now(UTC),
    )
    db_session.commit()
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_auditor_headers(SERVICE_ID),
        json={"view_reason": VIEW_REASON},
    )

    body = response.json()
    viewed_audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.event_type == "raw_query.viewed")
        .where(models.AuditLog.trace_id == trace_id)
    )
    assert redacted_count == 1
    assert response.status_code == 410
    assert body["status"] == "error"
    assert body["error"]["code"] == "RAW_QUERY_UNAVAILABLE"
    assert "decision" not in body
    assert "query_raw" not in response.text
    assert RAW_QUERY not in response.text
    assert viewed_audit_log is None


def test_raw_decrypt_returns_gone_for_missing_raw_query_envelope_without_view_audit_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_runtime_state(db_session)
    trace_id = f"trace-rawless-{uuid4().hex}"
    repository = IntentRoutingRepository(db_session)
    repository.insert_runtime_log(
        trace_id=trace_id,
        service_id=SERVICE_ID,
        latency_ms=12,
        query_masked="rawless masked query",
        created_at=datetime.now(UTC),
    )
    db_session.commit()
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_auditor_headers(SERVICE_ID),
        json={"view_reason": VIEW_REASON},
    )

    body = response.json()
    viewed_audit_log = db_session.scalar(
        select(models.AuditLog)
        .where(models.AuditLog.event_type == "raw_query.viewed")
        .where(models.AuditLog.trace_id == trace_id)
    )
    assert response.status_code == 410
    assert body["status"] == "error"
    assert body["error"]["code"] == "RAW_QUERY_UNAVAILABLE"
    assert "decision" not in body
    assert "query_raw" not in response.text
    assert viewed_audit_log is None


def test_raw_decrypt_unauthorized_role_returns_forbidden_error_envelope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_operator_headers(SERVICE_ID),
        json={"view_reason": VIEW_REASON},
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "error"
    assert body["error"]["code"] == "SERVICE_SCOPE_DENIED"
    assert "detail" not in body
    assert RAW_QUERY not in response.text


def test_raw_decrypt_wrong_scope_auditor_returns_forbidden_error_envelope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/runtime-logs/{trace_id}:decrypt-raw-query",
        headers=_auditor_headers(OTHER_SERVICE_ID),
        json={"view_reason": VIEW_REASON},
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "error"
    assert body["error"]["code"] == "SERVICE_SCOPE_DENIED"
    assert RAW_QUERY not in response.text


def _client(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    *,
    raise_server_exceptions: bool = True,
) -> TestClient:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv("INTENT_ROUTING_ENVIRONMENT", "prod")
    monkeypatch.setenv("RAW_TEXT_KEK_ID", "local-kek-001")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    clear_embedding_provider_cache()

    app = create_app()
    runtime_module = import_module("intent_routing.api.runtime")

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

    def override_session() -> Iterator[Session]:
        yield db_session

    @contextmanager
    def override_runtime_log_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[get_api_key_lookup] = lambda: runtime_lookup
    app.dependency_overrides[get_runtime_environment] = lambda: "prod"
    app.dependency_overrides[runtime_module.get_runtime_session] = override_session
    app.state.runtime_log_session_factory = override_runtime_log_session
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _create_runtime_trace(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    return _create_runtime_traces(db_session, monkeypatch, count=1)[0]


def _create_runtime_traces(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    *,
    count: int,
) -> list[str]:
    secret = _seed_runtime_state(db_session)
    client = _client(db_session, monkeypatch)
    trace_ids: list[str] = []
    for index in range(count):
        response = client.post(
            "/v1/intent-route",
            headers=_runtime_headers(
                secret,
                request_id=f"req-trace-audit-{index}-{uuid4().hex}",
            ),
            json=_dify_request(query=RAW_QUERY),
        )
        assert response.status_code == 200
        trace_ids.append(cast("str", response.json()["trace_id"]))
    return trace_ids


def _runtime_headers(secret: str, *, request_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {secret}",
        "X-Key-Id": KEY_ID,
        "X-App-Id": APP_ID,
        "X-Service-Id": SERVICE_ID,
        "X-Request-Id": request_id,
    }


def _admin_headers(**overrides: str) -> dict[str, str]:
    headers = {
        "X-Admin-Token": "local-admin-token",
        "X-Actor-Id": "admin-user",
        "X-Actor-Roles": "system_admin",
    }
    headers.update(overrides)
    return headers


def _operator_headers(service_id: str) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": "operator-user",
            "X-Actor-Roles": "service_operator",
            "X-Service-Scope": service_id,
        }
    )


def _auditor_headers(service_id: str, *, actor_id: str = "auditor-user") -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": actor_id,
            "X-Actor-Roles": "auditor",
            "X-Service-Scope": service_id,
        }
    )


def _dify_request(
    *,
    query: str,
    user_context: dict[str, Any] | None = None,
) -> dict[str, object]:
    payload = cast("dict[str, object]", json.loads(QUERY_FIXTURE.read_text()))
    payload["query"] = query
    if user_context is not None:
        payload["user_context"] = user_context
    return payload


def _seed_runtime_state(db_session: Session) -> str:
    _purge_runtime_rows(db_session)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    provider = FakeEmbeddingProvider()
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_raw_text_kek())

    repository.create_service(
        service_id=SERVICE_ID,
        display_name="Trace Audit Helpdesk",
        environment="prod",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="trace-audit-test",
        created_at=now,
        updated_at=now,
    )
    repository.create_service(
        service_id=OTHER_SERVICE_ID,
        display_name="Other Trace Audit Helpdesk",
        environment="prod",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="trace-audit-test",
        created_at=now,
        updated_at=now,
    )

    secret = "irt_trace_audit_live_secret"
    repository.create_api_key(
        key_id=KEY_ID,
        key_hash=hash_secret(secret),
        key_fingerprint=fingerprint_secret(secret),
        environment="prod",
        app_id=APP_ID,
        service_id=SERVICE_ID,
        allowed_intents=[],
        allowed_route_keys=[],
        status="active",
        expires_at=now + timedelta(days=30),
        revoked_at=None,
        created_by="trace-audit-test",
        created_at=now,
    )

    intents = [
        {
            "intent_id": "intent-api-timeout",
            "domain": "it",
            "display_name": "API timeout incident",
            "description": "Handle API timeout issues.",
            "route_key": "it.helpdesk.api_timeout",
            "include_keywords": ["timeout", "api", "gateway", "incident", "latency"],
            "exclude_keywords": [],
        }
    ]
    for intent in intents:
        intent_id = cast("str", intent["intent_id"])
        repository.create_intent(
            service_id=SERVICE_ID,
            intent_id=intent_id,
            domain=cast("str", intent["domain"]),
            display_name=cast("str", intent["display_name"]),
            description=cast("str", intent["description"]),
            route_key=cast("str", intent["route_key"]),
            status="active",
            include_keywords=cast("list[str]", intent["include_keywords"]),
            exclude_keywords=cast("list[str]", intent["exclude_keywords"]),
            created_by="trace-audit-test",
            updated_by="trace-audit-test",
            created_at=now,
            updated_at=now,
        )
        _create_approved_example(
            repository,
            encryptor=encryptor,
            provider=provider,
            service_id=SERVICE_ID,
            intent_id=intent_id,
            text_raw="api timeout gateway incident latency",
            created_at=now,
        )

    repository.create_policy_version(
        policy_version="pol-trace-audit-20260625-001",
        service_id=SERVICE_ID,
        threshold_preset="balanced",
        threshold_value=Decimal("0.80"),
        clarify_margin=Decimal("0.08"),
        min_candidate_score=Decimal("0.55"),
        fallback_score=Decimal("0.45"),
        risk_policy={"enabled": True},
        off_topic_policy={"enabled": False, "keywords": [], "message": ""},
        created_by="trace-audit-test",
        created_at=now,
    )
    repository.create_catalog_version(
        intent_catalog_version="cat-trace-audit-20260625-001",
        service_id=SERVICE_ID,
        snapshot={"intents": intents},
        created_by="trace-audit-test",
        created_at=now,
    )
    repository.create_test_dataset(
        {
            "test_dataset_version": "ds-trace-audit-20260625-001",
            "service_id": SERVICE_ID,
            "source_filename": "trace-audit-fixture.jsonl",
            "content_sha256": "sha256-trace-audit-fixture",
            "created_by": "trace-audit-test",
            "created_at": now,
        }
    )
    repository.create_test_run_with_results(
        {
            "test_run_id": "tr-trace-audit-20260625-001",
            "service_id": SERVICE_ID,
            "test_dataset_version": "ds-trace-audit-20260625-001",
            "policy_version": "pol-trace-audit-20260625-001",
            "intent_catalog_version": "cat-trace-audit-20260625-001",
            "threshold_preset": "balanced",
            "threshold_value": Decimal("0.80"),
            "pass_rate": Decimal("0.95"),
            "review_rate": Decimal("0.03"),
            "risk_pass_rate": Decimal("1.00"),
            "gate_passed": True,
            "created_by": "trace-audit-test",
            "created_at": now,
        },
        [],
    )
    repository.create_release(
        release_version=RELEASE_VERSION,
        service_id=SERVICE_ID,
        environment="prod",
        policy_version="pol-trace-audit-20260625-001",
        intent_catalog_version="cat-trace-audit-20260625-001",
        model_version="emb-fake-v1",
        vector_index_version="vec-trace-audit-20260625-001",
        test_dataset_version="ds-trace-audit-20260625-001",
        test_run_id="tr-trace-audit-20260625-001",
        pass_rate=Decimal("0.95"),
        risk_pass_rate=Decimal("1.00"),
        active=True,
        released_by="trace-audit-test",
        released_at=now,
        rollback_target=None,
    )
    db_session.commit()
    return secret


def _create_approved_example(
    repository: IntentRoutingRepository,
    *,
    encryptor: EnvelopeEncryptor,
    provider: FakeEmbeddingProvider,
    service_id: str,
    intent_id: str,
    text_raw: str,
    created_at: datetime,
) -> None:
    encrypted = encryptor.encrypt_text(text_raw)
    repository.create_example(
        service_id=service_id,
        intent_id=intent_id,
        example_type="positive",
        text_raw_ciphertext=encrypted.ciphertext,
        text_raw_encrypted_dek=encrypted.encrypted_dek,
        text_raw_encrypted_dek_iv=encrypted.encrypted_dek_iv,
        text_raw_encrypted_dek_auth_tag=encrypted.encrypted_dek_auth_tag,
        text_raw_key_id=encrypted.key_id,
        text_raw_iv=encrypted.iv,
        text_raw_auth_tag=encrypted.auth_tag,
        text_raw_algorithm=encrypted.algorithm,
        text_masked=mask_pii(text_raw),
        embedding=provider.embed_texts([mask_pii(text_raw)], max_tokens=256)[0],
        source="trace-audit-test",
        test_case_id=None,
        approved=True,
        created_by="trace-audit-test",
        created_at=created_at,
    )


def _purge_runtime_rows(db_session: Session) -> None:
    service_ids = (SERVICE_ID, OTHER_SERVICE_ID)
    run_ids = select(models.TestRun.test_run_id).where(
        models.TestRun.service_id.in_(service_ids)
    )
    dataset_versions = select(models.TestDataset.test_dataset_version).where(
        models.TestDataset.service_id.in_(service_ids)
    )

    db_session.execute(
        delete(models.RuntimeLog).where(
            or_(
                models.RuntimeLog.service_id.in_(service_ids),
                models.RuntimeLog.app_id == APP_ID,
            )
        )
    )
    db_session.execute(delete(models.AuditLog).where(models.AuditLog.service_id.in_(service_ids)))
    db_session.execute(delete(models.Release).where(models.Release.service_id.in_(service_ids)))
    db_session.execute(
        delete(models.TestResult).where(models.TestResult.test_run_id.in_(run_ids))
    )
    db_session.execute(delete(models.TestRun).where(models.TestRun.service_id.in_(service_ids)))
    db_session.execute(
        delete(models.TestCase).where(models.TestCase.test_dataset_version.in_(dataset_versions))
    )
    db_session.execute(
        delete(models.TestDataset).where(models.TestDataset.service_id.in_(service_ids))
    )
    db_session.execute(
        delete(models.IntentExample).where(models.IntentExample.service_id.in_(service_ids))
    )
    db_session.execute(delete(models.Intent).where(models.Intent.service_id.in_(service_ids)))
    db_session.execute(
        delete(models.VectorIndexVersion).where(
            models.VectorIndexVersion.service_id.in_(service_ids)
        )
    )
    db_session.execute(
        delete(models.IntentCatalogVersion).where(
            models.IntentCatalogVersion.service_id.in_(service_ids)
        )
    )
    db_session.execute(
        delete(models.PolicyVersion).where(models.PolicyVersion.service_id.in_(service_ids))
    )
    db_session.execute(delete(models.ApiKey).where(models.ApiKey.service_id.in_(service_ids)))
    db_session.execute(delete(models.Service).where(models.Service.service_id.in_(service_ids)))
    db_session.commit()


def _runtime_log(db_session: Session, trace_id: str) -> models.RuntimeLog | None:
    return db_session.scalar(
        select(models.RuntimeLog).where(models.RuntimeLog.trace_id == trace_id)
    )


def _raw_text_kek() -> str:
    return base64.b64encode(b"0" * 32).decode("ascii")
