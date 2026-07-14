from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
    delete,
    inspect,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository


def test_organization_directory_models_expose_expected_tables_and_constraints() -> None:
    assert {
        "departments",
        "users",
        "admin_users",
    }.issubset(models.Base.metadata.tables)

    departments = models.Department.__table__
    users = models.OrganizationUser.__table__
    admin_users = models.AdminUser.__table__

    assert set(cast(Any, departments.primary_key).columns.keys()) == {"id"}
    assert _has_unique_constraint(departments, ["dept_number"])
    assert _has_check_constraint(departments, "ck_departments_use_yn")
    assert departments.c.use_yn.server_default is not None

    assert set(cast(Any, users.primary_key).columns.keys()) == {"id"}
    assert _has_unique_constraint(users, ["user_number"])
    assert _has_check_constraint(users, "ck_users_use_yn")
    assert _has_fk(users, ["department_id"], "departments")
    assert _has_index(users, "department_id")
    assert users.c.use_yn.server_default is not None

    assert "organization_user_id" in admin_users.c
    assert _has_unique_constraint(admin_users, ["organization_user_id"])
    assert _has_fk(admin_users, ["organization_user_id"], "users")


def test_organization_directory_migration_creates_required_tables_and_links() -> None:
    migration = Path("alembic/versions/0007_organization_directory.py").read_text()

    assert "departments" in migration
    assert "users" in migration
    assert "organization_user_id" in migration
    assert "uq_departments_dept_number" in migration
    assert "uq_users_user_number" in migration
    assert "ix_users_department_id" in migration
    assert "uq_admin_users_organization_user_id" in migration
    assert "fk_admin_users_organization_user_id_users" in migration


def test_organization_directory_tables_exist(db_session: Session) -> None:
    inspector = inspect(db_session.get_bind())

    assert "departments" in inspector.get_table_names()
    assert "users" in inspector.get_table_names()

    department_columns = {column["name"] for column in inspector.get_columns("departments")}
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    admin_columns = {column["name"] for column in inspector.get_columns("admin_users")}

    assert {
        "id",
        "dept_number",
        "name",
        "use_yn",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    } <= department_columns
    assert {
        "id",
        "user_number",
        "name",
        "department_id",
        "use_yn",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    } <= user_columns
    assert "organization_user_id" in admin_columns


def test_repository_exposes_organization_directory_helpers() -> None:
    assert {
        "create_department",
        "list_departments",
        "update_department",
        "deactivate_department",
        "create_organization_user",
        "list_organization_users",
        "update_organization_user",
        "deactivate_organization_user",
    }.issubset(dir(IntentRoutingRepository))


def test_repository_creates_and_lists_departments(db_session: Session) -> None:
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)
    dept_number = "0969"

    _purge_organization_directory_rows(db_session, dept_numbers=[dept_number])
    try:
        department = repository.create_department(
            dept_number=dept_number,
            name="IT지원부",
            use_yn="Y",
            created_by="admin-a",
            updated_by="admin-a",
            created_at=now,
            updated_at=now,
        )

        assert department.dept_number == dept_number
        assert (
            repository.list_departments(query="IT", use_yn="Y", limit=20)[0].id
            == department.id
        )
    finally:
        _purge_organization_directory_rows(db_session, dept_numbers=[dept_number])


def test_repository_rejects_duplicate_department_number(db_session: Session) -> None:
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)
    dept_number = "0969"
    payload = {
        "dept_number": dept_number,
        "name": "IT지원부",
        "use_yn": "Y",
        "created_by": "admin-a",
        "updated_by": "admin-a",
        "created_at": now,
        "updated_at": now,
    }

    _purge_organization_directory_rows(db_session, dept_numbers=[dept_number])
    try:
        repository.create_department(**payload)
        with pytest.raises(IntegrityError):
            repository.create_department(**payload)
    finally:
        db_session.rollback()
        _purge_organization_directory_rows(db_session, dept_numbers=[dept_number])


