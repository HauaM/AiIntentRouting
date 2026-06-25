from __future__ import annotations

import base64
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.db import models
from intent_routing.main import create_app
from intent_routing.security.encryption import EncryptedText, EnvelopeEncryptor


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


def _intent_payload(route_key: str = "it.api_timeout.manual_lookup") -> dict[str, object]:
    suffix = uuid4().hex
    return {
        "intent_id": f"intent-{suffix}",
        "domain": "it",
        "display_name": "API timeout manual lookup",
        "description": "Help users look up API timeout incidents.",
        "route_key": route_key,
        "include_keywords": ["timeout", "api"],
        "exclude_keywords": ["password"],
    }


def _example_payload(text: str = "전화 010-1234-5678 확인") -> dict[str, object]:
    return {
        "example_type": "positive",
        "text_raw": text,
        "source": "admin-test",
        "test_case_id": None,
    }


def _developer_headers(service_id: str) -> dict[str, str]:
    return _admin_headers(
        **{
            "X-Actor-Id": "developer-user",
            "X-Actor-Roles": "service_developer",
            "X-Service-Scope": service_id,
        }
    )


def _raw_text_kek() -> str:
    return base64.b64encode(b"0" * 32).decode("ascii")


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


def _create_intent(
    client: TestClient,
    service_id: str,
    *,
    headers: dict[str, str] | None = None,
    route_key: str = "it.api_timeout.manual_lookup",
) -> dict[str, object]:
    response = client.post(
        f"/admin/v1/services/{service_id}/intents",
        headers=headers or _admin_headers(),
        json=_intent_payload(route_key),
    )
    assert response.status_code == 201
    return cast("dict[str, object]", response.json())


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


def test_create_and_list_draft_intents(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)

    created = _create_intent(client, service_id)
    list_response = client.get(
        f"/admin/v1/services/{service_id}/intents",
        headers=_admin_headers(),
    )

    assert created["status"] == "draft"
    assert created["route_key"] == "it.api_timeout.manual_lookup"
    assert list_response.status_code == 200
    assert [intent["intent_id"] for intent in list_response.json()] == [
        created["intent_id"]
    ]
    persisted = db_session.scalar(
        select(models.Intent).where(
            models.Intent.service_id == service_id,
            models.Intent.intent_id == created["intent_id"],
        )
    )
    assert persisted is not None
    assert persisted.status == "draft"


def test_duplicate_route_key_within_service_returns_conflict(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session, raise_server_exceptions=False)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    _create_intent(client, service_id)

    duplicate = _intent_payload("it.api_timeout.manual_lookup")
    response = client.post(
        f"/admin/v1/services/{service_id}/intents",
        headers=_admin_headers(),
        json=duplicate,
    )

    body = response.json()
    assert response.status_code == 409
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_REQUEST"


def test_invalid_route_key_returns_validation_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)

    payload = _intent_payload("it.api_timeout.prod")
    response = client.post(
        f"/admin/v1/services/{service_id}/intents",
        headers=_admin_headers(),
        json=payload,
    )

    assert response.status_code == 422


