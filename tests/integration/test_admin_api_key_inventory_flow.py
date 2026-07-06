from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
        json={
            "service_id": service_id,
            "display_name": "API Key Inventory Service",
            "environment": "dev",
            "default_threshold_preset": "balanced",
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


def test_api_key_inventory_excludes_secret(db_session: Session) -> None:
    client, user_id = _system_admin_client(db_session)
    service_id = f"svc-api-key-{uuid4().hex}"
    try:
        _create_service(client, service_id)

        created = client.post(
            "/admin/v1/api-keys",
            json={
                "service_id": service_id,
                "environment": "dev",
                "app_id": "helpdesk-bot",
                "allowed_intents": [],
                "allowed_route_keys": [],
                "expires_in_days": 90,
            },
        )
        inventory = client.get(
            "/admin/v1/api-keys",
            params={"service_id": service_id, "environment": "dev", "status": "active"},
        )

        assert created.status_code == 201
        assert "api_key" in created.json()
        assert inventory.status_code == 200
        row = inventory.json()[0]
        assert row["key_id"] == created.json()["key_id"]
        assert row["key_fingerprint"] == created.json()["key_fingerprint"]
        assert row["service_id"] == service_id
        assert row["environment"] == "dev"
        assert row["status"] == "active"
        assert "api_key" not in row
    finally:
        _purge_rows(db_session, user_id=user_id, service_id=service_id)
