from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import (
    get_admin_session,
    require_admin_context,
    require_admin_session_context,
)
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.main import create_app


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
        AssertionError("admin user management routes should use session context")
    )
    return TestClient(app)


def test_system_admin_manages_linked_admin_user_access(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    admin_user_id = f"managed-admin-{suffix}"
    email = f"managed-admin-{suffix}@example.com"
    dept_number = f"adm-mgmt-dept-{suffix}"
    user_number = f"adm-mgmt-user-{suffix}"
    client = _client(db_session)

    _purge_rows(
        db_session,
        admin_user_ids=[admin_user_id],
        emails=[email],
        dept_numbers=[dept_number],
        user_numbers=[user_number],
    )
    try:
        organization_user = _create_organization_user(
            db_session,
            dept_number=dept_number,
            user_number=user_number,
            use_yn="Y",
        )

        create_response = client.post(
            "/admin/v1/admin-users",
            json={
                "user_id": admin_user_id,
                "organization_user_id": str(organization_user.id),
                "email": email,
                "display_name": "Managed Admin",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["user_id"] == admin_user_id
        assert created["organization_user_id"] == str(organization_user.id)
        assert created["status"] == "disabled"
        assert created["global_roles"] == []
        assert created["is_last_active_system_admin"] is False
        assert "password_hash" not in create_response.text

        list_response = client.get(
            "/admin/v1/admin-users",
            params={"organization_user_id": str(organization_user.id)},
        )
        assert list_response.status_code == 200
        assert [row["user_id"] for row in list_response.json()] == [admin_user_id]

        grant_response = client.patch(
            f"/admin/v1/admin-users/{admin_user_id}",
            json={"global_roles": ["system_admin"]},
        )
        assert grant_response.status_code == 200
        assert grant_response.json()["global_roles"] == ["system_admin"]

        activate_response = client.patch(
            f"/admin/v1/admin-users/{admin_user_id}",
            json={"status": "active"},
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["status"] == "active"

        revoke_response = client.patch(
            f"/admin/v1/admin-users/{admin_user_id}",
            json={"global_roles": []},
        )
        assert revoke_response.status_code == 200
        assert revoke_response.json()["global_roles"] == []

        disable_response = client.patch(
            f"/admin/v1/admin-users/{admin_user_id}",
            json={"status": "disabled"},
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["status"] == "disabled"

        audit_events = list(
            db_session.scalars(
                select(models.AuditLog.event_type)
                .where(models.AuditLog.target_type == "admin_user")
                .where(models.AuditLog.target_id == admin_user_id)
                .order_by(models.AuditLog.created_at, models.AuditLog.event_type)
            )
        )
        assert "admin_user.created" in audit_events
        assert "admin_user.global_role_granted" in audit_events
        assert "admin_user.activated" in audit_events
        assert "admin_user.global_role_revoked" in audit_events
        assert "admin_user.disabled" in audit_events
    finally:
        _purge_rows(
            db_session,
            admin_user_ids=[admin_user_id],
            emails=[email],
            dept_numbers=[dept_number],
            user_numbers=[user_number],
        )


def test_admin_user_creation_rejects_inactive_users_and_duplicate_links(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    first_admin_user_id = f"duplicate-admin-{suffix}"
    second_admin_user_id = f"duplicate-admin-second-{suffix}"
    email = f"duplicate-admin-{suffix}@example.com"
    second_email = f"duplicate-admin-second-{suffix}@example.com"
    dept_number = f"adm-dup-dept-{suffix}"
    active_user_number = f"adm-dup-active-{suffix}"
    inactive_user_number = f"adm-dup-inactive-{suffix}"
    client = _client(db_session)

    _purge_rows(
        db_session,
        admin_user_ids=[first_admin_user_id, second_admin_user_id],
        emails=[email, second_email],
        dept_numbers=[dept_number],
        user_numbers=[active_user_number, inactive_user_number],
    )
    try:
        active_user = _create_organization_user(
            db_session,
            dept_number=dept_number,
            user_number=active_user_number,
            use_yn="Y",
        )
        inactive_user = _create_organization_user(
            db_session,
            dept_number=dept_number,
            user_number=inactive_user_number,
            use_yn="N",
        )

        first_response = client.post(
            "/admin/v1/admin-users",
            json={
                "user_id": first_admin_user_id,
                "organization_user_id": str(active_user.id),
                "email": email,
                "display_name": "Duplicate Admin",
            },
        )
        duplicate_link_response = client.post(
            "/admin/v1/admin-users",
            json={
                "user_id": second_admin_user_id,
                "organization_user_id": str(active_user.id),
                "email": second_email,
                "display_name": "Duplicate Link",
            },
        )
        duplicate_email_response = client.post(
            "/admin/v1/admin-users",
            json={
                "user_id": second_admin_user_id,
                "organization_user_id": str(inactive_user.id),
                "email": email.upper(),
                "display_name": "Duplicate Email",
            },
        )
        inactive_user_response = client.post(
            "/admin/v1/admin-users",
            json={
                "user_id": second_admin_user_id,
                "organization_user_id": str(inactive_user.id),
                "email": second_email,
                "display_name": "Inactive Link",
            },
        )

        assert first_response.status_code == 201
        assert duplicate_link_response.status_code == 409
        assert duplicate_link_response.json()["error"]["code"] == "INVALID_REQUEST"
        assert duplicate_email_response.status_code == 409
        assert duplicate_email_response.json()["error"]["code"] == "INVALID_REQUEST"
        assert inactive_user_response.status_code == 409
        assert inactive_user_response.json()["error"]["code"] == "INVALID_REQUEST"
    finally:
        _purge_rows(
            db_session,
            admin_user_ids=[first_admin_user_id, second_admin_user_id],
            emails=[email, second_email],
            dept_numbers=[dept_number],
            user_numbers=[active_user_number, inactive_user_number],
        )


def test_admin_user_activation_rejects_inactive_linked_organization_user(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    admin_user_id = f"inactive-link-admin-{suffix}"
    email = f"inactive-link-admin-{suffix}@example.com"
    dept_number = f"inactive-link-dept-{suffix}"
    user_number = f"inactive-link-user-{suffix}"
    client = _client(db_session)

    _purge_rows(
        db_session,
        admin_user_ids=[admin_user_id],
        emails=[email],
        dept_numbers=[dept_number],
        user_numbers=[user_number],
    )
    try:
        organization_user = _create_organization_user(
            db_session,
            dept_number=dept_number,
            user_number=user_number,
            use_yn="Y",
        )
        create_response = client.post(
            "/admin/v1/admin-users",
            json={
                "user_id": admin_user_id,
                "organization_user_id": str(organization_user.id),
                "email": email,
                "display_name": "Inactive Link Admin",
            },
        )
        assert create_response.status_code == 201

        organization_user.use_yn = "N"
        organization_user.updated_at = datetime.now(UTC)
        db_session.commit()

        activate_response = client.patch(
            f"/admin/v1/admin-users/{admin_user_id}",
            json={"status": "active"},
        )

        assert activate_response.status_code == 409
        assert activate_response.json()["error"]["code"] == "INVALID_REQUEST"
        persisted = db_session.get(models.AdminUser, admin_user_id)
        assert persisted is not None
        assert persisted.status == "disabled"
    finally:
        _purge_rows(
            db_session,
            admin_user_ids=[admin_user_id],
            emails=[email],
            dept_numbers=[dept_number],
            user_numbers=[user_number],
        )


def test_current_user_cannot_disable_or_revoke_own_last_system_admin(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    actor_id = f"last-system-admin-{suffix}"
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    client = _client(db_session, actor_id=actor_id)

    _purge_rows(db_session, admin_user_ids=[actor_id], emails=[f"{actor_id}@example.com"])
    try:
        repository.create_admin_user(
            user_id=actor_id,
            email=f"{actor_id}@example.com",
            display_name="Last System Admin",
            password_hash="password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=actor_id,
            role="system_admin",
            assigned_by="integration-test",
            assigned_at=now,
        )
        db_session.commit()

        list_response = client.get("/admin/v1/admin-users", params={"query": actor_id})
        disable_response = client.patch(
            f"/admin/v1/admin-users/{actor_id}",
            json={"status": "disabled"},
        )
        revoke_response = client.patch(
            f"/admin/v1/admin-users/{actor_id}",
            json={"global_roles": []},
        )

        assert list_response.status_code == 200
        assert list_response.json()[0]["is_last_active_system_admin"] is True
        assert disable_response.status_code == 409
        assert disable_response.json()["error"]["code"] == "INVALID_REQUEST"
        assert revoke_response.status_code == 409
        assert revoke_response.json()["error"]["code"] == "INVALID_REQUEST"
        assert db_session.get(models.AdminUser, actor_id).status == "active"  # type: ignore[union-attr]
        assert [
            role.role for role in repository.list_admin_user_roles(actor_id)
        ] == ["system_admin"]
    finally:
        _purge_rows(db_session, admin_user_ids=[actor_id], emails=[f"{actor_id}@example.com"])


def test_admin_user_management_routes_require_system_admin(
    db_session: Session,
) -> None:
    client = _client(db_session, global_roles=frozenset())
    missing_user_id = "missing-admin-user"
    missing_org_user_id = "11111111-1111-1111-1111-111111111111"

    requests = [
        ("get", "/admin/v1/admin-users", None),
        (
            "post",
            "/admin/v1/admin-users",
            {
                "organization_user_id": missing_org_user_id,
                "email": "denied@example.com",
                "display_name": "Denied",
            },
        ),
        (
            "patch",
            f"/admin/v1/admin-users/{missing_user_id}",
            {"status": "disabled"},
        ),
    ]

    for method, path, payload in requests:
        if payload is None:
            response = getattr(client, method)(path)
        else:
            response = getattr(client, method)(path, json=payload)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def _create_organization_user(
    db_session: Session,
    *,
    dept_number: str,
    user_number: str,
    use_yn: str,
) -> models.OrganizationUser:
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)
    department = db_session.scalar(
        select(models.Department).where(models.Department.dept_number == dept_number)
    )
    if department is None:
        department = repository.create_department(
            dept_number=dept_number,
            name=f"Dept {dept_number}",
            use_yn="Y",
            created_by="integration-test",
            updated_by="integration-test",
            created_at=now,
            updated_at=now,
        )
    organization_user = repository.create_organization_user(
        user_number=user_number,
        name=f"User {user_number}",
        department_id=department.id,
        use_yn=use_yn,
        created_by="integration-test",
        updated_by="integration-test",
        created_at=now,
        updated_at=now,
    )
    db_session.commit()
    return organization_user


def _purge_rows(
    db_session: Session,
    *,
    admin_user_ids: list[str] | None = None,
    emails: list[str] | None = None,
    dept_numbers: list[str] | None = None,
    user_numbers: list[str] | None = None,
) -> None:
    admin_user_ids = admin_user_ids or []
    emails = emails or []
    dept_numbers = dept_numbers or []
    user_numbers = user_numbers or []

    if emails:
        existing_ids = list(
            db_session.scalars(
                select(models.AdminUser.user_id).where(
                    models.AdminUser.email_normalized.in_(
                        [email.strip().lower() for email in emails]
                    )
                )
            )
        )
        admin_user_ids = [*admin_user_ids, *existing_ids]
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
            text(
                "delete from audit_logs "
                "where target_type = 'admin_user' and target_id = any(:user_ids)"
            ),
            {"user_ids": admin_user_ids},
        )
        db_session.execute(
            text("delete from admin_users where user_id = any(:user_ids)"),
            {"user_ids": admin_user_ids},
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
