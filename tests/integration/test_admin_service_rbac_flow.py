from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from os import environ
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import get_admin_session
from intent_routing.db import models
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


def test_me_services_reflects_role_grant_and_revoke_from_membership_api(
    db_session: Session,
) -> None:
    service_id = f"svc-me-c2-{uuid4().hex}"
    developer_user = f"developer-me-c2-{uuid4().hex}"
    system_admin_user = f"system-admin-me-c2-{uuid4().hex}"
    now = datetime.now(UTC)

    _purge_rows(
        db_session,
        user_ids=[developer_user, system_admin_user],
        service_ids=[service_id],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        _create_service(repository, service_id, now=now)
        developer_token = _create_user_session(
            repository,
            developer_user,
            now=now,
        )
        system_admin_token = _create_user_session(
            repository,
            system_admin_user,
            now=now,
            global_roles=["system_admin"],
        )
        db_session.commit()

        client = _client(db_session)

        initial_services_response = client.get(
            "/admin/v1/me/services",
            cookies={ADMIN_SESSION_COOKIE_NAME: developer_token},
        )
        grant_response = client.post(
            f"/admin/v1/services/{service_id}/members/{developer_user}/roles",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
            json={"role": "service_developer"},
        )
        services_after_grant_response = client.get(
            "/admin/v1/me/services",
            cookies={ADMIN_SESSION_COOKIE_NAME: developer_token},
        )
        revoke_response = client.delete(
            (
                f"/admin/v1/services/{service_id}/members/{developer_user}"
                "/roles/service_developer"
            ),
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
        )
        services_after_revoke_response = client.get(
            "/admin/v1/me/services",
            cookies={ADMIN_SESSION_COOKIE_NAME: developer_token},
        )
        intents_after_revoke_response = client.get(
            f"/admin/v1/services/{service_id}/intents",
            cookies={ADMIN_SESSION_COOKIE_NAME: developer_token},
        )

        assert initial_services_response.status_code == 200
        assert service_id not in {
            service["service_id"] for service in initial_services_response.json()
        }

        assert grant_response.status_code == 200
        assert services_after_grant_response.status_code == 200
        assert services_after_grant_response.json() == [
            {
                "service_id": service_id,
                "display_name": f"RBAC {service_id}",
                "environment": "test",
                "status": "active",
                "roles": ["service_developer"],
            }
        ]

        assert revoke_response.status_code == 200
        assert services_after_revoke_response.status_code == 200
        assert service_id not in {
            service["service_id"] for service in services_after_revoke_response.json()
        }
        assert intents_after_revoke_response.status_code == 403
        assert (
            intents_after_revoke_response.json()["error"]["code"]
            == "SERVICE_SCOPE_DENIED"
        )
    finally:
        _purge_rows(
            db_session,
            user_ids=[developer_user, system_admin_user],
            service_ids=[service_id],
        )


def test_system_admin_can_search_users_and_grant_revoke_service_roles(
    db_session: Session,
) -> None:
    service_id = f"svc-c2-members-{uuid4().hex}"
    developer_user = f"developer-c2-{uuid4().hex}"
    system_admin_user = f"system-admin-c2-{uuid4().hex}"
    now = datetime.now(UTC)

    _purge_rows(
        db_session,
        user_ids=[developer_user, system_admin_user],
        service_ids=[service_id],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        _create_service(repository, service_id, now=now)
        _create_user_session(
            repository,
            developer_user,
            now=now,
        )
        system_admin_token = _create_user_session(
            repository,
            system_admin_user,
            now=now,
            global_roles=["system_admin"],
        )
        db_session.commit()

        client = _client(db_session)

        users_response = client.get(
            "/admin/v1/users",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
            params={"query": "developer-c2", "limit": 25},
        )
        initial_members_response = client.get(
            f"/admin/v1/services/{service_id}/members",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
        )
        grant_response = client.post(
            f"/admin/v1/services/{service_id}/members/{developer_user}/roles",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
            json={"role": "service_developer"},
        )
        duplicate_grant_response = client.post(
            f"/admin/v1/services/{service_id}/members/{developer_user}/roles",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
            json={"role": "service_developer"},
        )
        members_after_grant_response = client.get(
            f"/admin/v1/services/{service_id}/members",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
        )
        revoke_response = client.delete(
            (
                f"/admin/v1/services/{service_id}/members/{developer_user}"
                "/roles/service_developer"
            ),
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
        )
        duplicate_revoke_response = client.delete(
            (
                f"/admin/v1/services/{service_id}/members/{developer_user}"
                "/roles/service_developer"
            ),
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
        )
        members_after_revoke_response = client.get(
            f"/admin/v1/services/{service_id}/members",
            cookies={ADMIN_SESSION_COOKIE_NAME: system_admin_token},
        )
        users_response_text = users_response.text

        assert users_response.status_code == 200
        users = users_response.json()
        developer_matches = [
            user for user in users if user["user_id"] == developer_user
        ]
        assert developer_matches == [
            {
                "user_id": developer_user,
                "email": f"{developer_user}@example.com",
                "display_name": developer_user,
                "status": "active",
            }
        ]
        assert "password_hash" not in users_response_text
        assert "token_hash" not in users_response_text
        assert "session_token" not in users_response_text

        assert initial_members_response.status_code == 200
        assert initial_members_response.json() == []

        assert grant_response.status_code == 200
        grant = grant_response.json()
        assert grant["service_id"] == service_id
        assert grant["user_id"] == developer_user
        assert grant["role"] == "service_developer"
        assert grant["assigned_by"] == system_admin_user
        assert grant["assigned_at"]

        assert duplicate_grant_response.status_code == 200
        assert duplicate_grant_response.json() == grant

        assert members_after_grant_response.status_code == 200
        assert members_after_grant_response.json() == [
            {
                "service_id": service_id,
                "user": {
                    "user_id": developer_user,
                    "email": f"{developer_user}@example.com",
                    "display_name": developer_user,
                    "status": "active",
                },
                "roles": [
                    {
                        "role": "service_developer",
                        "assigned_by": system_admin_user,
                        "assigned_at": grant["assigned_at"],
                    }
                ],
            }
        ]

        assert revoke_response.status_code == 200
        revoke = revoke_response.json()
        assert revoke["service_id"] == service_id
        assert revoke["user_id"] == developer_user
        assert revoke["role"] == "service_developer"
        assert revoke["revoked_by"] == system_admin_user
        assert revoke["revoked_at"]

        assert duplicate_revoke_response.status_code == 404
        assert duplicate_revoke_response.json()["error"]["code"] == "INVALID_REQUEST"

        assert members_after_revoke_response.status_code == 200
        assert members_after_revoke_response.json() == []

        audit_logs = list(
            db_session.scalars(
                select(models.AuditLog)
                .where(models.AuditLog.service_id == service_id)
                .where(
                    models.AuditLog.event_type.in_(
                        [
                            "service_membership.role_granted",
                            "service_membership.role_revoked",
                        ]
                    )
                )
                .order_by(models.AuditLog.created_at, models.AuditLog.event_type)
            )
        )
        assert [audit_log.event_type for audit_log in audit_logs] == [
            "service_membership.role_granted",
            "service_membership.role_revoked",
        ]
        grant_audit, revoke_audit = audit_logs
        assert grant_audit.actor_id == system_admin_user
        assert grant_audit.service_id == service_id
        assert grant_audit.target_type == "user_service_role"
        assert grant_audit.target_id == (
            f"{service_id}:{developer_user}:service_developer"
        )
        assert grant_audit.before_state is None
        assert grant_audit.after_state == grant
        assert revoke_audit.actor_id == system_admin_user
        assert revoke_audit.service_id == service_id
        assert revoke_audit.target_type == "user_service_role"
        assert revoke_audit.target_id == (
            f"{service_id}:{developer_user}:service_developer"
        )
        assert revoke_audit.before_state == {
            "service_id": service_id,
            "user_id": developer_user,
            "role": "service_developer",
            "assigned_by": system_admin_user,
            "assigned_at": grant["assigned_at"],
        }
        assert revoke_audit.after_state == revoke
    finally:
        _purge_rows(
            db_session,
            user_ids=[developer_user, system_admin_user],
            service_ids=[service_id],
        )


def test_non_system_admin_cannot_grant_or_revoke_service_roles(
    db_session: Session,
) -> None:
    service_id = f"svc-c2-deny-{uuid4().hex}"
    target_user = f"target-c2-{uuid4().hex}"
    actor_by_role = {
        "service_owner": f"owner-c2-{uuid4().hex}",
        "service_developer": f"developer-c2-deny-{uuid4().hex}",
        "service_operator": f"operator-c2-{uuid4().hex}",
        "auditor": f"auditor-c2-{uuid4().hex}",
    }
    unrelated_user = f"unrelated-c2-{uuid4().hex}"
    all_user_ids = [target_user, unrelated_user, *actor_by_role.values()]
    now = datetime.now(UTC)

    _purge_rows(db_session, user_ids=all_user_ids, service_ids=[service_id])
    try:
        repository = IntentRoutingRepository(db_session)
        _create_service(repository, service_id, now=now)
        _create_user_session(repository, target_user, now=now)
        repository.assign_user_service_role(
            user_id=target_user,
            service_id=service_id,
            role="service_operator",
            assigned_by="integration-test",
            assigned_at=now,
        )
        tokens_by_actor = {
            actor_user: _create_user_session(
                repository,
                actor_user,
                now=now,
                service_roles=[(service_id, role)],
            )
            for role, actor_user in actor_by_role.items()
        }
        tokens_by_actor[unrelated_user] = _create_user_session(
            repository,
            unrelated_user,
            now=now,
        )
        db_session.commit()

        client = _client(db_session)

        for actor_user, token in tokens_by_actor.items():
            grant_response = client.post(
                f"/admin/v1/services/{service_id}/members/{target_user}/roles",
                cookies={ADMIN_SESSION_COOKIE_NAME: token},
                json={"role": "service_developer"},
            )
            revoke_response = client.delete(
                (
                    f"/admin/v1/services/{service_id}/members/{target_user}"
                    "/roles/service_operator"
                ),
                cookies={ADMIN_SESSION_COOKIE_NAME: token},
            )

            assert grant_response.status_code == 403, actor_user
            assert grant_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
            assert revoke_response.status_code == 403, actor_user
            assert revoke_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"

        absent_grant_role = db_session.scalar(
            select(models.UserServiceRole)
            .where(models.UserServiceRole.user_id == target_user)
            .where(models.UserServiceRole.service_id == service_id)
            .where(models.UserServiceRole.role == "service_developer")
        )
        existing_revoke_target_role = db_session.scalar(
            select(models.UserServiceRole)
            .where(models.UserServiceRole.user_id == target_user)
            .where(models.UserServiceRole.service_id == service_id)
            .where(models.UserServiceRole.role == "service_operator")
        )
        membership_audit_logs = list(
            db_session.scalars(
                select(models.AuditLog)
                .where(models.AuditLog.service_id == service_id)
                .where(
                    models.AuditLog.event_type.in_(
                        [
                            "service_membership.role_granted",
                            "service_membership.role_revoked",
                        ]
                    )
                )
            )
        )

        assert absent_grant_role is None
        assert existing_revoke_target_role is not None
        assert membership_audit_logs == []
    finally:
        _purge_rows(db_session, user_ids=all_user_ids, service_ids=[service_id])


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
        text("delete from audit_logs where service_id = any(:service_ids)"),
        {"service_ids": service_ids},
    )
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
