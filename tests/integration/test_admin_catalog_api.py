from __future__ import annotations

import base64
import json
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.api.admin import get_admin_session
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.embedding.fake import FakeEmbeddingProvider
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


def _policy_version_payload() -> dict[str, object]:
    return {
        "threshold_preset": "balanced",
        "clarify_margin": 0.08,
        "min_candidate_score": 0.55,
        "fallback_score": 0.45,
        "risk_policy": {"enabled": True},
        "off_topic_policy": {
            "enabled": True,
            "keywords": ["날씨", "점심"],
            "message": "서비스 범위 밖 문의입니다.",
            "fallback_policy": {"type": "fixed_message", "retryable": False},
        },
    }


def _sprint0_csv_text() -> str:
    return (
        Path(__file__).resolve().parents[1] / "fixtures" / "sprint0_cases.csv"
    ).read_text()


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


def _seed_csv_runner_state(
    db_session: Session,
    client: TestClient,
    service_id: str,
) -> tuple[str, str]:
    _create_service(client, service_id)
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    provider = FakeEmbeddingProvider()
    encryptor = EnvelopeEncryptor(kek_id="test-kek", kek_base64=_raw_text_kek())
    intent_snapshot = {
        "intent_id": "it_api_timeout",
        "domain": "it",
        "display_name": "API timeout incident",
        "description": "Handle API timeout and server error issues.",
        "route_key": "it.api_timeout.manual_lookup",
        "include_keywords": ["api", "timeout", "500", "에러"],
        "exclude_keywords": [],
    }
    repository.create_intent(
        service_id=service_id,
        intent_id=intent_snapshot["intent_id"],
        domain=intent_snapshot["domain"],
        display_name=intent_snapshot["display_name"],
        description=intent_snapshot["description"],
        route_key=intent_snapshot["route_key"],
        status="active",
        include_keywords=intent_snapshot["include_keywords"],
        exclude_keywords=intent_snapshot["exclude_keywords"],
        created_by="integration-test",
        updated_by="integration-test",
        created_at=now,
        updated_at=now,
    )
    for text in ("API Timeout이 발생해요",):
        encrypted = encryptor.encrypt_text(text)
        repository.create_example(
            service_id=service_id,
            intent_id="it_api_timeout",
            example_type="positive",
            text_raw_ciphertext=encrypted.ciphertext,
            text_raw_encrypted_dek=encrypted.encrypted_dek,
            text_raw_encrypted_dek_iv=encrypted.encrypted_dek_iv,
            text_raw_encrypted_dek_auth_tag=encrypted.encrypted_dek_auth_tag,
            text_raw_key_id=encrypted.key_id,
            text_raw_iv=encrypted.iv,
            text_raw_auth_tag=encrypted.auth_tag,
            text_raw_algorithm=encrypted.algorithm,
            text_masked=text,
            embedding=provider.embed_texts([text], max_tokens=256)[0],
            source="integration-test",
            test_case_id=None,
            approved=True,
            created_by="integration-test",
            created_at=now,
        )
    policy_version = f"pol-{service_id}-001"
    catalog_version = f"cat-{service_id}-001"
    repository.create_policy_version(
        policy_version=policy_version,
        service_id=service_id,
        threshold_preset="balanced",
        threshold_value=Decimal("0.80"),
        clarify_margin=Decimal("0.08"),
        min_candidate_score=Decimal("0.55"),
        fallback_score=Decimal("0.45"),
        risk_policy={"enabled": True},
        off_topic_policy={
            "enabled": True,
            "keywords": ["날씨"],
            "message": "서비스 범위 밖 문의입니다.",
            "fallback_policy": {
                "type": "fixed_message",
                "retryable": False,
                "recommended_action": "handoff_to_default_channel",
            },
        },
        created_by="integration-test",
        created_at=now,
    )
    repository.create_catalog_version(
        intent_catalog_version=catalog_version,
        service_id=service_id,
        snapshot={"intents": [intent_snapshot]},
        created_by="integration-test",
        created_at=now,
    )
    return policy_version, catalog_version


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
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
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


