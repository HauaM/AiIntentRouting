from __future__ import annotations

import base64
import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from intent_routing.api.dependencies import get_api_key_lookup, get_runtime_environment
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.fake import FakeEmbeddingProvider
from intent_routing.embedding.provider import clear_embedding_provider_cache
from intent_routing.main import create_app
from intent_routing.security.api_keys import ApiKeyRecord, fingerprint_secret, hash_secret
from intent_routing.security.encryption import EnvelopeEncryptor
from intent_routing.security.pii import mask_pii

APP_ID = "dify-platform"
KEY_ID = "key-live-it-helpdesk"
QUERY_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dify_request.json"
RELEASE_VERSION = "rel-it-helpdesk-20260625-001"
SERVICE_ID = "it-helpdesk"


def test_healthz_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_documents_validation_errors_as_error_envelope() -> None:
    schema = create_app().openapi()

    validation_response = schema["paths"]["/v1/intent-route"]["post"]["responses"]["422"]
    validation_schema = validation_response["content"]["application/json"]["schema"]

    assert validation_schema == {"$ref": "#/components/schemas/ErrorEnvelope"}
    assert "ErrorEnvelope" in schema["components"]["schemas"]
    assert "ErrorInfo" in schema["components"]["schemas"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    assert "ValidationError" not in schema["components"]["schemas"]


def _record_for(
    secret: str,
    *,
    allowed_route_keys: list[str] | None = None,
    environment: str = "prod",
    expires_at: datetime | None = None,
    key_hash: str | None = None,
    revoked_at: datetime | None = None,
    status: str = "active",
) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id="key-live",
        key_hash=key_hash or hash_secret(secret),
        key_fingerprint=fingerprint_secret(secret),
        environment=environment,
        app_id="app-a",
        service_id="svc-a",
        allowed_intents=[],
        allowed_route_keys=allowed_route_keys or [],
        status=status,
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=1),
        revoked_at=revoked_at,
    )


def _client_with_key_lookup(
    lookup: Any,
    *,
    environment: str = "prod",
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_api_key_lookup] = lambda: lookup
    app.dependency_overrides[get_runtime_environment] = lambda: environment
    return TestClient(app)


def _headers(secret: str, **overrides: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {secret}",
        "X-Key-Id": "key-live",
        "X-App-Id": "app-a",
        "X-Service-Id": "svc-a",
    }
    headers.update(overrides)
    return headers


def _runtime_payload(**user_context: str) -> dict[str, object]:
    return {
        "query": "timeout help",
        "user_context": user_context,
    }


def test_intent_route_missing_authorization_returns_error_envelope() -> None:
    client = _client_with_key_lookup(lambda _key_id: None)

    response = client.post(
        "/v1/intent-route",
        headers={
            "X-Key-Id": "key-live",
            "X-App-Id": "app-a",
            "X-Service-Id": "svc-a",
        },
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["status"] == "error"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"
    assert "trace_id" in body


def test_intent_route_malformed_bearer_returns_authentication_failed() -> None:
    client = _client_with_key_lookup(lambda _key_id: None)

    response = client.post(
        "/v1/intent-route",
        headers=_headers("valid-runtime-secret", Authorization="Basic nope"),
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["status"] == "error"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_missing_app_id_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    headers = _headers(secret)
    headers.pop("X-App-Id")
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=headers,
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_missing_service_id_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    headers = _headers(secret)
    headers.pop("X-Service-Id")
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=headers,
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_missing_key_id_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    headers = _headers(secret)
    headers.pop("X-Key-Id")
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=headers,
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_unknown_key_id_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(lambda _key_id: None)

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_wrong_secret_returns_authentication_failed() -> None:
    client = _client_with_key_lookup(
        lambda _key_id: _record_for("stored-runtime-secret")
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers("wrong-runtime-secret"),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_environment_mismatch_returns_authentication_failed() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(secret, environment="dev"),
        environment="prod",
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_malformed_stored_hash_returns_error_envelope() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(
            secret,
            key_hash="pbkdf2_sha256$0$abcd$abcd",
        )
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["status"] == "error"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"
    assert "detail" not in body


def test_intent_route_invalid_body_returns_sanitized_error_envelope_with_request_id() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))
    raw_text = "전화 010-1234-5678 확인"

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret, **{"X-Request-Id": "req-validation-1"}),
        json={
            "query": {"raw": raw_text},
            "user_context": {},
        },
    )

    body = response.json()
    assert response.status_code == 422
    assert body["status"] == "error"
    assert body["request_id"] == "req-validation-1"
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert "detail" not in body
    assert "010-1234-5678" not in response.text
    assert raw_text not in response.text