def test_patch_intent_updates_catalog_fields(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    created = _create_intent(client, service_id)

    response = client.patch(
        f"/admin/v1/services/{service_id}/intents/{created['intent_id']}",
        headers=_admin_headers(),
        json={
            "display_name": "Updated display name",
            "status": "active",
            "route_key": "it.api_timeout.mobile_lookup",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["display_name"] == "Updated display name"
    assert body["status"] == "active"
    assert body["route_key"] == "it.api_timeout.mobile_lookup"


def test_patch_intent_rejects_explicit_null_fields_without_mutating_db(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    created = _create_intent(client, service_id)

    response = client.patch(
        f"/admin/v1/services/{service_id}/intents/{created['intent_id']}",
        headers=_admin_headers(),
        json={
            "display_name": None,
            "route_key": None,
            "include_keywords": None,
        },
    )

    body = response.json()
    assert response.status_code == 422
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert "detail" not in body
    persisted = db_session.scalar(
        select(models.Intent).where(
            models.Intent.service_id == service_id,
            models.Intent.intent_id == created["intent_id"],
        )
    )
    assert persisted is not None
    assert persisted.display_name == created["display_name"]
    assert persisted.route_key == created["route_key"]
    assert persisted.include_keywords == created["include_keywords"]


def test_create_example_encrypts_raw_text_masks_text_and_defaults_unapproved(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_ID", "test-kek")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    intent = _create_intent(client, service_id)
    raw_text = "전화 010-1234-5678 확인"

    response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
        json=_example_payload(raw_text),
    )

    body = response.json()
    assert response.status_code == 201
    assert body["text_masked"] == "전화 010-****-5678 확인"
    assert body["approved"] is False
    assert body["embedding"] is None
    persisted = db_session.get(models.IntentExample, body["example_id"])
    assert persisted is not None
    assert persisted.text_masked == "전화 010-****-5678 확인"
    assert persisted.approved is False
    assert persisted.embedding is None
    assert raw_text.encode("utf-8") not in persisted.text_raw_ciphertext
    decrypted = EnvelopeEncryptor(
        kek_id="test-kek",
        kek_base64=_raw_text_kek(),
    ).decrypt_text(
        EncryptedText(
            ciphertext=persisted.text_raw_ciphertext,
            encrypted_dek=persisted.text_raw_encrypted_dek,
            key_id=persisted.text_raw_key_id,
            iv=persisted.text_raw_iv,
            auth_tag=persisted.text_raw_auth_tag,
            algorithm=persisted.text_raw_algorithm,
            encrypted_dek_iv=persisted.text_raw_encrypted_dek_iv,
            encrypted_dek_auth_tag=persisted.text_raw_encrypted_dek_auth_tag,
        )
    )
    assert decrypted == raw_text
    audit_log = db_session.scalar(
        select(models.AuditLog).where(
            models.AuditLog.event_type == "example.created",
            models.AuditLog.target_id == body["example_id"],
        )
    )
    assert audit_log is not None
    assert audit_log.service_id == service_id
    assert audit_log.after_state is not None
    assert raw_text not in json.dumps(audit_log.after_state, sort_keys=True)


def test_malformed_example_request_returns_sanitized_validation_envelope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    intent = _create_intent(client, service_id)
    raw_text = "전화 010-1234-5678 확인"

    response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
        json={
            "example_type": "positive",
            "text_raw": raw_text,
        },
    )

    body = response.json()
    assert response.status_code == 422
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert "detail" not in body
    assert "010-1234-5678" not in response.text
    assert raw_text not in response.text


def test_list_examples_and_approve_example(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    intent = _create_intent(client, service_id)
    create_response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
        json=_example_payload(),
    )
    example_id = create_response.json()["example_id"]

    list_response = client.get(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
    )
    approve_response = client.patch(
        f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
        headers=_admin_headers(),
    )

    assert list_response.status_code == 200
    assert [example["example_id"] for example in list_response.json()] == [example_id]
    assert approve_response.status_code == 200
    assert approve_response.json()["approved"] is True
    persisted = db_session.get(models.IntentExample, example_id)
    assert persisted is not None
    assert persisted.approved is True


def test_only_matching_service_developer_can_modify_service_catalog(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    other_service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    _create_service(client, other_service_id)

    allowed_response = client.post(
        f"/admin/v1/services/{service_id}/intents",
        headers=_developer_headers(service_id),
        json=_intent_payload(),
    )
    denied_response = client.post(
        f"/admin/v1/services/{other_service_id}/intents",
        headers=_developer_headers(service_id),
        json=_intent_payload("insurance.claim.guide"),
    )

    assert allowed_response.status_code == 201
    assert denied_response.status_code == 403
    assert denied_response.json()["status"] == "error"
    assert denied_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