def test_approve_positive_example_generates_fake_embedding_without_bge_import(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    sys.modules.pop("FlagEmbedding", None)
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    intent = _create_intent(client, service_id)
    create_response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
        json=_example_payload("api timeout 문의"),
    )
    example_id = create_response.json()["example_id"]

    approve_response = client.patch(
        f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
        headers=_admin_headers(),
    )

    from intent_routing.embedding.provider import get_embedding_provider

    provider = get_embedding_provider()
    body = approve_response.json()
    persisted = db_session.get(models.IntentExample, example_id)
    assert approve_response.status_code == 200
    assert provider.model_version == "emb-fake-v1"
    assert provider.dimension == 1024
    assert "FlagEmbedding" not in sys.modules
    assert body["approved"] is True
    assert body["embedding"] is not None
    assert len(body["embedding"]) == 1024
    assert persisted is not None
    assert persisted.embedding is not None
    assert len(persisted.embedding) == 1024
    audit_log = db_session.scalar(
        select(models.AuditLog).where(
            models.AuditLog.event_type == "example.approved",
            models.AuditLog.target_id == example_id,
        )
    )
    assert audit_log is not None
    assert audit_log.after_state is not None
    assert audit_log.after_state["embedding"] == {
        "dimension": 1024,
        "stored": True,
    }


def test_approve_negative_example_generates_1024_dimension_embedding(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    intent = _create_intent(client, service_id)
    negative_payload = _example_payload("비밀번호 재설정")
    negative_payload["example_type"] = "negative"
    create_response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
        json=negative_payload,
    )
    example_id = create_response.json()["example_id"]

    approve_response = client.patch(
        f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
        headers=_admin_headers(),
    )

    body = approve_response.json()
    persisted = db_session.get(models.IntentExample, example_id)
    assert approve_response.status_code == 200
    assert body["example_type"] == "negative"
    assert body["approved"] is True
    assert body["embedding"] is not None
    assert len(body["embedding"]) == 1024
    assert persisted is not None
    assert persisted.embedding is not None
    assert len(persisted.embedding) == 1024