def test_intent_route_valid_key_invalid_service_returns_scope_denied() -> None:
    secret = "valid-runtime-secret"
    client = _client_with_key_lookup(lambda _key_id: _record_for(secret))

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret, **{"X-Service-Id": "svc-b"}),
        json=_runtime_payload(),
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "error"
    assert body["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_intent_route_expired_key_returns_authentication_failed() -> None:
    secret = "expired-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(
            secret,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_revoked_key_returns_authentication_failed() -> None:
    secret = "revoked-runtime-secret"
    client = _client_with_key_lookup(
        lambda _key_id: _record_for(
            secret,
            status="revoked",
            revoked_at=datetime.now(UTC),
        )
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(secret),
        json=_runtime_payload(),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_intent_route_authentication_failure_persists_runtime_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch)
    headers = _runtime_headers("unused-secret", request_id="req-runtime-401-log-1")
    headers.pop("Authorization")

    response = client.post(
        "/v1/intent-route",
        headers=headers,
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-401-log-1"
    assert persisted.app_id == APP_ID
    assert persisted.service_id == SERVICE_ID
    assert persisted.decision == "error"
    assert persisted.error_code == "AUTHENTICATION_FAILED"
    assert persisted.http_status == 401
    assert persisted.retryable is False
    assert persisted.query_masked == "api timeout gateway incident latency"


def test_intent_route_scope_failure_persists_runtime_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch)
    headers = _runtime_headers(secret, request_id="req-runtime-403-log-1")
    headers["X-Service-Id"] = "svc-b"

    response = client.post(
        "/v1/intent-route",
        headers=headers,
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 403
    assert body["error"]["code"] == "SERVICE_SCOPE_DENIED"

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-403-log-1"
    assert persisted.app_id == APP_ID
    assert persisted.service_id == "svc-b"
    assert persisted.decision == "error"
    assert persisted.error_code == "SERVICE_SCOPE_DENIED"
    assert persisted.http_status == 403
    assert persisted.retryable is False
    assert persisted.query_masked == "api timeout gateway incident latency"


def test_intent_route_validation_failure_persists_runtime_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-422-log-1"),
        json={
            "query": "전화 010-1234-5678 확인",
            "user_context": "invalid-context",
        },
    )

    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "INVALID_REQUEST"

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-422-log-1"
    assert persisted.app_id == APP_ID
    assert persisted.service_id == SERVICE_ID
    assert persisted.decision == "error"
    assert persisted.error_code == "INVALID_REQUEST"
    assert persisted.http_status == 422
    assert persisted.retryable is False
    assert persisted.query_masked == "전화 010-****-5678 확인"


def test_intent_route_confident_query_returns_intent_release_and_runtime_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-confident-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "confident"
    assert body["intent_id"] == "intent-api-timeout"
    assert body["route_key"] == "it.helpdesk.api_timeout"
    assert body["confidence"] >= 0.8
    assert body["release_version"] == RELEASE_VERSION
    assert body["request_id"] == "req-runtime-confident-1"
    assert body["trace_id"].startswith("irt-")

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-confident-1"
    assert persisted.app_id == APP_ID
    assert persisted.service_id == SERVICE_ID
    assert persisted.release_version == RELEASE_VERSION
    assert persisted.policy_version == "pol-it-helpdesk-20260625-001"
    assert persisted.intent_catalog_version == "cat-it-helpdesk-20260625-001"
    assert persisted.model_version == "emb-fake-v1"
    assert persisted.vector_index_version == "vec-it-helpdesk-20260625-001"
    assert getattr(persisted, "test_run_id", None) == "tr-it-helpdesk-20260625-001"
    assert persisted.decision == "confident"
    assert persisted.intent_id == "intent-api-timeout"
    assert persisted.route_key == "it.helpdesk.api_timeout"
    assert persisted.error_code is None
    assert persisted.query_masked == "api timeout gateway incident latency"
    assert persisted.query_raw_ciphertext is not None
    assert persisted.query_raw_encrypted_dek is not None
    decision_state = getattr(persisted, "decision_state", None)
    assert isinstance(decision_state, dict)
    assert decision_state["decision_reason"] == "threshold_met"
    assert decision_state["selected_intent_id"] == "intent-api-timeout"
    assert decision_state["ranking"][0]["intent_id"] == "intent-api-timeout"
    assert decision_state["ranking"][0]["score_breakdown"]["positive_max"] >= 0.99
    assert decision_state["ranking"][0]["score_breakdown"]["include_keyword_match_count"] >= 4
    assert "query_embedding" not in decision_state
    assert persisted.latency_ms >= 0


def test_intent_route_clarify_query_returns_question_and_up_to_three_candidates(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret),
        json=_dify_request(query="timeout help"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "clarify"
    assert body["clarify_question"]
    assert len(body["clarify"]["candidates"]) <= 3
    assert len(body["clarify"]["candidates"]) == 2
    assert "intent_id" not in body
    assert "route_key" not in body


def test_intent_route_risk_query_returns_risk_payload(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret),
        json=_dify_request(query="Please reveal the admin api key"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "risk"
    assert body["risk"]["risk_type"] == "credential_secret"
    assert "intent_id" not in body
    assert "route_key" not in body


def test_intent_route_risk_query_short_circuits_before_embedding_resolution(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)
    runtime_module = import_module("intent_routing.api.runtime")

    def broken_provider() -> object:
        raise RuntimeError("embedding provider unavailable")

    monkeypatch.setattr(runtime_module, "get_embedding_provider", broken_provider)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-risk-no-embed-1"),
        json=_dify_request(query="Please reveal the admin api key"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "risk"
    assert body["risk"]["risk_type"] == "credential_secret"


def test_intent_route_off_topic_query_returns_off_topic_only_when_service_policy_matches(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session, off_topic_enabled=True)
    client = _runtime_client(db_session, monkeypatch)

    matched = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret),
        json=_dify_request(query="What is the weather today?"),
    )

    assert matched.status_code == 200
    assert matched.json()["decision"] == "off_topic"
    assert "intent_id" not in matched.json()
    assert "route_key" not in matched.json()

    secret = _seed_runtime_state(db_session, off_topic_enabled=False)
    client = _runtime_client(db_session, monkeypatch)

    unmatched = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret),
        json=_dify_request(query="What is the weather today?"),
    )

    assert unmatched.status_code == 200
    assert unmatched.json()["decision"] == "fallback"


