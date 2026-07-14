from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.api import admin as admin_api
from intent_routing.api.admin_dependencies import (
    get_admin_session,
    require_admin_context,
    require_admin_session_context,
)
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.main import create_app


def test_permission_management_route_returns_empty_summary_list_without_db(
    monkeypatch,
) -> None:
    class _FakePermissionRepository:
        def __init__(self, session: object) -> None:
            self.session = session

        def list_permission_admin_user_summaries(self, **kwargs: object) -> list[object]:
            assert kwargs == {
                "query": None,
                "status": None,
                "global_role": None,
                "organization_link": None,
                "organization_use_yn": None,
                "limit": 100,
            }
            return []

    monkeypatch.setattr(admin_api, "IntentRoutingRepository", _FakePermissionRepository)

    response = _client_with_fake_session().get(
        "/admin/v1/permission-management/admin-users",
    )

    assert response.status_code == 200
    assert response.json() == []


def test_permission_management_summary_requires_system_admin_without_db() -> None:
    response = _client_with_fake_session(global_roles=frozenset()).get(
        "/admin/v1/permission-management/admin-users",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def _client(
    db_session: Session,
    *,
    actor_id: str = "system-admin",
    global_roles: frozenset[str] = frozenset({"system_admin"}),
) -> TestClient:
    app = create_app()
    session_context = SimpleNamespace(
        user=SimpleNamespace(user_id=actor_id),
        global_roles=global_roles,
        service_roles=(),
    )

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[require_admin_session_context] = lambda: session_context
    app.dependency_overrides[require_admin_context] = lambda: (_ for _ in ()).throw(
        AssertionError("permission management routes should use session context")
    )
    return TestClient(app)


def _client_with_fake_session(
    *,
    actor_id: str = "system-admin",
    global_roles: frozenset[str] = frozenset({"system_admin"}),
) -> TestClient:
    app = create_app()
    session_context = SimpleNamespace(
        user=SimpleNamespace(user_id=actor_id),
        global_roles=global_roles,
        service_roles=(),
    )

    def override_session() -> Iterator[object]:
        yield object()

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[require_admin_session_context] = lambda: session_context
    app.dependency_overrides[require_admin_context] = lambda: (_ for _ in ()).throw(
        AssertionError("permission management routes should use session context")
    )
    return TestClient(app)


def test_system_admin_lists_permission_summaries_without_user_authorization_flags(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    admin_user_id = f"perm-api-admin-{suffix}"
    service_id = f"perm-api-service-{suffix}"
    dept_number = f"perm-api-dept-{suffix}"
    user_number = f"perm-api-user-{suffix}"
    now = datetime.now(UTC)

    _purge_rows(
        db_session,
        admin_user_ids=[admin_user_id],
        service_ids=[service_id],
        dept_numbers=[dept_number],
        user_numbers=[user_number],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        department = repository.create_department(
            dept_number=dept_number,
            name="Permission API Department",
            use_yn="Y",
            created_by="integration-test",
            updated_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        organization_user = repository.create_organization_user(
            user_number=user_number,
            name="Permission API User",
            department_id=department.id,
            use_yn="Y",
            created_by="integration-test",
            updated_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_user(
            user_id=admin_user_id,
            organization_user_id=organization_user.id,
            email=f"permission-api-{suffix}@example.com",
            display_name="Permission API Admin",
            password_hash="secret-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=admin_user_id,
            role="system_admin",
            assigned_by="integration-test",
            assigned_at=now,
        )
        repository.create_service(
            service_id=service_id,
            display_name="Permission API Service",
            environment="test",
            default_threshold_preset="balanced",
            max_input_tokens=256,
            status="active",
            created_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        repository.assign_user_service_role(
            user_id=admin_user_id,
            service_id=service_id,
            role="service_owner",
            assigned_by="integration-test",
            assigned_at=now,
        )
        db_session.commit()

        response = _client(db_session).get(
            "/admin/v1/permission-management/admin-users",
            params={
                "query": admin_user_id,
                "status": "active",
                "global_role": "system_admin",
                "organization_link": "linked",
                "organization_use_yn": "Y",
            },
        )

        assert response.status_code == 200
        response_text = response.text
        for forbidden_field in (
            "password_hash",
            "token_hash",
            "session_token",
            "before_state",
            "after_state",
        ):
            assert forbidden_field not in response_text

        summaries = response.json()
        assert len(summaries) == 1
        summary = summaries[0]
        assert summary["user_id"] == admin_user_id
        assert summary["email"] == f"permission-api-{suffix}@example.com"
        assert summary["display_name"] == "Permission API Admin"
        assert summary["status"] == "active"
        assert summary["global_roles"] == ["system_admin"]
        assert isinstance(summary["is_last_active_system_admin"], bool)
        assert summary["created_at"] is not None
        assert summary["updated_at"] is not None
        assert summary["last_login_at"] is None
        assert summary["risk_flags"] == [] or summary["risk_flags"] == [
            "single_active_system_admin"
        ]

        organization_summary = summary["organization_user"]
        assert set(organization_summary) == {
            "id",
            "user_number",
            "name",
            "use_yn",
            "department",
        }
        assert organization_summary["id"] == str(organization_user.id)
        assert organization_summary["user_number"] == user_number
        assert organization_summary["name"] == "Permission API User"
        assert organization_summary["use_yn"] == "Y"
        assert "is_admin" not in organization_summary
        assert "admin_roles" not in organization_summary

        department_summary = organization_summary["department"]
        assert department_summary == {
            "id": str(department.id),
            "dept_number": dept_number,
            "name": "Permission API Department",
            "use_yn": "Y",
        }
        assert summary["service_roles"] == [
            {
                "service_id": service_id,
                "service_display_name": "Permission API Service",
                "role": "service_owner",
                "assigned_by": "integration-test",
                "assigned_at": now.isoformat().replace("+00:00", "Z"),
            }
        ]
    finally:
        _purge_rows(
            db_session,
            admin_user_ids=[admin_user_id],
            service_ids=[service_id],
            dept_numbers=[dept_number],
            user_numbers=[user_number],
        )


def test_permission_management_summary_requires_system_admin(
    db_session: Session,
) -> None:
    response = _client(db_session, global_roles=frozenset()).get(
        "/admin/v1/permission-management/admin-users",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def _purge_rows(
    db_session: Session,
    *,
    admin_user_ids: list[str],
    service_ids: list[str],
    dept_numbers: list[str],
    user_numbers: list[str],
) -> None:
    if admin_user_ids:
        db_session.execute(
            text("delete from admin_sessions where user_id = any(:user_ids)"),
            {"user_ids": admin_user_ids},
        )
        db_session.execute(
            text("delete from admin_user_roles where user_id = any(:user_ids)"),
            {"user_ids": admin_user_ids},
        )
        db_session.execute(
            text("delete from user_service_roles where user_id = any(:user_ids)"),
            {"user_ids": admin_user_ids},
        )
        db_session.execute(
            text("delete from admin_users where user_id = any(:user_ids)"),
            {"user_ids": admin_user_ids},
        )
    if service_ids:
        db_session.execute(
            text("delete from user_service_roles where service_id = any(:service_ids)"),
            {"service_ids": service_ids},
        )
        db_session.execute(
            text("delete from services where service_id = any(:service_ids)"),
            {"service_ids": service_ids},
        )
    if user_numbers:
        db_session.execute(
            text("delete from users where user_number = any(:user_numbers)"),
            {"user_numbers": user_numbers},
        )
    if dept_numbers:
        db_session.execute(
            text("delete from departments where dept_number = any(:dept_numbers)"),
            {"dept_numbers": dept_numbers},
        )
    db_session.commit()