def test_repository_creates_and_lists_organization_users(db_session: Session) -> None:
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)
    dept_number = "0970"
    user_number = "21P0031"

    _purge_organization_directory_rows(
        db_session,
        dept_numbers=[dept_number],
        user_numbers=[user_number],
    )
    try:
        department = repository.create_department(
            dept_number=dept_number,
            name="총무부",
            use_yn="Y",
            created_by="admin-b",
            updated_by="admin-b",
            created_at=now,
            updated_at=now,
        )
        organization_user = repository.create_organization_user(
            user_number=user_number,
            name="홍길동",
            department_id=department.id,
            use_yn="Y",
            created_by="admin-b",
            updated_by="admin-b",
            created_at=now,
            updated_at=now,
        )

        listed_users = repository.list_organization_users(
            query="총무",
            department_id=department.id,
            use_yn="Y",
            limit=20,
        )

        assert len(listed_users) == 1
        assert listed_users[0].id == organization_user.id
    finally:
        _purge_organization_directory_rows(
            db_session,
            dept_numbers=[dept_number],
            user_numbers=[user_number],
        )


def test_repository_denies_session_for_inactive_linked_organization_user(
    db_session: Session,
) -> None:
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)
    dept_number = "0971"
    user_number = "21P0032"
    admin_user_id = "org-linked-admin"
    token_hash = "org-linked-admin-session"

    _purge_account_auth_rows(db_session, user_id=admin_user_id)
    _purge_organization_directory_rows(
        db_session,
        dept_numbers=[dept_number],
        user_numbers=[user_number],
    )
    try:
        department = repository.create_department(
            dept_number=dept_number,
            name="보안부",
            use_yn="Y",
            created_by="admin-c",
            updated_by="admin-c",
            created_at=now,
            updated_at=now,
        )
        organization_user = repository.create_organization_user(
            user_number=user_number,
            name="김보안",
            department_id=department.id,
            use_yn="N",
            created_by="admin-c",
            updated_by="admin-c",
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_user(
            user_id=admin_user_id,
            email="org-linked-admin@example.com",
            display_name="Org Linked Admin",
            password_hash="password-hash",
            status="active",
            organization_user_id=organization_user.id,
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_session(
            session_id="org-linked-admin-session-id",
            user_id=admin_user_id,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + timedelta(hours=8),
        )
        db_session.commit()

        assert repository.get_active_admin_session_context(
            token_hash,
            now=now + timedelta(minutes=1),
        ) is None
    finally:
        _purge_account_auth_rows(db_session, user_id=admin_user_id)
        _purge_organization_directory_rows(
            db_session,
            dept_numbers=[dept_number],
            user_numbers=[user_number],
        )


def _has_fk(table: Any, column_names: list[str], target_table: str) -> bool:
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and list(constraint.columns.keys()) == column_names
        and all(element.column.table.name == target_table for element in constraint.elements)
        for constraint in table.constraints
    )


def _has_index(table: Any, column_name: str) -> bool:
    return any(
        [column.name for column in index.columns] == [column_name] for index in table.indexes
    )


def _has_check_constraint(table: Any, name: str) -> bool:
    return any(
        isinstance(constraint, CheckConstraint) and constraint.name == name
        for constraint in table.constraints
    )


def _has_unique_constraint(table: Any, column_names: list[str]) -> bool:
    return any(
        isinstance(constraint, UniqueConstraint)
        and list(constraint.columns.keys()) == column_names
        for constraint in table.constraints
    )


def _purge_account_auth_rows(db_session: Session, *, user_id: str) -> None:
    db_session.execute(delete(models.AdminSession).where(models.AdminSession.user_id == user_id))
    db_session.execute(delete(models.AdminUserRole).where(models.AdminUserRole.user_id == user_id))
    db_session.execute(
        delete(models.UserServiceRole).where(models.UserServiceRole.user_id == user_id)
    )
    db_session.execute(delete(models.AdminUser).where(models.AdminUser.user_id == user_id))
    db_session.commit()


def _purge_organization_directory_rows(
    db_session: Session,
    *,
    dept_numbers: list[str],
    user_numbers: list[str] | None = None,
) -> None:
    user_numbers = user_numbers or []
    if dept_numbers:
        department_ids = list(
            db_session.scalars(
                select(models.Department.id).where(
                    models.Department.dept_number.in_(dept_numbers)
                )
            )
        )
        if department_ids:
            db_session.execute(
                delete(models.OrganizationUser).where(
                    models.OrganizationUser.department_id.in_(department_ids)
                )
            )
    if user_numbers:
        db_session.execute(
            delete(models.OrganizationUser).where(
                models.OrganizationUser.user_number.in_(user_numbers)
            )
        )
    if dept_numbers:
        db_session.execute(
            delete(models.Department).where(
                models.Department.dept_number.in_(dept_numbers)
            )
        )
    db_session.commit()
