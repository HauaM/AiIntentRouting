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
            json={"global_roles": ["application_admin"]},
        )
        assert grant_response.status_code == 200
        assert grant_response.json()["global_roles"] == ["application_admin"]

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
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    existing_actor_id = db_session.scalar(
        select(models.AdminUserRole.user_id).where(
            models.AdminUserRole.role == "system_admin"
        )
    )
    actor_id = existing_actor_id or f"last-system-admin-{suffix}"
    client = _client(db_session, actor_id=actor_id)
    created_actor = existing_actor_id is None
    if created_actor:
        _purge_rows(db_session, admin_user_ids=[actor_id], emails=[f"{actor_id}@example.com"])
    try:
        if created_actor:
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
        original_roles = [
            role.role for role in repository.list_admin_user_roles(actor_id)
        ]

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
        ] == original_roles
    finally:
        if created_actor:
            _purge_rows(db_session, admin_user_ids=[actor_id], emails=[f"{actor_id}@example.com"])


def test_cannot_grant_second_system_admin(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    target_user_id = f"sys-b-{suffix}"
    target_email = f"{target_user_id}@example.com"
    dept_number = f"sys-admin-transfer-dept-{suffix}"
    target_user_number = f"sys-admin-target-{suffix}"
    source = _existing_or_created_system_admin(db_session, suffix=suffix)

    _purge_rows(
        db_session,
        admin_user_ids=[target_user_id],
        emails=[target_email],
        dept_numbers=[dept_number],
        user_numbers=[target_user_number],
    )
    try:
        target = _create_admin_user(
            db_session,
            user_id=target_user_id,
            email=target_email,
            dept_number=dept_number,
            user_number=target_user_number,
            role="application_admin",
        )
        client = _client(db_session, actor_id=source.user_id)

        response = client.patch(
            f"/admin/v1/admin-users/{target.user_id}",
            json={"global_roles": ["application_admin", "system_admin"]},
        )

        assert response.status_code == 409
        assert "system_admin already exists" in response.text
    finally:
        _purge_rows(
            db_session,
            admin_user_ids=[target_user_id],
            emails=[target_email],
            dept_numbers=[dept_number],
            user_numbers=[target_user_number],
        )


def test_system_admin_transfer_replaces_single_owner_atomically(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    target_user_id = f"sys-target-{suffix}"
    target_email = f"{target_user_id}@example.com"
    dept_number = f"sys-admin-transfer-dept-{suffix}"
    target_user_number = f"sys-admin-target-{suffix}"
    source = _existing_or_created_system_admin(db_session, suffix=suffix)

    _purge_rows(
        db_session,
        admin_user_ids=[target_user_id],
        emails=[target_email],
        dept_numbers=[dept_number],
        user_numbers=[target_user_number],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        before_source_roles = [
            role.role for role in repository.list_admin_user_roles(source.user_id)
        ]
        target = _create_admin_user(
            db_session,
            user_id=target_user_id,
            email=target_email,
            dept_number=dept_number,
            user_number=target_user_number,
            role="application_admin",
        )
        client = _client(db_session, actor_id=source.user_id)

        response = client.post(
            "/admin/v1/system-admin-transfer",
            json={
                "from_admin_user_id": source.user_id,
                "to_admin_user_id": target.user_id,
                "reason": "Platform ownership rotation.",
            },
        )

        assert response.status_code == 200
        repository = IntentRoutingRepository(db_session)
        assert [role.role for role in repository.list_admin_user_roles(source.user_id)] == [
            "application_admin"
        ]
        assert [role.role for role in repository.list_admin_user_roles(target.user_id)] == [
            "system_admin"
        ]
        audit_events = list(
            db_session.scalars(
                select(models.AuditLog.event_type)
                .where(models.AuditLog.target_type == "admin_user")
                .where(models.AuditLog.target_id == target.user_id)
                .order_by(models.AuditLog.created_at, models.AuditLog.event_type)
            )
        )
        assert "admin_user.system_admin_transferred" in audit_events
    finally:
        repository = IntentRoutingRepository(db_session)
        target_user = repository.get_admin_user(target_user_id)
        restore_now = datetime.now(UTC)
        if target_user is not None:
            _restore_admin_user_roles(
                db_session,
                user_id=target_user.user_id,
                desired_roles=[],
                assigned_at=restore_now,
            )
            db_session.commit()
        _restore_admin_user_roles(
            db_session,
            user_id=source.user_id,
            desired_roles=before_source_roles,
            assigned_at=restore_now,
        )
        db_session.commit()
        _purge_rows(
            db_session,
            admin_user_ids=[target_user_id],
            emails=[target_email],
            dept_numbers=[dept_number],
            user_numbers=[target_user_number],
        )


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
        (
            "post",
            "/admin/v1/system-admin-transfer",
            {
                "from_admin_user_id": "source-admin",
                "to_admin_user_id": "target-admin",
                "reason": "Denied non-system-admin transfer.",
            },
        ),
    ]

    for method, path, payload in requests:
        if payload is None:
            response = getattr(client, method)(path)
        else:
            response = getattr(client, method)(path, json=payload)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_admin_access_request_approval_creates_user_admin_user_and_application_admin(
    db_session: Session,
) -> None:
    client = _client(db_session)
    suffix = uuid4().hex[:8]
    user_number = f"req-user-{suffix}"
    email = f"req-user-{suffix}@example.com"
    password = "request-password"
    department = _create_department(db_session, dept_number=f"req-dept-{suffix}")

    _purge_rows(
        db_session,
        emails=[email],
        user_numbers=[user_number],
    )
    try:
        request_response = client.post(
            "/admin/v1/admin-access-requests",
            json={
                "user_number": user_number,
                "name": "Request User",
                "department_id": str(department.id),
                "email": email,
                "password": password,
                "access_reason": "Need to manage routing intents for service alpha.",
            },
        )
        assert request_response.status_code == 201
        request_id = request_response.json()["request_id"]

        approve_response = client.post(
            f"/admin/v1/admin-access-requests/{request_id}/approve",
            json={"decision_reason": "Approved for service onboarding."},
        )

        assert approve_response.status_code == 200
        body = approve_response.json()
        assert body["status"] == "approved"
        assert body["created_user_id"] is not None
        assert body["created_admin_user_id"] is not None
        assert body["department"]["id"] == str(department.id)
        assert body["department"]["dept_number"] == department.dept_number

        request_record = db_session.get(models.AdminAccessRequest, request_id)
        assert request_record is not None
        assert request_record.password_hash is None

        organization_user = db_session.get(models.OrganizationUser, body["created_user_id"])
        assert organization_user is not None
        assert organization_user.user_number == user_number

        admin_user = db_session.get(models.AdminUser, body["created_admin_user_id"])
        assert admin_user is not None
        assert admin_user.status == "active"
        assert (
            admin_user.admin_access_reason
            == "Need to manage routing intents for service alpha."
        )

        roles = [
            role.role
            for role in IntentRoutingRepository(db_session).list_admin_user_roles(
                admin_user.user_id
            )
        ]
        assert roles == ["application_admin"]

        audit_events = list(
            db_session.scalars(
                select(models.AuditLog.event_type)
                .where(
                    models.AuditLog.target_type.in_(
                        ["admin_access_request", "admin_user"]
                    )
                )
                .where(
                    models.AuditLog.target_id.in_(
                        [str(request_id), admin_user.user_id]
                    )
                )
                .order_by(models.AuditLog.created_at, models.AuditLog.event_type)
            )
        )
        assert "admin_access_request.created" in audit_events
        assert "admin_access_request.approved" in audit_events
        assert "admin_user.global_role_granted" in audit_events
    finally:
        _purge_rows(
            db_session,
            emails=[email],
            user_numbers=[user_number],
        )


def test_non_system_admin_cannot_approve_admin_access_request(
    db_session: Session,
) -> None:
    client = _client(db_session, global_roles=frozenset({"application_admin"}))
    response = client.get("/admin/v1/admin-access-requests")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_system_admin_list_admin_access_requests_applies_status_filter_and_limit(
    db_session: Session,
) -> None:
    client = _client(db_session)
    suffix = uuid4().hex[:8]
    pending_user_numbers = [f"pending-user-{suffix}-1", f"pending-user-{suffix}-2"]
    pending_emails = [f"{user_number}@example.com" for user_number in pending_user_numbers]
    approved_user_number = f"approved-user-{suffix}"
    approved_email = f"{approved_user_number}@example.com"
    department = _create_department(db_session, dept_number=f"list-dept-{suffix}")

    _purge_rows(
        db_session,
        emails=[*pending_emails, approved_email],
        user_numbers=[*pending_user_numbers, approved_user_number],
    )
    try:
        for index, (user_number, email) in enumerate(
            zip(pending_user_numbers, pending_emails, strict=True),
            start=1,
        ):
            create_response = client.post(
                "/admin/v1/admin-access-requests",
                json={
                    "user_number": user_number,
                    "name": f"Pending User {index}",
                    "department_id": str(department.id),
                    "email": email,
                    "password": "pending-password",
                    "access_reason": f"Pending access request {index}.",
                },
            )
            assert create_response.status_code == 201

        approved_create_response = client.post(
            "/admin/v1/admin-access-requests",
            json={
                "user_number": approved_user_number,
                "name": "Approved User",
                "department_id": str(department.id),
                "email": approved_email,
                "password": "approved-password",
                "access_reason": "Approved access request.",
            },
        )
        assert approved_create_response.status_code == 201
        approved_request_id = approved_create_response.json()["request_id"]

        approve_response = client.post(
            f"/admin/v1/admin-access-requests/{approved_request_id}/approve",
            json={"decision_reason": "Approved for admin onboarding."},
        )
        assert approve_response.status_code == 200

        response = client.get(
            "/admin/v1/admin-access-requests",
            params={"status": "pending", "limit": 1},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["status"] == "pending"
        assert body[0]["user_number"] in pending_user_numbers
    finally:
        _purge_rows(
            db_session,
            emails=[*pending_emails, approved_email],
            user_numbers=[*pending_user_numbers, approved_user_number],
        )


def test_list_admin_access_requests_rejects_invalid_status_query(
    db_session: Session,
) -> None:
    client = _client(db_session)

    response = client.get(
        "/admin/v1/admin-access-requests",
        params={"status": "not-a-real-status"},
    )

    assert response.status_code == 422


def test_admin_access_request_rejection_clears_pending_password_hash(
    db_session: Session,
) -> None:
    client = _client(db_session)
    suffix = uuid4().hex[:8]
    user_number = f"reject-user-{suffix}"
    email = f"reject-user-{suffix}@example.com"
    department = _create_department(db_session, dept_number=f"reject-dept-{suffix}")

    _purge_rows(
        db_session,
        emails=[email],
        user_numbers=[user_number],
    )
    try:
        create_response = client.post(
            "/admin/v1/admin-access-requests",
            json={
                "user_number": user_number,
                "name": "Reject User",
                "department_id": str(department.id),
                "email": email,
                "password": "reject-password",
                "access_reason": "Need temporary admin review capabilities.",
            },
        )
        assert create_response.status_code == 201
        request_id = create_response.json()["request_id"]

        reject_response = client.post(
            f"/admin/v1/admin-access-requests/{request_id}/reject",
            json={"decision_reason": "Insufficient business justification."},
        )

        assert reject_response.status_code == 200
        body = reject_response.json()
        assert body["status"] == "rejected"
        assert body["created_user_id"] is None
        assert body["created_admin_user_id"] is None

        request_record = db_session.get(models.AdminAccessRequest, request_id)
        assert request_record is not None
        assert request_record.password_hash is None
        assert request_record.decision_reason == "Insufficient business justification."
    finally:
        _purge_rows(
            db_session,
            emails=[email],
            user_numbers=[user_number],
        )


def test_public_departments_returns_active_minimal_registration_choices(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    active_dept_number = f"public-active-{suffix}"
    inactive_dept_number = f"public-inactive-{suffix}"
    client = _client(db_session)

    _purge_rows(db_session, dept_numbers=[active_dept_number, inactive_dept_number])
    try:
        active_department = _create_department(
            db_session,
            dept_number=active_dept_number,
        )
        inactive_department = _create_department(
            db_session,
            dept_number=inactive_dept_number,
        )
        inactive_department.use_yn = "N"
        db_session.commit()

        response = client.get(
            "/admin/v1/public/departments",
            params={"query": suffix},
        )

        assert response.status_code == 200
        body = response.json()
        assert body == [
            {
                "id": str(active_department.id),
                "dept_number": active_dept_number,
                "name": active_department.name,
            }
        ]
        assert "use_yn" not in response.text
        assert "created_by" not in response.text
    finally:
        _purge_rows(db_session, dept_numbers=[active_dept_number, inactive_dept_number])


def _create_department(
    db_session: Session,
    *,
    dept_number: str,
) -> models.Department:
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
        db_session.commit()
    return department


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


def _create_admin_user(
    db_session: Session,
    *,
    user_id: str,
    email: str,
    dept_number: str,
    user_number: str,
    role: str,
) -> models.AdminUser:
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)
    organization_user = _create_organization_user(
        db_session,
        dept_number=dept_number,
        user_number=user_number,
        use_yn="Y",
    )
    admin_user = repository.create_admin_user(
        user_id=user_id,
        email=email,
        display_name=f"Admin {user_id}",
        password_hash="password-hash",
        status="active",
        organization_user_id=organization_user.id,
        admin_access_reason="integration test setup",
        created_at=now,
        updated_at=now,
    )
    repository.assign_admin_user_role(
        user_id=admin_user.user_id,
        role=role,
        assigned_by="integration-test",
        assigned_at=now,
    )
    db_session.commit()
    return admin_user


def _existing_or_created_system_admin(
    db_session: Session,
    *,
    suffix: str,
) -> models.AdminUser:
    repository = IntentRoutingRepository(db_session)
    existing_user_id = db_session.scalar(
        select(models.AdminUserRole.user_id).where(models.AdminUserRole.role == "system_admin")
    )
    if existing_user_id is not None:
        existing = repository.get_admin_user(existing_user_id)
        assert existing is not None
        return existing

    user_id = f"seed-system-admin-{suffix}"
    email = f"{user_id}@example.com"
    _purge_rows(db_session, admin_user_ids=[user_id], emails=[email])
    now = datetime.now(UTC)
    admin_user = repository.create_admin_user(
        user_id=user_id,
        email=email,
        display_name="Seed System Admin",
        password_hash="password-hash",
        status="active",
        admin_access_reason="integration test seed system admin",
        created_at=now,
        updated_at=now,
    )
    repository.assign_admin_user_role(
        user_id=admin_user.user_id,
        role="system_admin",
        assigned_by="integration-test",
        assigned_at=now,
    )
    db_session.commit()
    return admin_user


def _restore_admin_user_roles(
    db_session: Session,
    *,
    user_id: str,
    desired_roles: list[str],
    assigned_at: datetime,
) -> None:
    repository = IntentRoutingRepository(db_session)
    desired = frozenset(desired_roles)
    current = frozenset(
        role.role for role in repository.list_admin_user_roles(user_id)
    )

    # `system_admin` must be assigned before other roles are restored, and removed last.
    if "system_admin" in desired and "system_admin" not in current:
        repository.ensure_admin_user_role(
            user_id=user_id,
            role="system_admin",
            assigned_by="integration-test-restore",
            assigned_at=assigned_at,
        )
        current = frozenset(
            role.role for role in repository.list_admin_user_roles(user_id)
        )

    for role in sorted(desired - current):
        repository.ensure_admin_user_role(
            user_id=user_id,
            role=role,
            assigned_by="integration-test-restore",
            assigned_at=assigned_at,
        )

    for role in sorted(current - desired):
        if role == "system_admin" and "system_admin" in desired:
            continue
        repository.delete_admin_user_role_by_key(user_id, role)


def _purge_rows(
    db_session: Session,
    *,
    admin_user_ids: list[str] | None = None,
    admin_access_request_ids: list[str] | None = None,
    emails: list[str] | None = None,
    dept_numbers: list[str] | None = None,
    user_numbers: list[str] | None = None,
) -> None:
    db_session.rollback()
    admin_user_ids = admin_user_ids or []
    admin_access_request_ids = admin_access_request_ids or []
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
        existing_request_ids = list(
            db_session.scalars(
                select(models.AdminAccessRequest.request_id).where(
                    models.AdminAccessRequest.email_normalized.in_(
                        [email.strip().lower() for email in emails]
                    )
                )
            )
        )
        admin_access_request_ids = [
            *admin_access_request_ids,
            *[str(request_id) for request_id in existing_request_ids],
        ]
    if user_numbers:
        existing_request_ids = list(
            db_session.scalars(
                select(models.AdminAccessRequest.request_id).where(
                    models.AdminAccessRequest.user_number.in_(user_numbers)
                )
            )
        )
        admin_access_request_ids = [
            *admin_access_request_ids,
            *[str(request_id) for request_id in existing_request_ids],
        ]
    if admin_access_request_ids:
        db_session.execute(
            text(
                "delete from audit_logs "
                "where target_type = 'admin_access_request' and target_id = any(:request_ids)"
            ),
            {"request_ids": admin_access_request_ids},
        )
        db_session.execute(
            text("delete from admin_access_requests where request_id::text = any(:request_ids)"),
            {"request_ids": admin_access_request_ids},
        )
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
