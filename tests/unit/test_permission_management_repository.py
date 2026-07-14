from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository


def test_repository_exposes_permission_summary_helper() -> None:
    assert "list_permission_admin_user_summaries" in dir(IntentRoutingRepository)


def test_repository_lists_permission_admin_user_summaries_with_metadata_and_risks(
    db_session: Session,
) -> None:
    suffix = uuid4().hex[:8]
    prefix = f"perm-repo-{suffix}"
    active_admin_id = f"{prefix}-active"
    inactive_link_admin_id = f"{prefix}-inactive-link"
    disabled_service_admin_id = f"{prefix}-disabled-service"
    unlinked_admin_id = f"{prefix}-unlinked"
    service_id = f"{prefix}-service"
    active_dept_number = f"{prefix}-dept-active"
    inactive_dept_number = f"{prefix}-dept-inactive"
    active_user_number = f"{prefix}-user-active"
    inactive_user_number = f"{prefix}-user-inactive"
    disabled_user_number = f"{prefix}-user-disabled"
    now = datetime.now(UTC).replace(microsecond=0)

    _purge_rows(
        db_session,
        admin_user_ids=[
            active_admin_id,
            inactive_link_admin_id,
            disabled_service_admin_id,
            unlinked_admin_id,
        ],
        service_ids=[service_id],
        dept_numbers=[active_dept_number, inactive_dept_number],
        user_numbers=[active_user_number, inactive_user_number, disabled_user_number],
    )
    try:
        repository = IntentRoutingRepository(db_session)
        active_user = _create_organization_user(
            repository,
            dept_number=active_dept_number,
            user_number=active_user_number,
            use_yn="Y",
            now=now,
        )
        inactive_user = _create_organization_user(
            repository,
            dept_number=inactive_dept_number,
            user_number=inactive_user_number,
            use_yn="N",
            now=now,
        )
        disabled_user = _create_organization_user(
            repository,
            dept_number=active_dept_number,
            user_number=disabled_user_number,
            use_yn="Y",
            now=now,
        )
        repository.create_service(
            service_id=service_id,
            display_name="Permission Repository Service",
            environment="test",
            default_threshold_preset="balanced",
            max_input_tokens=256,
            status="active",
            created_by="unit-test",
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_user(
            user_id=active_admin_id,
            organization_user_id=active_user.id,
            email=f"{active_admin_id}@example.com",
            display_name="Permission Repository Active",
            password_hash="active-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=active_admin_id,
            role="system_admin",
            assigned_by="unit-test",
            assigned_at=now,
        )
        repository.assign_user_service_role(
            user_id=active_admin_id,
            service_id=service_id,
            role="auditor",
            assigned_by="unit-test",
            assigned_at=now,
        )
        repository.create_admin_user(
            user_id=inactive_link_admin_id,
            organization_user_id=inactive_user.id,
            email=f"{inactive_link_admin_id}@example.com",
            display_name="Permission Repository Inactive Link",
            password_hash="inactive-link-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_user(
            user_id=disabled_service_admin_id,
            organization_user_id=disabled_user.id,
            email=f"{disabled_service_admin_id}@example.com",
            display_name="Permission Repository Disabled Service",
            password_hash="disabled-service-password-hash",
            status="disabled",
            created_at=now,
            updated_at=now,
        )
        repository.assign_user_service_role(
            user_id=disabled_service_admin_id,
            service_id=service_id,
            role="service_operator",
            assigned_by="unit-test",
            assigned_at=now,
        )
        repository.create_admin_user(
            user_id=unlinked_admin_id,
            email=f"{unlinked_admin_id}@example.com",
            display_name="Permission Repository Unlinked",
            password_hash="unlinked-password-hash",
            status="active",
            created_at=now,
            updated_at=now,
        )
        db_session.commit()

        summaries = repository.list_permission_admin_user_summaries(
            query=prefix,
            limit=10,
        )

        by_user_id = {summary.user.user_id: summary for summary in summaries}
        assert set(by_user_id) == {
            active_admin_id,
            inactive_link_admin_id,
            disabled_service_admin_id,
            unlinked_admin_id,
        }
        active_summary = by_user_id[active_admin_id]
        assert active_summary.user.email == f"{active_admin_id}@example.com"
        assert active_summary.user.display_name == "Permission Repository Active"
        assert active_summary.user.status == "active"
        assert active_summary.global_roles == ("system_admin",)
        assert isinstance(active_summary.is_last_active_system_admin, bool)
        assert active_summary.organization_user is active_user
        assert (
            active_summary.organization_user.department.dept_number
            == active_dept_number
        )
        active_service_role = active_summary.service_roles[0]
        assert (
            active_service_role.service_id,
            active_service_role.service_display_name,
            active_service_role.role,
            active_service_role.assigned_by,
            active_service_role.assigned_at,
        ) == (
            service_id,
            "Permission Repository Service",
            "auditor",
            "unit-test",
            now,
        )
        assert active_summary.risk_flags == () or active_summary.risk_flags == (
            "single_active_system_admin",
        )

        inactive_link_summary = by_user_id[inactive_link_admin_id]
        assert inactive_link_summary.organization_user is inactive_user
        assert "linked_inactive_organization_user" in inactive_link_summary.risk_flags
        assert "active_admin_without_roles" in inactive_link_summary.risk_flags

        disabled_service_summary = by_user_id[disabled_service_admin_id]
        assert "disabled_admin_has_service_roles" in disabled_service_summary.risk_flags
        assert disabled_service_summary.service_roles[0].role == "service_operator"

        unlinked_summary = by_user_id[unlinked_admin_id]
        assert unlinked_summary.organization_user is None
        assert "unlinked_admin_user" in unlinked_summary.risk_flags
        assert "active_admin_without_roles" in unlinked_summary.risk_flags

        assert {
            summary.user.user_id
            for summary in repository.list_permission_admin_user_summaries(
                query=prefix,
                status="disabled",
            )
        } == {disabled_service_admin_id}
        assert {
            summary.user.user_id
            for summary in repository.list_permission_admin_user_summaries(
                query=prefix,
                global_role="system_admin",
            )
        } == {active_admin_id}
        assert {
            summary.user.user_id
            for summary in repository.list_permission_admin_user_summaries(
                query=prefix,
                organization_link="unlinked",
            )
        } == {unlinked_admin_id}
        assert {
            summary.user.user_id
            for summary in repository.list_permission_admin_user_summaries(
                query=prefix,
                organization_use_yn="N",
            )
        } == {inactive_link_admin_id}
    finally:
        _purge_rows(
            db_session,
            admin_user_ids=[
                active_admin_id,
                inactive_link_admin_id,
                disabled_service_admin_id,
                unlinked_admin_id,
            ],
            service_ids=[service_id],
            dept_numbers=[active_dept_number, inactive_dept_number],
            user_numbers=[active_user_number, inactive_user_number, disabled_user_number],
        )


def _create_organization_user(
    repository: IntentRoutingRepository,
    *,
    dept_number: str,
    user_number: str,
    use_yn: str,
    now: datetime,
) -> models.OrganizationUser:
    department = repository.create_department(
        dept_number=dept_number,
        name=f"Department {dept_number}",
        use_yn="Y",
        created_by="unit-test",
        updated_by="unit-test",
        created_at=now,
        updated_at=now,
    )
    return repository.create_organization_user(
        user_number=user_number,
        name=f"User {user_number}",
        department_id=department.id,
        use_yn=use_yn,
        created_by="unit-test",
        updated_by="unit-test",
        created_at=now,
        updated_at=now,
    )


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