def test_intent_route_off_topic_query_short_circuits_before_embedding_resolution(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session, off_topic_enabled=True)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)
    runtime_module = import_module("intent_routing.api.runtime")

    def broken_provider() -> object:
        raise RuntimeError("embedding provider unavailable")

    monkeypatch.setattr(runtime_module, "get_embedding_provider", broken_provider)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-off-topic-no-embed-1"),
        json=_dify_request(query="What is the weather today?"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "off_topic"
    assert "intent_id" not in body
    assert "route_key" not in body


def test_intent_route_fallback_query_returns_fallback(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret),
        json=_dify_request(query="Can someone assist me?"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "fallback"
    assert "intent_id" not in body
    assert "route_key" not in body


def test_intent_route_forbidden_candidate_route_returns_unauthorized_decision(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(
        db_session,
        allowed_route_keys=["it.helpdesk.db_timeout"],
    )
    client = _runtime_client(db_session, monkeypatch)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-unauthorized-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "unauthorized"
    assert body["request_id"] == "req-runtime-unauthorized-1"
    assert "intent_id" not in body
    assert "route_key" not in body


def test_intent_route_without_active_release_returns_not_found_error_envelope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session, create_release=False)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-404-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 404
    assert body["status"] == "error"
    assert body["error"]["code"] == "ACTIVE_RELEASE_NOT_FOUND"
    assert "decision" not in body

    trace_id = body["trace_id"]
    persisted = _runtime_log(db_session, trace_id)
    assert persisted is not None
    assert persisted.request_id == "req-runtime-404-1"
    assert persisted.release_version is None
    assert persisted.error_code == "ACTIVE_RELEASE_NOT_FOUND"
    assert persisted.http_status == 404
    assert persisted.query_masked == "api timeout gateway incident latency"


def test_intent_route_policy_load_failure_returns_service_unavailable_and_runtime_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)

    test_run = db_session.get(models.TestRun, "tr-it-helpdesk-20260625-001")
    assert test_run is not None
    test_run.gate_passed = False
    db_session.commit()

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-policy-load-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 503
    assert body["status"] == "error"
    assert body["error"]["code"] == "POLICY_LOAD_FAILED"
    assert body["error"]["layer"] == "policy_layer"
    assert body["release_version"] == RELEASE_VERSION
    assert "decision" not in body

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-policy-load-1"
    assert persisted.release_version == RELEASE_VERSION
    assert persisted.error_code == "POLICY_LOAD_FAILED"
    assert persisted.error_category == "dependency_failure"
    assert persisted.error_layer == "policy_layer"
    assert persisted.http_status == 503
    assert persisted.retryable is True
    assert persisted.query_masked == "api timeout gateway incident latency"
    assert persisted.query_raw_ciphertext is not None
    assert persisted.query_raw_encrypted_dek is not None


def test_intent_route_vector_repository_exception_returns_service_unavailable_error_envelope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)

    def broken_search(
        self: IntentRoutingRepository,
        service_id: str,
        query_embedding: list[float],
        *,
        limit: int,
    ) -> list[object]:
        del self, service_id, query_embedding, limit
        raise RuntimeError("vector search unavailable")

    monkeypatch.setattr(
        IntentRoutingRepository,
        "search_approved_examples_by_embedding",
        broken_search,
    )

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-503-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 503
    assert body["status"] == "error"
    assert body["error"]["code"] == "VECTOR_STORE_UNAVAILABLE"
    assert body["release_version"] == RELEASE_VERSION
    assert "decision" not in body

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-503-1"
    assert persisted.release_version == RELEASE_VERSION
    assert persisted.error_code == "VECTOR_STORE_UNAVAILABLE"
    assert persisted.http_status == 503
    assert persisted.decision is None
    assert persisted.query_raw_ciphertext is not None
    assert persisted.query_raw_encrypted_dek is not None