def test_exact_search_returns_top_examples_ordered_by_cosine_similarity(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    api_intent = _create_intent(client, service_id)
    password_intent = _create_intent(
        client,
        service_id,
        route_key="it.password_reset.manual_lookup",
    )
    examples: list[str] = []
    for intent, text in (
        (api_intent, "api timeout 문의"),
        (password_intent, "비밀번호 재설정"),
        (api_intent, "오늘 날씨 어때"),
    ):
        create_response = client.post(
            f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
            headers=_admin_headers(),
            json=_example_payload(text),
        )
        example_id = create_response.json()["example_id"]
        examples.append(example_id)
        approve_response = client.patch(
            f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
            headers=_admin_headers(),
        )
        assert approve_response.status_code == 200
    unapproved_response = client.post(
        f"/admin/v1/services/{service_id}/intents/{api_intent['intent_id']}/examples",
        headers=_admin_headers(),
        json=_example_payload("api timeout 문의"),
    )
    assert unapproved_response.status_code == 201

    from intent_routing.embedding.provider import get_embedding_provider

    provider = get_embedding_provider()
    query_embedding = provider.embed_texts(
        ["API Timeout이 발생해요"],
        max_tokens=256,
    )[0]
    results = IntentRoutingRepository(db_session).search_approved_examples_by_embedding(
        service_id,
        query_embedding,
        limit=3,
    )

    assert [str(result.example_id) for result in results] == examples
    assert [result.intent_id for result in results] == [
        api_intent["intent_id"],
        password_intent["intent_id"],
        api_intent["intent_id"],
    ]
    assert results[0].similarity > results[1].similarity > results[2].similarity


def test_exact_search_rejects_invalid_query_inputs(db_session: Session) -> None:
    repository = IntentRoutingRepository(db_session)

    with pytest.raises(ValueError, match="1024"):
        repository.search_approved_examples_by_embedding(
            "svc-catalog",
            [1.0, 0.0],
            limit=1,
        )
    with pytest.raises(ValueError, match="limit"):
        repository.search_approved_examples_by_embedding(
            "svc-catalog",
            [0.0] * 1024,
            limit=0,
        )


def test_approve_example_embeds_masked_text_by_default_without_decrypting_raw(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_texts: list[str] = []

    class CapturingProvider:
        model_version = "emb-test-capture"
        dimension = 1024

        def embed_texts(self, texts: list[str], *, max_tokens: int) -> list[list[float]]:
            del max_tokens
            captured_texts.extend(texts)
            return [[1.0] + [0.0] * 1023 for _ in texts]

    def fail_decrypt(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("default masked embedding must not decrypt raw text")

    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.delenv("EMBED_EXAMPLES_FROM", raising=False)
    monkeypatch.setattr(
        "intent_routing.api.admin.get_embedding_provider",
        lambda: CapturingProvider(),
    )
    monkeypatch.setattr(EnvelopeEncryptor, "decrypt_text", fail_decrypt)
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    intent = _create_intent(client, service_id)
    raw_text = "전화 010-1234-5678 확인"
    create_response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
        json=_example_payload(raw_text),
    )
    example_id = create_response.json()["example_id"]

    approve_response = client.patch(
        f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
        headers=_admin_headers(),
    )

    assert approve_response.status_code == 200
    assert captured_texts == ["전화 010-****-5678 확인"]


def test_approve_example_embeds_raw_text_only_when_explicitly_configured(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_texts: list[str] = []

    class CapturingProvider:
        model_version = "emb-test-capture"
        dimension = 1024

        def embed_texts(self, texts: list[str], *, max_tokens: int) -> list[list[float]]:
            del max_tokens
            captured_texts.extend(texts)
            return [[1.0] + [0.0] * 1023 for _ in texts]

    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBED_EXAMPLES_FROM", "raw")
    monkeypatch.setattr(
        "intent_routing.api.admin.get_embedding_provider",
        lambda: CapturingProvider(),
    )
    client = _client(db_session)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    intent = _create_intent(client, service_id)
    raw_text = "전화 010-1234-5678 확인"
    create_response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
        json=_example_payload(raw_text),
    )
    example_id = create_response.json()["example_id"]

    approve_response = client.patch(
        f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
        headers=_admin_headers(),
    )

    assert approve_response.status_code == 200
    assert captured_texts == [raw_text]


def test_approve_example_returns_sanitized_error_when_provider_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingProvider:
        model_version = "emb-test-failing"
        dimension = 1024

        def embed_texts(self, texts: list[str], *, max_tokens: int) -> list[list[float]]:
            del texts, max_tokens
            raise RuntimeError("model exploded at /secret/model/path")

    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setattr(
        "intent_routing.api.admin.get_embedding_provider",
        lambda: FailingProvider(),
    )
    client = _client(db_session, raise_server_exceptions=False)
    service_id = f"svc-catalog-{uuid4().hex}"
    _create_service(client, service_id)
    intent = _create_intent(client, service_id)
    raw_text = "전화 010-1234-5678 확인"
    create_response = client.post(
        f"/admin/v1/services/{service_id}/intents/{intent['intent_id']}/examples",
        headers=_admin_headers(),
        json=_example_payload(raw_text),
    )
    example_id = create_response.json()["example_id"]

    approve_response = client.patch(
        f"/admin/v1/services/{service_id}/examples/{example_id}:approve",
        headers=_admin_headers(),
    )

    body = approve_response.json()
    assert approve_response.status_code == 500
    assert body["status"] == "error"
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "Embedding generation failed."
    assert raw_text not in approve_response.text
    assert "/secret/model/path" not in approve_response.text


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


def test_create_and_get_policy_version_persists_thresholds_and_off_topic_policy(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-policy-{uuid4().hex}"
    _create_service(client, service_id)

    create_response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_admin_headers(),
        json=_policy_version_payload(),
    )

    create_body = create_response.json()
    assert create_response.status_code == 201
    assert create_body["service_id"] == service_id
    assert create_body["threshold_preset"] == "balanced"
    assert create_body["threshold_value"] == pytest.approx(0.8)
    assert create_body["off_topic_policy"] == _policy_version_payload()["off_topic_policy"]
    policy_version = create_body["policy_version"]

    persisted = db_session.get(models.PolicyVersion, policy_version)
    assert persisted is not None
    assert persisted.threshold_value == Decimal("0.8")
    assert persisted.clarify_margin == Decimal("0.08")
    assert persisted.min_candidate_score == Decimal("0.55")
    assert persisted.fallback_score == Decimal("0.45")
    assert persisted.off_topic_policy == _policy_version_payload()["off_topic_policy"]

    get_response = client.get(
        f"/admin/v1/services/{service_id}/policy-versions/{policy_version}",
        headers=_admin_headers(),
    )

    get_body = get_response.json()
    assert get_response.status_code == 200
    assert get_body == create_body
    audit_log = db_session.scalar(
        select(models.AuditLog).where(
            models.AuditLog.event_type == "policy_version.created",
            models.AuditLog.target_id == policy_version,
        )
    )
    assert audit_log is not None
    assert audit_log.service_id == service_id
    assert audit_log.target_type == "policy_version"


def test_service_developer_can_manage_only_scoped_policy_versions(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-policy-{uuid4().hex}"
    other_service_id = f"svc-policy-{uuid4().hex}"
    _create_service(client, service_id)
    _create_service(client, other_service_id)

    allowed_response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_developer_headers(service_id),
        json=_policy_version_payload(),
    )
    denied_response = client.post(
        f"/admin/v1/services/{other_service_id}/policy-versions",
        headers=_developer_headers(service_id),
        json=_policy_version_payload(),
    )

    assert allowed_response.status_code == 201
    assert denied_response.status_code == 403
    assert denied_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_policy_version_endpoints_return_not_found_for_missing_service_or_version(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-policy-{uuid4().hex}"
    _create_service(client, service_id)

    missing_service_response = client.post(
        f"/admin/v1/services/missing-{uuid4().hex}/policy-versions",
        headers=_admin_headers(),
        json=_policy_version_payload(),
    )
    missing_version_response = client.get(
        f"/admin/v1/services/{service_id}/policy-versions/missing-version",
        headers=_admin_headers(),
    )

    assert missing_service_response.status_code == 404
    assert missing_service_response.json()["error"]["code"] == "INVALID_REQUEST"
    assert missing_version_response.status_code == 404
    assert missing_version_response.json()["error"]["code"] == "INVALID_REQUEST"


def test_create_policy_version_rejects_blank_off_topic_keywords(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-policy-{uuid4().hex}"
    _create_service(client, service_id)
    payload = _policy_version_payload()
    payload["off_topic_policy"] = {
        **cast(dict[str, object], payload["off_topic_policy"]),
        "keywords": ["날씨", "   "],
    }

    response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_admin_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert db_session.scalar(
        select(models.PolicyVersion).where(models.PolicyVersion.service_id == service_id)
    ) is None
    assert db_session.scalar(
        select(models.AuditLog).where(
            models.AuditLog.event_type == "policy_version.created",
            models.AuditLog.service_id == service_id,
        )
    ) is None


def test_create_policy_version_rejects_extra_policy_keys_without_persisting(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-policy-{uuid4().hex}"
    _create_service(client, service_id)

    risk_payload = _policy_version_payload()
    risk_payload["risk_policy"] = {"enabled": True, "mode": "loose"}
    risk_response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_admin_headers(),
        json=risk_payload,
    )

    assert risk_response.status_code == 422
    assert risk_response.json()["status"] == "error"
    assert risk_response.json()["error"]["code"] == "INVALID_REQUEST"
    assert "detail" not in risk_response.json()
    assert db_session.scalar(
        select(models.PolicyVersion).where(models.PolicyVersion.service_id == service_id)
    ) is None
    assert db_session.scalar(
        select(models.AuditLog).where(
            models.AuditLog.event_type == "policy_version.created",
            models.AuditLog.service_id == service_id,
        )
    ) is None

    fallback_payload = _policy_version_payload()
    fallback_off_topic = cast(dict[str, object], fallback_payload["off_topic_policy"])
    fallback_payload["off_topic_policy"] = {
        **fallback_off_topic,
        "fallback_policy": {
            **cast(dict[str, object], fallback_off_topic["fallback_policy"]),
            "extra": "nope",
        },
    }
    fallback_response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_admin_headers(),
        json=fallback_payload,
    )

    assert fallback_response.status_code == 422
    assert fallback_response.json()["status"] == "error"
    assert fallback_response.json()["error"]["code"] == "INVALID_REQUEST"
    assert "detail" not in fallback_response.json()
    assert db_session.scalar(
        select(models.PolicyVersion).where(models.PolicyVersion.service_id == service_id)
    ) is None
    assert db_session.scalar(
        select(models.AuditLog).where(
            models.AuditLog.event_type == "policy_version.created",
            models.AuditLog.service_id == service_id,
        )
    ) is None


def test_create_policy_version_returns_conflict_on_id_collision(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setattr(
        "intent_routing.api.admin._policy_version_id",
        lambda service_id, _now: f"pol-fixed-collision-{service_id}",
    )
    client = _client(db_session, raise_server_exceptions=False)
    service_id = f"svc-policy-{uuid4().hex}"
    _create_service(client, service_id)

    first_response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_admin_headers(),
        json=_policy_version_payload(),
    )
    second_response = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        headers=_admin_headers(),
        json=_policy_version_payload(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["status"] == "error"
    assert second_response.json()["error"]["code"] == "INVALID_REQUEST"
    persisted_versions = db_session.scalars(
        select(models.PolicyVersion).where(models.PolicyVersion.service_id == service_id)
    ).all()
    assert len(persisted_versions) == 1
    assert persisted_versions[0].policy_version == f"pol-fixed-collision-{service_id}"


def test_post_test_run_persists_dataset_run_and_results(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    client = _client(db_session)
    service_id = f"svc-test-run-{uuid4().hex}"
    policy_version, catalog_version = _seed_csv_runner_state(
        db_session,
        client,
        service_id,
    )

    response = client.post(
        f"/admin/v1/services/{service_id}/test-runs",
        headers=_admin_headers(),
        json={
            "policy_version": policy_version,
            "intent_catalog_version": catalog_version,
            "threshold_preset": "balanced",
            "source_filename": "sprint0_cases.csv",
            "csv_text": _sprint0_csv_text(),
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["test_run_id"].startswith("tr-")
    assert body["test_dataset_version"].startswith("tds-")
    assert body["threshold_preset"] == "balanced"
    assert body["threshold_value"] == pytest.approx(0.8)
    assert body["pass_rate"] == pytest.approx(1.0)
    assert body["review_rate"] == pytest.approx(0.0)
    assert body["risk_pass_rate"] == pytest.approx(1.0)
    assert body["gate_passed"] is True
    assert body["block_reasons"] == []
    assert body["recommendations"] == []

    persisted_dataset = db_session.get(models.TestDataset, body["test_dataset_version"])
    persisted_run = db_session.get(models.TestRun, body["test_run_id"])
    persisted_cases = db_session.scalars(
        select(models.TestCase).where(
            models.TestCase.test_dataset_version == body["test_dataset_version"]
        )
    ).all()
    persisted_results = db_session.scalars(
        select(models.TestResult).where(
            models.TestResult.test_run_id == body["test_run_id"]
        )
    ).all()
    assert persisted_dataset is not None
    assert persisted_dataset.source_filename == "sprint0_cases.csv"
    assert persisted_run is not None
    assert persisted_run.threshold_value == Decimal("0.8")
    assert len(persisted_cases) == 5
    assert len(persisted_results) == 5
    assert {result.result for result in persisted_results} == {"PASS"}


def test_post_test_run_accepts_multipart_csv_upload(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    client = _client(db_session)
    service_id = f"svc-test-run-{uuid4().hex}"
    policy_version, catalog_version = _seed_csv_runner_state(
        db_session,
        client,
        service_id,
    )

    response = client.post(
        f"/admin/v1/services/{service_id}/test-runs",
        headers=_admin_headers(),
        data={
            "policy_version": policy_version,
            "intent_catalog_version": catalog_version,
            "threshold_preset": "balanced",
        },
        files={
            "file": (
                "sprint0_cases.csv",
                _sprint0_csv_text().encode("utf-8"),
                "text/csv",
            )
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["test_run_id"].startswith("tr-")
    assert body["test_dataset_version"].startswith("tds-")
    assert body["threshold_preset"] == "balanced"
    assert body["threshold_value"] == pytest.approx(0.8)
    assert body["pass_rate"] == pytest.approx(1.0)
    persisted_dataset = db_session.get(models.TestDataset, body["test_dataset_version"])
    assert persisted_dataset is not None
    assert persisted_dataset.source_filename == "sprint0_cases.csv"
    persisted_results = db_session.scalars(
        select(models.TestResult).where(
            models.TestResult.test_run_id == body["test_run_id"]
        )
    ).all()
    assert len(persisted_results) == 5


def test_get_test_run_summary_and_results_returns_persisted_rows(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    client = _client(db_session)
    service_id = f"svc-test-run-{uuid4().hex}"
    policy_version, catalog_version = _seed_csv_runner_state(
        db_session,
        client,
        service_id,
    )
    create_response = client.post(
        f"/admin/v1/services/{service_id}/test-runs",
        headers=_admin_headers(),
        json={
            "policy_version": policy_version,
            "intent_catalog_version": catalog_version,
            "threshold_preset": "balanced",
            "source_filename": "sprint0_cases.csv",
            "csv_text": _sprint0_csv_text(),
        },
    )
    created = create_response.json()
    result_to_mutate = db_session.scalar(
        select(models.TestResult)
        .where(models.TestResult.test_run_id == created["test_run_id"])
        .where(models.TestResult.case_id == "C001")
    )
    assert result_to_mutate is not None
    result_to_mutate.result = "FAIL"
    result_to_mutate.reason = "mutated after run to prove summary source of truth"
    db_session.commit()

    summary_response = client.get(
        f"/admin/v1/services/{service_id}/test-runs/{created['test_run_id']}",
        headers=_admin_headers(),
    )
    results_response = client.get(
        f"/admin/v1/services/{service_id}/test-runs/{created['test_run_id']}/results",
        headers=_admin_headers(),
    )

    assert summary_response.status_code == 200
    summary_body = summary_response.json()
    assert summary_body["pass_rate"] == created["pass_rate"]
    assert summary_body["review_rate"] == created["review_rate"]
    assert summary_body["risk_pass_rate"] == created["risk_pass_rate"]
    assert summary_body["gate_passed"] == created["gate_passed"]
    assert summary_body["threshold_preset"] == created["threshold_preset"]
    assert summary_body["threshold_value"] == created["threshold_value"]
    assert results_response.status_code == 200
    rows = results_response.json()
    assert len(rows) == 5
    assert rows[0] == {
        "case_id": "C001",
        "query_masked": "API Timeout이 발생해요",
        "case_type": "positive",
        "expected_decision": "confident",
        "expected_intent": "it_api_timeout",
        "actual_decision": "confident",
        "actual_intent": "it_api_timeout",
        "actual_route_key": "it.api_timeout.manual_lookup",
        "confidence": pytest.approx(1.0),
        "result": "FAIL",
        "reason": "mutated after run to prove summary source of truth",
    }
    assert [row["case_id"] for row in rows] == ["C001", "C002", "C003", "C004", "C005"]


def test_same_csv_can_run_with_each_threshold_preset(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    monkeypatch.setenv("RAW_TEXT_KEK_BASE64", _raw_text_kek())
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")
    client = _client(db_session)
    service_id = f"svc-test-run-{uuid4().hex}"
    policy_version, catalog_version = _seed_csv_runner_state(
        db_session,
        client,
        service_id,
    )

    created: dict[str, dict[str, object]] = {}
    for preset in ("strict", "balanced", "exploratory"):
        response = client.post(
            f"/admin/v1/services/{service_id}/test-runs",
            headers=_admin_headers(),
            json={
                "policy_version": policy_version,
                "intent_catalog_version": catalog_version,
                "threshold_preset": preset,
                "source_filename": "sprint0_cases.csv",
                "csv_text": _sprint0_csv_text(),
            },
        )
        assert response.status_code == 201
        created[preset] = response.json()

    assert len({body["test_run_id"] for body in created.values()}) == 3
    assert created["strict"]["threshold_value"] == pytest.approx(1.0)
    assert created["balanced"]["threshold_value"] == pytest.approx(0.8)
    assert created["exploratory"]["threshold_value"] == pytest.approx(0.6)


def test_post_test_run_invalid_csv_returns_error_envelope(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session, raise_server_exceptions=False)
    service_id = f"svc-test-run-{uuid4().hex}"
    policy_version, catalog_version = _seed_csv_runner_state(
        db_session,
        client,
        service_id,
    )

    response = client.post(
        f"/admin/v1/services/{service_id}/test-runs",
        headers=_admin_headers(),
        json={
            "policy_version": policy_version,
            "intent_catalog_version": catalog_version,
            "threshold_preset": "balanced",
            "source_filename": "bad.csv",
            "csv_text": (
                "case_id,query,case_type,expected_intent,memo\n"
                "C001,hello,positive,it_api_timeout,bad"
            ),
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert "columns" in body["error"]["message"]
    assert "detail" not in body
