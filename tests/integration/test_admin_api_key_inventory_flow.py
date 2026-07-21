from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import get_admin_session
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.main import create_app
from intent_routing.security.admin_sessions import (
    ADMIN_SESSION_COOKIE_NAME,
    hash_admin_session_token,
)


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    return TestClient(app, raise_server_exceptions=False)


def _admin_headers(**overrides: str) -> dict[str, str]:
    headers = {
        "X-Admin-Token": "local-admin-token",
        "X-Actor-Id": "api-key-inventory-admin",
        "X-Actor-Roles": "system_admin",
    }
    headers.update(overrides)
    return headers


def _system_admin_client(db_session: Session) -> tuple[TestClient, str]:
    user_id = f"api-key-inventory-admin-{uuid4().hex}"
    raw_token = f"raw-session-{user_id}"
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    repository.create_admin_user(
        user_id=user_id,
        email=f"{user_id}@example.com",
        display_name="API Key Inventory Admin",
        password_hash="password-hash",
        status="active",
        created_at=now,
        updated_at=now,
    )
    repository.assign_admin_user_role(
        user_id=user_id,
        role="system_admin",
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

    client = _client(db_session)
    client.cookies.set(ADMIN_SESSION_COOKIE_NAME, raw_token)
    return client, user_id


def _create_service(client: TestClient, service_id: str) -> None:
    response = client.post(
        "/admin/v1/services",
        headers=_admin_headers(),
        json={
            "service_id": service_id,
            "display_name": "API Key Inventory Service",
            "max_input_tokens": 256,
        },
    )
    assert response.status_code == 201


def _purge_rows(db_session: Session, *, user_id: str, service_id: str) -> None:
    db_session.execute(
        text("delete from audit_logs where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from api_keys where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from services where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.execute(
        text("delete from admin_sessions where user_id = :user_id"),
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


def test_api_key_inventory_excludes_secret(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-api-key-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        created = IntentRoutingRepository(db_session).create_api_key(
            key_id=f"key_live_{uuid4().hex}",
            key_hash="inventory-test-hash",
            key_fingerprint="sha256:inventory-test:0000",
            environment="dev",
            app_id="helpdesk-bot",
            service_id=service_id,
            allowed_intents=[],
            allowed_route_keys=[],
            status="active",
            expires_at=datetime.now(UTC) + timedelta(days=90),
            revoked_at=None,
            created_by="api-key-inventory-admin",
            created_at=datetime.now(UTC),
        )
        db_session.commit()
        inventory = client.get(
            "/admin/v1/api-keys",
            headers=_admin_headers(),
            params={"service_id": service_id, "environment": "dev", "status": "active"},
        )

        assert inventory.status_code == 200
        row = inventory.json()[0]
        assert row["key_id"] == created.key_id
        assert row["key_fingerprint"] == created.key_fingerprint
        assert row["service_id"] == service_id
        assert row["environment"] == "dev"
        assert row["status"] == "active"
        assert "api_key" not in row
    finally:
        _purge_rows(
            db_session,
            user_id="api-key-inventory-admin",
            service_id=service_id,
        )


def test_api_key_inventory_rejects_unsupported_environment_filter(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)

    response = client.get(
        "/admin/v1/api-keys",
        headers=_admin_headers(),
        params={"environment": "pilot"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert (
        response.json()["error"]["message"]
        == "environment must be one of dev, qa, prod."
    )


def test_api_key_create_endpoints_reject_blank_app_id_before_released_catalog_validation(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")
    client = _client(db_session)
    service_id = f"svc-api-key-input-{uuid4().hex}"
    try:
        _create_service(client, service_id)
        payload = {"environment": "dev", "app_id": " \t "}

        global_response = client.post(
            "/admin/v1/api-keys",
            headers=_admin_headers(),
            json={**payload, "service_id": service_id},
        )
        service_response = client.post(
            f"/admin/v1/services/{service_id}/api-keys",
            headers=_admin_headers(),
            json=payload,
        )

        assert global_response.status_code == 422
        assert service_response.status_code == 422

        released_catalog_response = client.post(
            f"/admin/v1/services/{service_id}/api-keys",
            headers=_admin_headers(),
            json={"environment": "dev", "app_id": " checkout-web "},
        )
        assert released_catalog_response.status_code == 422
        assert released_catalog_response.json()["error"]["message"] == (
            "released catalog is required for scoped API key creation."
        )
    finally:
        _purge_rows(
            db_session,
            user_id="api-key-inventory-admin",
            service_id=service_id,
        )