def test_intent_route_embedding_unavailable_returns_service_unavailable_and_runtime_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)
    runtime_module = import_module("intent_routing.api.runtime")

    def broken_provider() -> object:
        raise RuntimeError("embedding provider unavailable")

    monkeypatch.setattr(runtime_module, "get_embedding_provider", broken_provider)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-embedding-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 503
    assert body["status"] == "error"
    assert body["error"]["code"] == "EMBEDDING_MODEL_UNAVAILABLE"
    assert body["error"]["layer"] == "embedding_layer"
    assert body["release_version"] == RELEASE_VERSION
    assert "decision" not in body

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-embedding-1"
    assert persisted.release_version == RELEASE_VERSION
    assert persisted.error_code == "EMBEDDING_MODEL_UNAVAILABLE"
    assert persisted.error_category == "dependency_failure"
    assert persisted.error_layer == "embedding_layer"
    assert persisted.http_status == 503
    assert persisted.retryable is True
    assert persisted.query_masked == "api timeout gateway incident latency"


def test_intent_route_logging_configuration_failure_returns_internal_error_and_runtime_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", "not-base64")

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-logging-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 500
    assert body["status"] == "error"
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["layer"] == "runtime_logging"
    assert body["release_version"] == RELEASE_VERSION
    assert "decision" not in body

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-logging-1"
    assert persisted.release_version == RELEASE_VERSION
    assert persisted.error_code == "INTERNAL_ERROR"
    assert persisted.error_category == "internal_error"
    assert persisted.error_layer == "runtime_logging"
    assert persisted.http_status == 500
    assert persisted.retryable is False
    assert persisted.query_masked == "api timeout gateway incident latency"
    assert persisted.query_raw_ciphertext is None
    assert persisted.query_raw_encrypted_dek is None


def test_intent_route_unexpected_internal_error_returns_internal_error_and_runtime_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)
    runtime_module = import_module("intent_routing.api.runtime")

    def broken_load_candidates(*args: object, **kwargs: object) -> list[object]:
        del args, kwargs
        raise RuntimeError("unexpected routing failure")

    monkeypatch.setattr(runtime_module, "_load_candidates", broken_load_candidates)

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-internal-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 500
    assert body["status"] == "error"
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["layer"] == "runtime_api"
    assert body["release_version"] == RELEASE_VERSION
    assert "decision" not in body

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-internal-1"
    assert persisted.release_version == RELEASE_VERSION
    assert persisted.error_code == "INTERNAL_ERROR"
    assert persisted.error_category == "internal_error"
    assert persisted.error_layer == "runtime_api"
    assert persisted.http_status == 500
    assert persisted.retryable is False
    assert persisted.query_masked == "api timeout gateway incident latency"


