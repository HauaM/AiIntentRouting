from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from os import environ
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

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in environ,
    reason="Mutating RBAC integration tests require explicit TEST_DATABASE_URL.",
)


def test_session_service_developer_can_manage_only_assigned_service(
    db_session: Session,
) -> None:
    service_a = f"svc-rbac-a-{uuid4().hex}"
    service_b = f"svc-rbac-b-{uuid4().hex}"
    developer_user = f"developer-{uuid4().hex}"
    operator_user = f"operator-{uuid4().hex}"
    system_admin_user = f"system-admin-{uuid4().hex}"
    now = datetime.now(UTC)

    _purge_rows(
        db_session,
        user_ids=[developer_user, operator_user, system_admin_user],
        service_ids=[service_a, service_b],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        _create_service(repository, service_a, now=now)
        _create_service(repository, service_b, now=now)
        developer_token = _create_user_session(
            repository,
            developer_user,
            now=now,
            service_roles=[(service_a, "service_developer")],
        )
        operator_token = _create_user_session(
            repository,
            operator_user,
            now=now,
            service_roles=[(service_a, "service_operator")],
        )
        system_admin_token = _create_user_session(
            repository,
            system_admin_user,
            now=now,
            global_roles=["system_admin"],
        )
        db_session.commit()

        client = _client(db_session)

        allowed_create = client.post(
            f"/admin/v1/services/{service_a}/intents",
            cookies={ADMIN_SESSION_COOKIE_NAME: developer_token},
            json=_intent_payload("route.service.a"),
        )
        denied_other_service = client.get(
            f"/admin/v1/services/{service_b}/intents",
            cookies={ADMIN_SESSION_COOKIE_NAME: developer_token},
        )
        operator_denied = client.post(
            f"/admin/v1/services/{service_a}/intents",
            cookies={ADMIN_SESSION_COOKIE_NAME: operator_token},
            json=_intent_payload("route.operator.denied"),
        )
        system_admin_allowed = client.get(
            f"/admin/v1/services/{service_b}/intents",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
        )

        assert allowed_create.status_code == 201
        assert allowed_create.json()["created_by"] == developer_user
        assert denied_other_service.status_code == 403
        assert denied_other_service.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
        assert operator_denied.status_code == 403
        assert operator_denied.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
        assert system_admin_allowed.status_code == 200
    finally:
        _purge_rows(
            db_session,
            user_ids=[developer_user, operator_user, system_admin_user],
            service_ids=[service_a, service_b],
        )


def test_me_services_returns_session_accessible_services(
    db_session: Session,
) -> None:
    service_a = f"svc-me-a-{uuid4().hex}"
    service_b = f"svc-me-b-{uuid4().hex}"
    developer_user = f"developer-me-{uuid4().hex}"
    system_admin_user = f"system-admin-me-{uuid4().hex}"
    now = datetime.now(UTC)

    _purge_rows(
        db_session,
        user_ids=[developer_user, system_admin_user],
        service_ids=[service_a, service_b],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        _create_service(repository, service_a, now=now)
        _create_service(repository, service_b, now=now)
        developer_token = _create_user_session(
            repository,
            developer_user,
            now=now,
            service_roles=[(service_a, "service_developer")],
        )
        system_admin_token = _create_user_session(
            repository,
            system_admin_user,
            now=now,
            global_roles=["system_admin"],
        )
        db_session.commit()

        client = _client(db_session)

        developer_response = client.get(
            "/admin/v1/me/services",
            cookies={ADMIN_SESSION_COOKIE_NAME: developer_token},
            headers={
                "X-Service-Scope": service_b,
                "X-Actor-Roles": "system_admin",
            },
        )
        system_admin_response = client.get(
            "/admin/v1/me/services",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
        )

        assert developer_response.status_code == 200
        developer_services = developer_response.json()
        assert [service["service_id"] for service in developer_services] == [service_a]
        assert developer_services[0]["roles"] == ["service_developer"]

        assert system_admin_response.status_code == 200
        system_admin_services = system_admin_response.json()
        system_admin_services_by_id = {
            service["service_id"]: service for service in system_admin_services
        }
        assert system_admin_services_by_id[service_a]["roles"] == ["system_admin"]
        assert system_admin_services_by_id[service_b]["roles"] == ["system_admin"]
    finally:
        _purge_rows(
            db_session,
            user_ids=[developer_user, system_admin_user],
            service_ids=[service_a, service_b],
        )


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    return TestClient(app)


def _create_service(
    repository: IntentRoutingRepository,
    service_id: str,
    *,
    now: datetime,
) -> None:
    repository.create_service(
        service_id=service_id,
        display_name=f"RBAC {service_id}",
        environment="test",
        default_threshold_preset="balanced",
        max_input_tokens=256,
        status="active",
        created_by="integration-test",
        created_at=now,
        updated_at=now,
    )


def _create_user_session(
    repository: IntentRoutingRepository,
    user_id: str,
    *,
    now: datetime,
    global_roles: list[str] | None = None,
    service_roles: list[tuple[str, str]] | None = None,
) -> str:
    repository.create_admin_user(
        user_id=user_id,
        email=f"{user_id}@example.com",
        display_name=user_id,
        password_hash="password-hash",
        status="active",
        created_at=now,
        updated_at=now,
    )
    for role in global_roles or []:
        repository.assign_admin_user_role(
            user_id=user_id,
            role=role,
            assigned_by="integration-test",
            assigned_at=now,
        )
    for service_id, role in service_roles or []:
        repository.assign_user_service_role(
            user_id=user_id,
            service_id=service_id,
            role=role,
            assigned_by="integration-test",
            assigned_at=now,
        )
    raw_token = f"raw-session-{user_id}"
    repository.create_admin_session(
        session_id=f"session-{user_id}",
        user_id=user_id,
        token_hash=hash_admin_session_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    return raw_token


def _intent_payload(route_key: str) -> dict[str, object]:
    return {
        "intent_id": f"intent-{uuid4().hex}",
        "domain": "support",
        "display_name": "Support intent",
        "description": "Route support requests.",
        "route_key": route_key,
        "include_keywords": ["support"],
        "exclude_keywords": [],
    }


def _purge_rows(
    db_session: Session,
    *,
    user_ids: list[str],
    service_ids: list[str],
) -> None:
    db_session.execute(
        text("delete from user_service_roles where user_id = any(:user_ids)"),
        {"user_ids": user_ids},
    )
    db_session.execute(
        text("delete from admin_user_roles where user_id = any(:user_ids)"),
        {"user_ids": user_ids},
    )
    db_session.execute(
        text("delete from admin_sessions where user_id = any(:user_ids)"),
        {"user_ids": user_ids},
    )
    db_session.execute(
        text("delete from admin_users where user_id = any(:user_ids)"),
        {"user_ids": user_ids},
    )
    db_session.execute(
        text("delete from intents where service_id = any(:service_ids)"),
        {"service_ids": service_ids},
    )
    db_session.execute(
        text("delete from services where service_id = any(:service_ids)"),
        {"service_ids": service_ids},
    )
    db_session.commit()
