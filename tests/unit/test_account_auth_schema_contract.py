from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository, normalize_admin_email


def test_account_auth_models_expose_expected_tables_and_constraints() -> None:
    assert {
        "admin_users",
        "admin_sessions",
        "admin_user_roles",
        "user_service_roles",
    }.issubset(models.Base.metadata.tables)

    admin_users = models.AdminUser.__table__
    admin_sessions = models.AdminSession.__table__
    admin_user_roles = models.AdminUserRole.__table__
    user_service_roles = models.UserServiceRole.__table__

    assert set(cast(Any, admin_users.primary_key).columns.keys()) == {"user_id"}
    assert _has_unique_constraint(admin_users, ["email"])
    assert _has_unique_constraint(admin_users, ["email_normalized"])
    assert _has_check_constraint(admin_users, "ck_admin_users_status")
    assert admin_users.c.status.server_default is not None

    assert set(cast(Any, admin_sessions.primary_key).columns.keys()) == {"session_id"}
    assert _has_unique_constraint(admin_sessions, ["token_hash"])
    assert _has_fk(admin_sessions, ["user_id"], "admin_users")

    assert set(cast(Any, admin_user_roles.primary_key).columns.keys()) == {
        "user_id",
        "role",
    }
    assert _has_fk(admin_user_roles, ["user_id"], "admin_users")
    assert _has_check_constraint(admin_user_roles, "ck_admin_user_roles_role")

    assert set(cast(Any, user_service_roles.primary_key).columns.keys()) == {
        "user_id",
        "service_id",
        "role",
    }
    assert _has_fk(user_service_roles, ["user_id"], "admin_users")
    assert _has_fk(user_service_roles, ["service_id"], "services")
    assert _has_check_constraint(user_service_roles, "ck_user_service_roles_role")


def test_account_auth_migration_uses_real_service_membership_not_wildcard() -> None:
    migration = Path(
        "alembic/versions/0005_account_auth_service_rbac.py"
    ).read_text()

    assert "admin_users" in migration
    assert "admin_sessions" in migration
    assert "admin_user_roles" in migration
    assert "user_service_roles" in migration
    assert "email_normalized" in migration
    assert "services.service_id" in migration
    assert "service_id='*'" not in migration
    assert '"*"' not in migration


def test_repository_exposes_account_auth_helpers() -> None:
    assert {
        "create_admin_user",
        "get_admin_user",
        "get_admin_user_by_email",
        "update_admin_user_login",
        "assign_admin_user_role",
        "admin_user_role_exists",
        "list_admin_user_roles",
        "create_admin_session",
        "get_admin_session_by_token_hash",
        "get_active_admin_session_context",
        "revoke_admin_session",
        "assign_user_service_role",
        "list_user_service_roles",
        "list_service_roles_for_user",
        "list_services",
        "list_services_for_user",
    }.issubset(dir(IntentRoutingRepository))


def test_repository_normalizes_email_and_rejects_unknown_roles() -> None:
    session = _FakeSession()
    repository = IntentRoutingRepository(cast(Session, session))

    user = repository.create_admin_user(
        user_id="admin-user",
        email=" Admin.User@Example.COM ",
        display_name="Admin User",
        password_hash="password-hash",
    )

    assert user.email == "Admin.User@Example.COM"
    assert user.email_normalized == "admin.user@example.com"
    assert user.status == "active"
    assert session.added[-1] is user

    with pytest.raises(ValueError, match="admin user role"):
        repository.assign_admin_user_role(
            user_id="admin-user",
            role="service_developer",
            assigned_by="bootstrap",
            assigned_at=object(),
        )

    with pytest.raises(ValueError, match="user service role"):
        repository.assign_user_service_role(
            user_id="admin-user",
            service_id="svc-test",
            role="service_admin",
            assigned_by="bootstrap",
            assigned_at=object(),
        )


def test_normalize_admin_email_rejects_blank_values() -> None:
    assert normalize_admin_email(" Admin@Example.COM ") == "admin@example.com"

    with pytest.raises(ValueError, match="email must not be blank"):
        normalize_admin_email("  ")


def _has_unique_constraint(table: Any, column_names: list[str]) -> bool:
    return any(
        isinstance(constraint, UniqueConstraint)
        and list(constraint.columns.keys()) == column_names
        for constraint in table.constraints
    )


def _has_fk(table: Any, column_names: list[str], target_table: str) -> bool:
    return any(
        isinstance(constraint, ForeignKeyConstraint)
        and list(constraint.columns.keys()) == column_names
        and all(element.column.table.name == target_table for element in constraint.elements)
        for constraint in table.constraints
    )


def _has_check_constraint(table: Any, name: str) -> bool:
    return any(
        isinstance(constraint, CheckConstraint) and constraint.name == name
        for constraint in table.constraints
    )


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        pass