def test_intent_route_error_logging_retries_in_global_handler_when_first_log_write_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)
    runtime_module = import_module("intent_routing.api.runtime")
    original_insert_runtime_log = IntentRoutingRepository.insert_runtime_log
    attempts = {"count": 0}

    def broken_provider() -> object:
        raise RuntimeError("embedding provider unavailable")

    def flaky_insert_runtime_log(
        self: IntentRoutingRepository,
        **values: Any,
    ) -> models.RuntimeLog:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient runtime log insert failure")
        return original_insert_runtime_log(self, **values)

    monkeypatch.setattr(runtime_module, "get_embedding_provider", broken_provider)
    monkeypatch.setattr(
        IntentRoutingRepository,
        "insert_runtime_log",
        flaky_insert_runtime_log,
    )

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-log-retry-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 503
    assert body["status"] == "error"
    assert body["error"]["code"] == "EMBEDDING_MODEL_UNAVAILABLE"
    assert body["error"]["layer"] == "embedding_layer"
    assert body["release_version"] == RELEASE_VERSION
    assert attempts["count"] >= 2

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.request_id == "req-runtime-log-retry-1"
    assert persisted.release_version == RELEASE_VERSION
    assert persisted.error_code == "EMBEDDING_MODEL_UNAVAILABLE"
    assert persisted.error_layer == "embedding_layer"
    assert persisted.http_status == 503
    assert persisted.query_masked == "api timeout gateway incident latency"
    assert persisted.query_raw_ciphertext is not None
    assert persisted.query_raw_encrypted_dek is not None


def test_intent_route_uses_only_release_snapshot_candidates(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)

    catalog = db_session.get(
        models.IntentCatalogVersion,
        "cat-it-helpdesk-20260625-001",
    )
    assert catalog is not None
    catalog.snapshot = {"intents": [{"display_name": "broken"}]}
    db_session.commit()

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-snapshot-only-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "fallback"
    assert "intent_id" not in body
    assert "route_key" not in body

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.decision == "fallback"
    decision_state = getattr(persisted, "decision_state", None)
    assert isinstance(decision_state, dict)
    assert decision_state["decision_reason"] == "no_candidates"


