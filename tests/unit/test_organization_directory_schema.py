from pathlib import Path
from typing import Any, cast

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint, inspect

from intent_routing.db import models


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


def test_organization_directory_tables_exist(db_session):
    inspector = inspect(db_session.bind)

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
