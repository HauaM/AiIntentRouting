from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.db import models
from intent_routing.main import create_app


def _admin_headers(**overrides: str) -> dict[str, str]:
    headers = {
        "X-Admin-Token": "local-admin-token",
        "X-Actor-Id": "admin-user",
        "X-Actor-Roles": "system_admin",
    }
    headers.update(overrides)
    return headers


def _client(
    db_session: Session,
    *,
    raise_server_exceptions: bool = True,
) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _service_payload(service_id: str) -> dict[str, object]:
    return {
        "service_id": service_id,
        "display_name": "Admin API test service",
        "environment": "test",
        "default_threshold_preset": "balanced",
        "max_input_tokens": 256,
    }


def _api_key_payload(service_id: str) -> dict[str, object]:
    return {
        "service_id": service_id,
        "environment": "test",
        "app_id": f"app-{uuid4().hex}",
        "allowed_intents": ["intent-a"],
        "allowed_route_keys": ["route.a"],
        "expires_in_days": 90,
    }


def _create_service(
    client: TestClient,
    service_id: str,
    *,
    headers: dict[str, str] | None = None,
) -> None:
    response = client.post(
        "/admin/v1/services",
        headers=headers or _admin_headers(),
        json=_service_payload(service_id),
    )
    assert response.status_code == 201


def test_admin_can_create_service_and_api_key(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-admin-{uuid4().hex}"

    service_response = client.post(
        "/admin/v1/services",
        headers=_admin_headers(),
        json=_service_payload(service_id),
    )
    assert service_response.status_code == 201

    key_response = client.post(
        "/admin/v1/api-keys",
        headers=_admin_headers(),
        json=_api_key_payload(service_id),
    )

    body = key_response.json()
    assert key_response.status_code == 201
    assert body["key_id"].startswith("key_live_")
    assert body["api_key"].startswith("irt_")
    assert body["api_key_displayed_once"] is True
    persisted_key = db_session.get(models.ApiKey, body["key_id"])
    assert persisted_key is not None
    expected_expiry = datetime.now(UTC) + timedelta(days=90)
    assert persisted_key.expires_at == pytest.approx(
        expected_expiry,
        abs=timedelta(seconds=10),
    )


def test_revoke_endpoint_persists_revoked_status_and_audit_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-admin-{uuid4().hex}"
    _create_service(client, service_id)
    key_response = client.post(
        "/admin/v1/api-keys",
        headers=_admin_headers(),
        json=_api_key_payload(service_id),
    )
    key_id = key_response.json()["key_id"]

    response = client.post(
        f"/admin/v1/api-keys/{key_id}:revoke",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    persisted_key = db_session.get(models.ApiKey, key_id)
    assert persisted_key is not None
    assert persisted_key.status == "revoked"
    assert persisted_key.revoked_at is not None
    audit_log = db_session.scalar(
        select(models.AuditLog).where(
            models.AuditLog.event_type == "api_key.revoked",
            models.AuditLog.target_id == key_id,
        )
    )
    assert audit_log is not None
    assert audit_log.actor_id == "admin-user"
    assert audit_log.target_type == "api_key"


def test_duplicate_service_returns_conflict_and_session_recovers(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session, raise_server_exceptions=False)
    service_id = f"svc-admin-{uuid4().hex}"
    _create_service(client, service_id)

    duplicate_response = client.post(
        "/admin/v1/services",
        headers=_admin_headers(),
        json=_service_payload(service_id),
    )

    assert duplicate_response.status_code == 409
    duplicate_body = duplicate_response.json()
    assert duplicate_body["status"] == "error"
    assert duplicate_body["error"]["code"] == "INVALID_REQUEST"
    assert "detail" not in duplicate_body

    recovery_response = client.post(
        "/admin/v1/services",
        headers=_admin_headers(),
        json=_service_payload(f"svc-admin-{uuid4().hex}"),
    )
    assert recovery_response.status_code == 201


def test_missing_admin_token_returns_error_envelope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    headers = _admin_headers()
    headers.pop("X-Admin-Token")

    response = client.post(
        "/admin/v1/services",
        headers=headers,
        json=_service_payload(f"svc-admin-{uuid4().hex}"),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["status"] == "error"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"
    assert "trace_id" in body


def test_blank_configured_admin_token_returns_error_envelope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", " ")
    client = _client(db_session)

    response = client.post(
        "/admin/v1/services",
        headers=_admin_headers(**{"X-Admin-Token": " "}),
        json=_service_payload(f"svc-admin-{uuid4().hex}"),
    )

    body = response.json()
    assert response.status_code == 401
    assert body["status"] == "error"
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"


def test_non_system_admin_role_cannot_create_service_or_key(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-admin-{uuid4().hex}"
    developer_headers = _admin_headers(**{"X-Actor-Roles": "service_developer"})

    service_response = client.post(
        "/admin/v1/services",
        headers=developer_headers,
        json=_service_payload(service_id),
    )
    key_response = client.post(
        "/admin/v1/api-keys",
        headers=developer_headers,
        json=_api_key_payload(service_id),
    )

    assert service_response.status_code == 403
    assert service_response.json()["status"] == "error"
    assert key_response.status_code == 403
    assert key_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_api_key_raw_secret_is_not_persisted_in_db_or_audit_log(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-admin-{uuid4().hex}"
    _create_service(client, service_id)

    key_response = client.post(
        "/admin/v1/api-keys",
        headers=_admin_headers(),
        json=_api_key_payload(service_id),
    )
    body = key_response.json()
    raw_api_key = body["api_key"]

    persisted_key = db_session.get(models.ApiKey, body["key_id"])
    assert persisted_key is not None
    assert persisted_key.key_hash != raw_api_key
    assert raw_api_key not in persisted_key.key_hash
    assert persisted_key.key_fingerprint != raw_api_key
    assert raw_api_key not in persisted_key.key_fingerprint

    revoke_response = client.post(
        f"/admin/v1/api-keys/{body['key_id']}:revoke",
        headers=_admin_headers(),
    )
    assert revoke_response.status_code == 200
    audit_logs = list(
        db_session.scalars(
            select(models.AuditLog).where(models.AuditLog.target_id == body["key_id"])
        )
    )
    assert audit_logs
    for audit_log in audit_logs:
        serialized_before_state = json.dumps(audit_log.before_state, sort_keys=True)
        serialized_after_state = json.dumps(audit_log.after_state, sort_keys=True)
        assert raw_api_key not in serialized_before_state
        assert raw_api_key not in serialized_after_state
