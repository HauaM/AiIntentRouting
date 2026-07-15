from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.api import admin as admin_api
from intent_routing.api.admin_dependencies import (
    get_admin_session,
    require_admin_context,
    require_admin_session_context,
)
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.main import create_app


def test_permission_management_route_returns_empty_summary_list_without_db(
    monkeypatch: pytest.MonkeyPatch,
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


def test_permission_management_audit_logs_requires_system_admin_without_db() -> None:
    response = _client_with_fake_session(global_roles=frozenset()).get(
        "/admin/v1/permission-management/audit-logs",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_permission_management_risk_findings_requires_system_admin_without_db() -> None:
    response = _client_with_fake_session(global_roles=frozenset()).get(
        "/admin/v1/permission-management/risk-findings",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_permission_management_service_roles_requires_system_admin_without_db() -> None:
    response = _client_with_fake_session(global_roles=frozenset()).get(
        "/admin/v1/permission-management/service-roles",
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
            "admin_yn",
            "adminYn",
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
        assert isinstance(summary["risk_flags"], list)

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


def test_system_admin_lists_permission_service_roles_with_filters_and_metadata(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    admin_user_id = f"perm-service-role-admin-{suffix}"
    other_admin_user_id = f"perm-service-role-other-{suffix}"
    service_id = f"perm-service-role-service-{suffix}"
    other_service_id = f"perm-service-role-other-service-{suffix}"
    dept_number = f"perm-service-role-dept-{suffix}"
    user_number = f"perm-service-role-user-{suffix}"
    now = datetime.now(UTC).replace(microsecond=0)

    _purge_rows(
        db_session,
        admin_user_ids=[admin_user_id, other_admin_user_id],
        service_ids=[service_id, other_service_id],
        dept_numbers=[dept_number],
        user_numbers=[user_number],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        department = repository.create_department(
            dept_number=dept_number,
            name=f"Permission Service Roles Department {suffix}",
            use_yn="Y",
            created_by="integration-test",
            updated_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        organization_user = repository.create_organization_user(
            user_number=user_number,
            name=f"Permission Service Roles User {suffix}",
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
            email=f"{admin_user_id}@example.com",
            display_name="Permission Service Roles Admin",
            password_hash="target-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_user(
            user_id=other_admin_user_id,
            email=f"{other_admin_user_id}@example.com",
            display_name="Permission Service Roles Other",
            password_hash="other-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.create_service(
            service_id=service_id,
            display_name="Permission Service Roles Service",
            environment="test",
            default_threshold_preset="balanced",
            max_input_tokens=256,
            status="active",
            created_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        repository.create_service(
            service_id=other_service_id,
            display_name="Permission Service Roles Other Service",
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
            role="service_developer",
            assigned_by="integration-test",
            assigned_at=now,
        )
        repository.assign_user_service_role(
            user_id=other_admin_user_id,
            service_id=other_service_id,
            role="auditor",
            assigned_by="integration-test",
            assigned_at=now,
        )
        db_session.commit()

        client = _client(db_session)
        filtered_response = client.get(
            "/admin/v1/permission-management/service-roles",
            params={
                "service_id": service_id,
                "user_id": admin_user_id,
                "role": "service_developer",
            },
        )
        query_response = client.get(
            "/admin/v1/permission-management/service-roles",
            params={
                "query": f"Permission Service Roles Department {suffix}",
                "limit": 10,
            },
        )

        assert filtered_response.status_code == 200
        assert query_response.status_code == 200
        response_text = filtered_response.text + query_response.text
        for forbidden_field in (
            "admin_yn",
            "adminYn",
            "password_hash",
            "target-password-hash",
            "other-password-hash",
            "token_hash",
            "session_token",
            "before_state",
            "after_state",
        ):
            assert forbidden_field not in response_text

        items = filtered_response.json()
        assert len(items) == 1
        item = items[0]
        assert set(item) == {
            "service_id",
            "service_display_name",
            "user",
            "organization_user",
            "role",
            "assigned_by",
            "assigned_at",
        }
        assert item["service_id"] == service_id
        assert item["service_display_name"] == "Permission Service Roles Service"
        assert item["role"] == "service_developer"
        assert item["assigned_by"] == "integration-test"
        assert item["assigned_at"] == now.isoformat().replace("+00:00", "Z")
        assert item["user"] == {
            "user_id": admin_user_id,
            "email": f"{admin_user_id}@example.com",
            "display_name": "Permission Service Roles Admin",
            "status": "active",
        }
        assert item["organization_user"] == {
            "id": str(organization_user.id),
            "user_number": user_number,
            "name": f"Permission Service Roles User {suffix}",
            "use_yn": "Y",
            "department_name": f"Permission Service Roles Department {suffix}",
        }
        assert [
            (matched["service_id"], matched["user"]["user_id"], matched["role"])
            for matched in query_response.json()
        ] == [(service_id, admin_user_id, "service_developer")]
    finally:
        _purge_rows(
            db_session,
            admin_user_ids=[admin_user_id, other_admin_user_id],
            service_ids=[service_id, other_service_id],
            dept_numbers=[dept_number],
            user_numbers=[user_number],
        )


def test_permission_management_audit_logs_filter_groups_and_sanitize_states(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    admin_user_id = f"perm-audit-admin-{suffix}"
    service_id = f"perm-audit-service-{suffix}"
    now = datetime.now(UTC).replace(microsecond=0)

    _purge_rows(
        db_session,
        admin_user_ids=[admin_user_id],
        service_ids=[service_id],
        dept_numbers=[],
        user_numbers=[],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        repository.create_service(
            service_id=service_id,
            display_name="Permission Audit Service",
            environment="test",
            default_threshold_preset="balanced",
            max_input_tokens=256,
            status="active",
            created_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        repository.insert_audit_log(
            event_type="admin_user.created",
            actor_id="system-admin",
            service_id=None,
            trace_id=None,
            target_type="admin_user",
            target_id=admin_user_id,
            view_reason=(
                "approval=PERM-AUDIT-001; "
                "reason=password_hash token session_token api_secret should redact"
            ),
            source_ip="127.0.0.1",
            before_state={"password_hash": "plain-password-hash"},
            after_state={
                "token": "plain-session-token",
                "api_secret": "plain-api-secret",
            },
            created_at=now,
        )
        repository.insert_audit_log(
            event_type="service_membership.role_granted",
            actor_id="system-admin",
            service_id=service_id,
            trace_id=None,
            target_type="user_service_role",
            target_id=f"{service_id}:{admin_user_id}:auditor",
            view_reason=None,
            source_ip="127.0.0.1",
            before_state={"session_token": "plain-session-token"},
            after_state={"api_secret": "plain-api-secret"},
            created_at=now + timedelta(seconds=1),
        )
        repository.insert_audit_log(
            event_type="api_key.created",
            actor_id="system-admin",
            service_id=service_id,
            trace_id=None,
            target_type="api_key",
            target_id=f"ignored-{suffix}",
            view_reason=None,
            source_ip="127.0.0.1",
            before_state=None,
            after_state=None,
            created_at=now + timedelta(seconds=2),
        )
        db_session.commit()

        client = _client(db_session)
        admin_user_response = client.get(
            "/admin/v1/permission-management/audit-logs",
            params={"event_group": "admin_user", "target_id": admin_user_id},
        )
        service_membership_response = client.get(
            "/admin/v1/permission-management/audit-logs",
            params={"event_group": "service_membership", "service_id": service_id},
        )
        all_response = client.get(
            "/admin/v1/permission-management/audit-logs",
            params={"actor_id": "system-admin", "limit": 2},
        )
        unrelated_event_type_response = client.get(
            "/admin/v1/permission-management/audit-logs",
            params={
                "event_type": "api_key.created",
                "actor_id": "system-admin",
                "target_id": f"ignored-{suffix}",
                "limit": 1,
            },
        )

        assert admin_user_response.status_code == 200
        assert service_membership_response.status_code == 200
        assert all_response.status_code == 200
        assert unrelated_event_type_response.status_code == 200
        assert [item["event_type"] for item in admin_user_response.json()] == [
            "admin_user.created"
        ]
        assert [item["event_type"] for item in service_membership_response.json()] == [
            "service_membership.role_granted"
        ]
        assert [item["event_type"] for item in all_response.json()] == [
            "service_membership.role_granted",
            "admin_user.created",
        ]
        assert unrelated_event_type_response.json() == []
        assert admin_user_response.json()[0]["service_id"] is None
        response_text = (
            admin_user_response.text
            + service_membership_response.text
            + all_response.text
        )
        for forbidden_fragment in (
            "before_state",
            "after_state",
            "password_hash",
            "plain-password-hash",
            "plain-session-token",
            "plain-api-secret",
            "session_token",
            "api_secret",
        ):
            assert forbidden_fragment not in response_text
    finally:
        _purge_rows(
            db_session,
            admin_user_ids=[admin_user_id],
            service_ids=[service_id],
            dept_numbers=[],
            user_numbers=[],
        )


def test_permission_management_risk_findings_returns_baseline_findings(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    prefix = f"perm-risk-{suffix}"
    single_admin_id = f"{prefix}-single-system"
    inactive_link_admin_id = f"{prefix}-inactive-link"
    disabled_service_admin_id = f"{prefix}-disabled-service"
    unlinked_admin_id = f"{prefix}-unlinked"
    service_id = f"{prefix}-service"
    active_dept_number = f"{prefix}-dept-active"
    inactive_dept_number = f"{prefix}-dept-inactive"
    disabled_dept_number = f"{prefix}-dept-disabled"
    active_user_number = f"{prefix}-user-active"
    inactive_user_number = f"{prefix}-user-inactive"
    disabled_user_number = f"{prefix}-user-disabled"
    now = datetime.now(UTC).replace(microsecond=0)

    admin_user_ids = [
        single_admin_id,
        inactive_link_admin_id,
        disabled_service_admin_id,
        unlinked_admin_id,
    ]
    service_ids = [service_id]
    dept_numbers = [
        active_dept_number,
        inactive_dept_number,
        disabled_dept_number,
    ]
    user_numbers = [
        active_user_number,
        inactive_user_number,
        disabled_user_number,
    ]
    system_admin_role_rows: list[dict[str, object]] = []
    try:
        system_admin_role_rows = _backup_and_delete_system_admin_roles(db_session)
        _purge_rows(
            db_session,
            admin_user_ids=admin_user_ids,
            service_ids=service_ids,
            dept_numbers=dept_numbers,
            user_numbers=user_numbers,
        )
        repository = IntentRoutingRepository(db_session)
        active_user = _create_permission_organization_user(
            repository,
            dept_number=active_dept_number,
            user_number=active_user_number,
            use_yn="Y",
            now=now,
        )
        inactive_user = _create_permission_organization_user(
            repository,
            dept_number=inactive_dept_number,
            user_number=inactive_user_number,
            use_yn="N",
            now=now,
        )
        disabled_user = _create_permission_organization_user(
            repository,
            dept_number=disabled_dept_number,
            user_number=disabled_user_number,
            use_yn="Y",
            now=now,
        )
        repository.create_service(
            service_id=service_id,
            display_name="Permission Risk Service",
            environment="test",
            default_threshold_preset="balanced",
            max_input_tokens=256,
            status="active",
            created_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_user(
            user_id=single_admin_id,
            organization_user_id=active_user.id,
            email=f"{single_admin_id}@example.com",
            display_name="Single System Admin",
            password_hash="single-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=single_admin_id,
            role="system_admin",
            assigned_by="integration-test",
            assigned_at=now,
        )
        repository.create_admin_user(
            user_id=inactive_link_admin_id,
            organization_user_id=inactive_user.id,
            email=f"{inactive_link_admin_id}@example.com",
            display_name="Inactive Linked Admin",
            password_hash="inactive-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_user(
            user_id=disabled_service_admin_id,
            organization_user_id=disabled_user.id,
            email=f"{disabled_service_admin_id}@example.com",
            display_name="Disabled Service Admin",
            password_hash="disabled-password-hash",
            status="disabled",
            created_at=now,
            updated_at=now,
        )
        repository.assign_user_service_role(
            user_id=disabled_service_admin_id,
            service_id=service_id,
            role="service_operator",
            assigned_by="integration-test",
            assigned_at=now,
        )
        repository.create_admin_user(
            user_id=unlinked_admin_id,
            email=f"{unlinked_admin_id}@example.com",
            display_name="Unlinked Admin",
            password_hash="unlinked-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        db_session.commit()

        response = _client(db_session).get(
            "/admin/v1/permission-management/risk-findings"
        )

        assert response.status_code == 200
        findings = response.json()
        relevant_findings = [
            finding
            for finding in findings
            if finding["admin_user_id"] in admin_user_ids
        ]
        by_key = {
            (
                finding["category"],
                finding["admin_user_id"],
                finding["service_id"],
            ): finding
            for finding in relevant_findings
        }

        assert (
            "linked_inactive_organization_user",
            inactive_link_admin_id,
            None,
        ) in by_key
        assert (
            "disabled_admin_has_service_roles",
            disabled_service_admin_id,
            service_id,
        ) in by_key
        assert ("active_admin_without_roles", unlinked_admin_id, None) in by_key
        assert ("unlinked_admin_user", unlinked_admin_id, None) in by_key
        assert (
            by_key[
                (
                    "disabled_admin_has_service_roles",
                    disabled_service_admin_id,
                    service_id,
                )
            ]["finding_id"]
            == f"disabled_admin_has_service_roles:{disabled_service_admin_id}:{service_id}"
        )
        for finding in relevant_findings:
            assert finding["severity"] in {"low", "medium", "high"}
            assert finding["title"]
            assert finding["recommended_action"]
            assert isinstance(finding["evidence"], dict)
            assert finding["category"] != "single_active_system_admin"
        response_text = response.text
        for forbidden_fragment in (
            "password_hash",
            "single-password-hash",
            "inactive-password-hash",
            "disabled-password-hash",
            "unlinked-password-hash",
        ):
            assert forbidden_fragment not in response_text
    finally:
        try:
            _purge_rows(
                db_session,
                admin_user_ids=admin_user_ids,
                service_ids=service_ids,
                dept_numbers=dept_numbers,
                user_numbers=user_numbers,
            )
        finally:
            db_session.rollback()
            _restore_system_admin_roles(db_session, system_admin_role_rows)


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
            text(
                "delete from audit_logs "
                "where actor_id = any(:user_ids) or target_id = any(:user_ids)"
            ),
            {"user_ids": admin_user_ids},
        )
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
            text("delete from audit_logs where service_id = any(:service_ids)"),
            {"service_ids": service_ids},
        )
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


def _create_permission_organization_user(
    repository: IntentRoutingRepository,
    *,
    dept_number: str,
    user_number: str,
    use_yn: str,
    now: datetime,
) -> models.OrganizationUser:
    department = repository.create_department(
        dept_number=dept_number,
        name=f"Permission Department {dept_number}",
        use_yn="Y",
        created_by="integration-test",
        updated_by="integration-test",
        created_at=now,
        updated_at=now,
    )
    return repository.create_organization_user(
        user_number=user_number,
        name=f"Permission User {user_number}",
        department_id=department.id,
        use_yn=use_yn,
        created_by="integration-test",
        updated_by="integration-test",
        created_at=now,
        updated_at=now,
    )


def _backup_and_delete_system_admin_roles(
    db_session: Session,
) -> list[dict[str, object]]:
    rows = [
        dict(row)
        for row in db_session.execute(
            text(
                "select user_id, role, assigned_by, assigned_at "
                "from admin_user_roles where role = 'system_admin'"
            )
        ).mappings()
    ]
    db_session.execute(text("delete from admin_user_roles where role = 'system_admin'"))
    db_session.commit()
    return rows


def _restore_system_admin_roles(
    db_session: Session,
    rows: list[dict[str, object]],
) -> None:
    if rows:
        db_session.execute(
            text(
                "insert into admin_user_roles (user_id, role, assigned_by, assigned_at) "
                "values (:user_id, :role, :assigned_by, :assigned_at) "
                "on conflict (user_id, role) do update set "
                "assigned_by = excluded.assigned_by, "
                "assigned_at = excluded.assigned_at"
            ),
            rows,
        )
    db_session.commit()