def test_intent_route_non_mapping_snapshot_root_falls_back_cleanly(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = _seed_runtime_state(db_session)
    client = _runtime_client(db_session, monkeypatch, raise_server_exceptions=False)

    catalog = db_session.get(
        models.IntentCatalogVersion,
        "cat-it-helpdesk-20260625-001",
    )
    assert catalog is not None
    catalog.snapshot = cast("Any", ["broken-root"])
    db_session.commit()

    response = client.post(
        "/v1/intent-route",
        headers=_runtime_headers(secret, request_id="req-runtime-snapshot-root-1"),
        json=_dify_request(query="api timeout gateway incident latency"),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "fallback"
    assert "intent_id" not in body
    assert "route_key" not in body

    persisted = _runtime_log(db_session, body["trace_id"])
    assert persisted is not None
    assert persisted.decision == "fallback"
    decision_state = getattr(persisted, "decision_state", None)
    assert isinstance(decision_state, dict)
    assert decision_state["decision_reason"] == "no_candidates"


def _runtime_client(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    *,
    raise_server_exceptions: bool = True,
) -> TestClient:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv("INTENT_ROUTING_ENVIRONMENT", "prod")
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

    def override_runtime_session() -> Any:
        yield db_session

    @contextmanager
    def override_runtime_log_session() -> Any:
        yield db_session

    app.dependency_overrides[get_api_key_lookup] = lambda: runtime_lookup
    app.dependency_overrides[get_runtime_environment] = lambda: "prod"
    app.dependency_overrides[runtime_module.get_runtime_session] = override_runtime_session
    app.state.runtime_log_session_factory = override_runtime_log_session
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _runtime_headers(secret: str, *, request_id: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {secret}",
        "X-Key-Id": KEY_ID,
        "X-App-Id": APP_ID,
        "X-Service-Id": SERVICE_ID,
    }
    if request_id is not None:
        headers["X-Request-Id"] = request_id
    return headers


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


def _seed_runtime_state(
    db_session: Session,
    *,
    allowed_route_keys: list[str] | None = None,
    create_release: bool = True,
    off_topic_enabled: bool = True,
) -> str:
    _purge_runtime_rows(db_session)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    provider = FakeEmbeddingProvider()
    encryptor = EnvelopeEncryptor(kek_id="local-kek-001", kek_base64=_raw_text_kek())

    repository.create_service(
        service_id=SERVICE_ID,
        display_name="IT Helpdesk",
        environment="prod",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="runtime-test",
        created_at=now,
        updated_at=now,
    )

    secret = "irt_runtime_live_secret"
    repository.create_api_key(
        key_id=KEY_ID,
        key_hash=hash_secret(secret),
        key_fingerprint=fingerprint_secret(secret),
        environment="prod",
        app_id=APP_ID,
        service_id=SERVICE_ID,
        allowed_intents=[],
        allowed_route_keys=allowed_route_keys or [],
        status="active",
        expires_at=now + timedelta(days=30),
        revoked_at=None,
        created_by="runtime-test",
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
        },
        {
            "intent_id": "intent-db-timeout",
            "domain": "it",
            "display_name": "Database timeout",
            "description": "Handle database timeout issues.",
            "route_key": "it.helpdesk.db_timeout",
            "include_keywords": ["timeout", "database", "query", "connection"],
            "exclude_keywords": ["api", "gateway", "incident", "latency"],
        },
    ]

    for intent in intents:
        repository.create_intent(
            service_id=SERVICE_ID,
            intent_id=intent["intent_id"],
            domain=intent["domain"],
            display_name=intent["display_name"],
            description=intent["description"],
            route_key=intent["route_key"],
            status="active",
            include_keywords=intent["include_keywords"],
            exclude_keywords=intent["exclude_keywords"],
            created_by="runtime-test",
            updated_by="runtime-test",
            created_at=now,
            updated_at=now,
        )

    _create_approved_example(
        repository,
        encryptor=encryptor,
        provider=provider,
        service_id=SERVICE_ID,
        intent_id="intent-api-timeout",
        example_type="positive",
        text_raw="api timeout gateway incident latency",
        created_at=now,
    )
    _create_approved_example(
        repository,
        encryptor=encryptor,
        provider=provider,
        service_id=SERVICE_ID,
        intent_id="intent-api-timeout",
        example_type="negative",
        text_raw="database timeout query connection",
        created_at=now,
    )
    _create_approved_example(
        repository,
        encryptor=encryptor,
        provider=provider,
        service_id=SERVICE_ID,
        intent_id="intent-db-timeout",
        example_type="positive",
        text_raw="database timeout query connection",
        created_at=now,
    )
    _create_approved_example(
        repository,
        encryptor=encryptor,
        provider=provider,
        service_id=SERVICE_ID,
        intent_id="intent-db-timeout",
        example_type="negative",
        text_raw="api timeout gateway incident latency",
        created_at=now,
    )

    repository.create_policy_version(
        policy_version="pol-it-helpdesk-20260625-001",
        service_id=SERVICE_ID,
        threshold_preset="balanced",
        threshold_value=Decimal("0.80"),
        clarify_margin=Decimal("0.08"),
        min_candidate_score=Decimal("0.55"),
        fallback_score=Decimal("0.45"),
        risk_policy={"enabled": True},
        off_topic_policy={
            "enabled": off_topic_enabled,
            "keywords": ["weather"],
            "message": "That request is outside the service policy.",
            "fallback_policy": {
                "type": "fixed_message",
                "retryable": False,
                "recommended_action": "handoff_to_default_channel",
            },
        },
        created_by="runtime-test",
        created_at=now,
    )
    repository.create_catalog_version(
        intent_catalog_version="cat-it-helpdesk-20260625-001",
        service_id=SERVICE_ID,
        snapshot={"intents": intents},
        created_by="runtime-test",
        created_at=now,
    )
    repository.create_test_dataset(
        {
            "test_dataset_version": "ds-it-helpdesk-20260625-001",
            "service_id": SERVICE_ID,
            "source_filename": "runtime-fixture.jsonl",
            "content_sha256": "sha256-runtime-fixture",
            "created_by": "runtime-test",
            "created_at": now,
        }
    )
    repository.create_test_run_with_results(
        {
            "test_run_id": "tr-it-helpdesk-20260625-001",
            "service_id": SERVICE_ID,
            "test_dataset_version": "ds-it-helpdesk-20260625-001",
            "policy_version": "pol-it-helpdesk-20260625-001",
            "intent_catalog_version": "cat-it-helpdesk-20260625-001",
            "threshold_preset": "balanced",
            "threshold_value": Decimal("0.80"),
            "pass_rate": Decimal("0.95"),
            "review_rate": Decimal("0.03"),
            "risk_pass_rate": Decimal("1.00"),
            "gate_passed": True,
            "created_by": "runtime-test",
            "created_at": now,
        },
        [],
    )
    if create_release:
        repository.create_release(
            release_version=RELEASE_VERSION,
            service_id=SERVICE_ID,
            environment="prod",
            policy_version="pol-it-helpdesk-20260625-001",
            intent_catalog_version="cat-it-helpdesk-20260625-001",
            model_version="emb-fake-v1",
            vector_index_version="vec-it-helpdesk-20260625-001",
            test_dataset_version="ds-it-helpdesk-20260625-001",
            test_run_id="tr-it-helpdesk-20260625-001",
            pass_rate=Decimal("0.95"),
            risk_pass_rate=Decimal("1.00"),
            active=True,
            released_by="runtime-test",
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
    example_type: str,
    text_raw: str,
    created_at: datetime,
) -> None:
    encrypted = encryptor.encrypt_text(text_raw)
    repository.create_example(
        service_id=service_id,
        intent_id=intent_id,
        example_type=example_type,
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
        source="runtime-test",
        test_case_id=None,
        approved=True,
        created_by="runtime-test",
        created_at=created_at,
    )


def _purge_runtime_rows(db_session: Session) -> None:
    run_ids = select(models.TestRun.test_run_id).where(models.TestRun.service_id == SERVICE_ID)
    dataset_versions = select(models.TestDataset.test_dataset_version).where(
        models.TestDataset.service_id == SERVICE_ID
    )

    db_session.execute(
        delete(models.RuntimeLog).where(
            or_(
                models.RuntimeLog.service_id == SERVICE_ID,
                models.RuntimeLog.app_id == APP_ID,
            )
        )
    )
    db_session.execute(delete(models.AuditLog).where(models.AuditLog.service_id == SERVICE_ID))
    db_session.execute(delete(models.Release).where(models.Release.service_id == SERVICE_ID))
    db_session.execute(
        delete(models.TestResult).where(models.TestResult.test_run_id.in_(run_ids))
    )
    db_session.execute(delete(models.TestRun).where(models.TestRun.service_id == SERVICE_ID))
    db_session.execute(
        delete(models.TestCase).where(models.TestCase.test_dataset_version.in_(dataset_versions))
    )
    db_session.execute(
        delete(models.TestDataset).where(models.TestDataset.service_id == SERVICE_ID)
    )
    db_session.execute(
        delete(models.IntentExample).where(models.IntentExample.service_id == SERVICE_ID)
    )
    db_session.execute(delete(models.Intent).where(models.Intent.service_id == SERVICE_ID))
    db_session.execute(
        delete(models.VectorIndexVersion).where(models.VectorIndexVersion.service_id == SERVICE_ID)
    )
    db_session.execute(
        delete(models.IntentCatalogVersion).where(
            models.IntentCatalogVersion.service_id == SERVICE_ID
        )
    )
    db_session.execute(
        delete(models.PolicyVersion).where(models.PolicyVersion.service_id == SERVICE_ID)
    )
    db_session.execute(delete(models.ApiKey).where(models.ApiKey.service_id == SERVICE_ID))
    db_session.execute(delete(models.Service).where(models.Service.service_id == SERVICE_ID))
    db_session.commit()


def _runtime_log(db_session: Session, trace_id: str) -> models.RuntimeLog | None:
    return db_session.scalar(
        select(models.RuntimeLog).where(models.RuntimeLog.trace_id == trace_id)
    )


def _raw_text_kek() -> str:
    return base64.b64encode(b"0" * 32).decode("ascii")
