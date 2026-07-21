from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict, cast
from uuid import uuid4

import pytest
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository, normalize_admin_email


class _AdminUserValues(TypedDict):
    user_id: str
    email: str
    display_name: str
    password_hash: str
    admin_access_reason: str
    status: str
    created_at: datetime
    updated_at: datetime


def test_account_auth_models_expose_expected_tables_and_constraints() -> None:
    assert {
        "admin_users",
        "admin_access_requests",
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


def test_alembic_revision_ids_fit_default_version_table_and_0008_leaves_it_alone() -> None:
    migration_dir = Path("alembic/versions")
    revision_files = sorted(migration_dir.glob("*.py"))
    revisions: dict[str, str] = {}

    for path in revision_files:
        migration = path.read_text()
        revision_line = next(
            line for line in migration.splitlines() if line.startswith("revision: str = ")
        )
        revision = revision_line.split(" = ", maxsplit=1)[1].strip().strip('"')
        revisions[path.name] = revision

    assert all(len(revision) <= 32 for revision in revisions.values())
    assert len(revisions["0008_application_admin_approval_rbac.py"]) <= 32

    migration_0008 = Path(
        "alembic/versions/0008_application_admin_approval_rbac.py"
    ).read_text()
    assert (
        'op.alter_column("alembic_version", "version_num", type_=sa.Text())'
        not in migration_0008
    )


def test_repository_exposes_account_auth_helpers() -> None:
    assert {
        "create_admin_user",
        "get_admin_user",
        "get_admin_user_by_email",
        "update_admin_user_login",
        "update_admin_user_password",
        "assign_admin_user_role",
        "ensure_admin_user_role",
        "admin_user_role_exists",
        "list_admin_user_roles",
        "create_admin_session",
        "get_admin_session_by_token_hash",
        "get_active_admin_session_context",
        "revoke_admin_session",
        "assign_user_service_role",
        "list_user_service_roles",
        "list_service_roles_for_user",
        "list_admin_users",
        "list_service_member_roles",
        "get_user_service_role",
        "ensure_user_service_role",
        "delete_user_service_role_by_key",
        "delete_user_service_role",
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
        admin_access_reason="Needs admin UI access for service support.",
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


def test_repository_list_admin_users_builds_query_and_clamps_limit() -> None:
    session = _FakeSession()
    repository = IntentRoutingRepository(cast(Session, session))

    assert repository.list_admin_users(query=" MixedCase ", limit=100) == []

    assert session.scalars_statement is not None
    compiled = str(
        session.scalars_statement.compile(compile_kwargs={"literal_binds": True})
    )
    assert "LIMIT 25" in compiled
    assert "%mixedcase%" in compiled
    assert "lower(admin_users.email_normalized)" in compiled
    assert "lower(admin_users.email)" in compiled
    assert "lower(admin_users.display_name)" in compiled
    assert "lower(admin_users.user_id)" in compiled


def test_repository_ensure_user_service_role_rejects_blank_user_id() -> None:
    repository = IntentRoutingRepository(cast(Session, _FakeSession()))

    with pytest.raises(ValueError, match="user service role user_id"):
        repository.ensure_user_service_role(
            user_id=" ",
            service_id="svc-test",
            role="service_owner",
            assigned_by="test",
            assigned_at=object(),
        )


def test_repository_ensure_user_service_role_rejects_blank_service_id() -> None:
    repository = IntentRoutingRepository(cast(Session, _FakeSession()))

    with pytest.raises(ValueError, match="user service role service_id"):
        repository.ensure_user_service_role(
            user_id="admin-user",
            service_id=" ",
            role="service_owner",
            assigned_by="test",
            assigned_at=object(),
        )


def test_repository_get_user_service_role_rejects_unknown_role() -> None:
    repository = IntentRoutingRepository(cast(Session, _FakeSession()))

    with pytest.raises(ValueError, match="user service role"):
        repository.get_user_service_role(
            "admin-user",
            "svc-test",
            "service_admin",
        )


def test_repository_delete_user_service_role_by_key_locks_and_deletes_row() -> None:
    session = _FakeSession()
    role_record = models.UserServiceRole(
        user_id="admin-user",
        service_id="svc-test",
        role="service_owner",
        assigned_by="other-admin",
        assigned_at=datetime(2026, 7, 10, tzinfo=UTC),
    )
    session.scalar_result = role_record
    repository = IntentRoutingRepository(cast(Session, session))

    deleted_role = repository.delete_user_service_role_by_key(
        "admin-user",
        "svc-test",
        "service_owner",
    )

    assert deleted_role is role_record
    assert session.scalar_statement is not None
    assert session.scalar_statement._for_update_arg is not None
    assert session.deleted == [role_record]
    assert session.flush_count == 1


def test_repository_delete_user_service_role_by_key_returns_none_for_missing_role() -> None:
    session = _FakeSession()
    repository = IntentRoutingRepository(cast(Session, session))

    assert (
        repository.delete_user_service_role_by_key(
            "admin-user",
            "svc-test",
            "service_owner",
        )
        is None
    )
    assert session.scalar_statement is not None
    assert session.scalar_statement._for_update_arg is not None
    assert session.deleted == []
    assert session.flush_count == 0


def test_repository_delete_user_service_role_by_key_rejects_unknown_role() -> None:
    repository = IntentRoutingRepository(cast(Session, _FakeSession()))

    with pytest.raises(ValueError, match="user service role"):
        repository.delete_user_service_role_by_key(
            "admin-user",
            "svc-test",
            "service_admin",
        )


def test_repository_ensure_user_service_role_refetches_after_integrity_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    repository = IntentRoutingRepository(cast(Session, session))
    existing_role = models.UserServiceRole(
        user_id="admin-user",
        service_id="svc-test",
        role="service_owner",
        assigned_by="other-admin",
        assigned_at=datetime(2026, 7, 10, tzinfo=UTC),
    )
    lookup_results: Iterator[models.UserServiceRole | None] = iter(
        [None, existing_role]
    )

    def fake_get_user_service_role(
        user_id: str,
        service_id: str,
        role: str,
    ) -> models.UserServiceRole | None:
        assert (user_id, service_id, role) == (
            "admin-user",
            "svc-test",
            "service_owner",
        )
        return next(lookup_results)

    def raise_integrity_error(_role_record: models.UserServiceRole) -> None:
        raise IntegrityError("insert user_service_roles", {}, Exception("duplicate"))

    monkeypatch.setattr(repository, "get_user_service_role", fake_get_user_service_role)
    monkeypatch.setattr(repository, "_add_and_flush", raise_integrity_error)

    role_record, created = repository.ensure_user_service_role_with_created(
        user_id="admin-user",
        service_id="svc-test",
        role="service_owner",
        assigned_by="session-admin",
        assigned_at=datetime(2026, 7, 10, 1, 2, 3, tzinfo=UTC),
    )

    assert role_record is existing_role
    assert created is False
    assert session.nested_transactions == 1


def test_repository_updates_admin_password_and_ensures_role(
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    user_id = "admin-password-sync"
    repository = IntentRoutingRepository(db_session)

    db_session.execute(
        text("delete from admin_user_roles where role = 'system_admin'"),
    )
    db_session.execute(
        text("delete from admin_user_roles where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.commit()

    try:
        user = repository.create_admin_user(
            user_id=user_id,
            email="password-sync@example.com",
            display_name="Password Sync",
            password_hash="old-password-hash",
            admin_access_reason="Approved to operate assigned application services.",
            status="active",
            created_at=now,
            updated_at=now,
        )

        repository.update_admin_user_password(
            user,
            password_hash="new-password-hash",
            updated_at=now,
        )
        role = repository.ensure_admin_user_role(
            user_id=user_id,
            role="system_admin",
            assigned_by="startup-provisioning",
            assigned_at=now,
        )
        duplicate_role = repository.ensure_admin_user_role(
            user_id=user_id,
            role="system_admin",
            assigned_by="startup-provisioning",
            assigned_at=now,
        )
        db_session.commit()

        assert user.password_hash == "new-password-hash"
        assert user.updated_at == now
        assert role is duplicate_role
        assert [role.role for role in repository.list_admin_user_roles(user_id)] == [
            "system_admin"
        ]
    finally:
        db_session.execute(
            text("delete from admin_user_roles where role = 'system_admin'"),
        )
        db_session.execute(
            text("delete from admin_user_roles where user_id = :user_id"),
            {"user_id": user_id},
        )
        db_session.execute(
            text("delete from admin_users where user_id = :user_id"),
            {"user_id": user_id},
        )
        db_session.commit()


def test_repository_searches_admin_users_without_secret_fields(
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    users: list[_AdminUserValues] = [
        {
            "user_id": "repo-search-alpha-user",
            "email": "Repo.Search.Alpha@example.com",
            "display_name": "Repository Alpha Owner",
            "password_hash": "alpha-password-hash",
            "admin_access_reason": "Approved for alpha service administration.",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        },
        {
            "user_id": "repo-search-beta-user",
            "email": "repo.search.beta@example.com",
            "display_name": "Repository Beta Reviewer",
            "password_hash": "beta-password-hash",
            "admin_access_reason": "Approved for beta service review work.",
            "status": "disabled",
            "created_at": now,
            "updated_at": now,
        },
    ]

    _purge_admin_users(db_session, [user["user_id"] for user in users])

    try:
        for user in users:
            repository.create_admin_user(**user)
        db_session.commit()

        email_matches = repository.list_admin_users(query="SEARCH.ALPHA")
        display_name_matches = repository.list_admin_users(query="beTa rEvIeWeR")
        user_id_matches = repository.list_admin_users(query="alpha-user")

        assert [user.user_id for user in email_matches] == ["repo-search-alpha-user"]
        assert [user.user_id for user in display_name_matches] == [
            "repo-search-beta-user"
        ]
        assert [user.user_id for user in user_id_matches] == ["repo-search-alpha-user"]
        assert all(isinstance(user, models.AdminUser) for user in email_matches)

        non_secret_rows = [
            {
                "user_id": user.user_id,
                "status": user.status,
                "email": user.email,
                "display_name": user.display_name,
            }
            for user in email_matches + display_name_matches
        ]
        assert non_secret_rows == [
            {
                "user_id": "repo-search-alpha-user",
                "status": "active",
                "email": "Repo.Search.Alpha@example.com",
                "display_name": "Repository Alpha Owner",
            },
            {
                "user_id": "repo-search-beta-user",
                "status": "disabled",
                "email": "repo.search.beta@example.com",
                "display_name": "Repository Beta Reviewer",
            },
        ]
    finally:
        _purge_admin_users(db_session, [user["user_id"] for user in users])


def test_repository_ensures_and_deletes_user_service_roles(
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    user_id = "repo-membership-user"
    service_id = "repo-membership-service"
    repository = IntentRoutingRepository(db_session)

    _purge_service_membership_rows(db_session, user_id=user_id, service_id=service_id)

    try:
        repository.create_admin_user(
            user_id=user_id,
            email="repo.membership@example.com",
            display_name="Repository Membership",
            password_hash="membership-password-hash",
            admin_access_reason="Approved for membership management test coverage.",
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.create_service(
            service_id=service_id,
            display_name="Repository Membership Service",
            max_input_tokens=256,
            status="active",
            created_by="test",
            created_at=now,
            updated_at=now,
        )

        role = repository.ensure_user_service_role(
            user_id=user_id,
            service_id=service_id,
            role="service_owner",
            assigned_by="test",
            assigned_at=now,
        )
        duplicate_role = repository.ensure_user_service_role(
            user_id=user_id,
            service_id=service_id,
            role="service_owner",
            assigned_by="test",
            assigned_at=now,
        )
        db_session.commit()

        assert role is duplicate_role
        assert (
            role.user_id,
            role.service_id,
            role.role,
        ) == (user_id, service_id, "service_owner")
        assert [
            (member_role.user_id, member_role.role)
            for member_role in repository.list_service_member_roles(service_id)
        ] == [(user_id, "service_owner")]
        assert repository.get_user_service_role(
            user_id,
            service_id,
            "service_owner",
        ) is role

        repository.delete_user_service_role(role)
        db_session.commit()

        assert repository.get_user_service_role(
            user_id,
            service_id,
            "service_owner",
        ) is None
    finally:
        _purge_service_membership_rows(db_session, user_id=user_id, service_id=service_id)


def test_admin_user_roles_allow_application_admin_and_single_system_admin_index(
    db_session: Session,
) -> None:
    inspector = inspect(db_session.get_bind())
    admin_user_roles = cast(Any, models.AdminUserRole.__table__)

    assert _has_check_constraint(admin_user_roles, "ck_admin_user_roles_role")
    check_sql = " ".join(
        constraint.sqltext.text
        for constraint in admin_user_roles.constraints
        if getattr(constraint, "name", "") == "ck_admin_user_roles_role"
    )
    assert "system_admin" in check_sql
    assert "application_admin" in check_sql

    index_names = {index["name"] for index in inspector.get_indexes("admin_user_roles")}
    assert "uq_admin_user_roles_single_system_admin" in index_names


def test_admin_access_requests_schema_exists(db_session: Session) -> None:
    inspector = inspect(db_session.get_bind())
    assert "admin_access_requests" in inspector.get_table_names()

    columns = {
        column["name"] for column in inspector.get_columns("admin_access_requests")
    }
    assert {
        "request_id",
        "user_number",
        "name",
        "department_id",
        "email",
        "email_normalized",
        "password_hash",
        "access_reason",
        "status",
        "requested_at",
        "decided_at",
        "decided_by",
        "decision_reason",
        "created_user_id",
        "created_admin_user_id",
    } <= columns

    admin_columns = {column["name"] for column in inspector.get_columns("admin_users")}
    assert "admin_access_reason" in admin_columns


def test_admin_access_requests_allow_history_but_reject_duplicate_pending_email(
    db_session: Session,
) -> None:
    department_id = _create_department(db_session, dept_number="TASK2-REQ-EMAIL")
    email = "task2.pending.email@example.com"
    normalized_email = "task2.pending.email@example.com"
    inserted_request_ids: list[str] = []

    try:
        for status in ("approved", "rejected"):
            request_id = str(uuid4())
            inserted_request_ids.append(request_id)
            db_session.execute(
                text(
                    """
                    insert into admin_access_requests (
                        request_id,
                        user_number,
                        name,
                        department_id,
                        email,
                        email_normalized,
                        password_hash,
                        access_reason,
                        status,
                        requested_at
                    ) values (
                        :request_id,
                        :user_number,
                        :name,
                        :department_id,
                        :email,
                        :email_normalized,
                        :password_hash,
                        :access_reason,
                        :status,
                        :requested_at
                    )
                    """
                ),
                {
                    "request_id": request_id,
                    "user_number": f"TASK2-HISTORY-{status.upper()}",
                    "name": f"Task 2 History {status.title()}",
                    "department_id": department_id,
                    "email": email,
                    "email_normalized": normalized_email,
                    "password_hash": None,
                    "access_reason": "Task 2 history coverage.",
                    "status": status,
                    "requested_at": datetime.now(UTC),
                },
            )

        pending_request_id = str(uuid4())
        inserted_request_ids.append(pending_request_id)
        db_session.execute(
            text(
                """
                insert into admin_access_requests (
                    request_id,
                    user_number,
                    name,
                    department_id,
                    email,
                    email_normalized,
                    password_hash,
                    access_reason,
                    status,
                    requested_at
                ) values (
                    :request_id,
                    :user_number,
                    :name,
                    :department_id,
                    :email,
                    :email_normalized,
                    :password_hash,
                    :access_reason,
                    :status,
                    :requested_at
                )
                """
            ),
            {
                "request_id": pending_request_id,
                "user_number": "TASK2-PENDING-EMAIL-ONE",
                "name": "Task 2 Pending Email One",
                "department_id": department_id,
                "email": email,
                "email_normalized": normalized_email,
                "password_hash": "pending-password-hash",
                "access_reason": "Task 2 pending uniqueness coverage.",
                "status": "pending",
                "requested_at": datetime.now(UTC),
            },
        )
        db_session.commit()

        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    """
                    insert into admin_access_requests (
                        request_id,
                        user_number,
                        name,
                        department_id,
                        email,
                        email_normalized,
                        password_hash,
                        access_reason,
                        status,
                        requested_at
                    ) values (
                        :request_id,
                        :user_number,
                        :name,
                        :department_id,
                        :email,
                        :email_normalized,
                        :password_hash,
                        :access_reason,
                        :status,
                        :requested_at
                    )
                    """
                ),
                {
                    "request_id": str(uuid4()),
                    "user_number": "TASK2-PENDING-EMAIL-TWO",
                    "name": "Task 2 Pending Email Two",
                    "department_id": department_id,
                    "email": email,
                    "email_normalized": normalized_email,
                    "password_hash": "pending-password-hash-2",
                    "access_reason": "Task 2 pending uniqueness coverage.",
                    "status": "pending",
                    "requested_at": datetime.now(UTC),
                },
            )
            db_session.commit()
        db_session.rollback()
    finally:
        db_session.rollback()
        _purge_admin_access_requests(db_session, request_ids=inserted_request_ids)
        _purge_departments(db_session, department_ids=[department_id])


def test_admin_access_requests_reject_duplicate_pending_user_number(
    db_session: Session,
) -> None:
    department_id = _create_department(db_session, dept_number="TASK2-REQ-USER-NUM")
    user_number = "TASK2-PENDING-USER-NUMBER"
    inserted_request_ids: list[str] = []

    try:
        first_request_id = str(uuid4())
        inserted_request_ids.append(first_request_id)
        db_session.execute(
            text(
                """
                insert into admin_access_requests (
                    request_id,
                    user_number,
                    name,
                    department_id,
                    email,
                    email_normalized,
                    password_hash,
                    access_reason,
                    status,
                    requested_at
                ) values (
                    :request_id,
                    :user_number,
                    :name,
                    :department_id,
                    :email,
                    :email_normalized,
                    :password_hash,
                    :access_reason,
                    :status,
                    :requested_at
                )
                """
            ),
            {
                "request_id": first_request_id,
                "user_number": user_number,
                "name": "Task 2 Pending User Number One",
                "department_id": department_id,
                "email": "task2.pending.user.number.one@example.com",
                "email_normalized": "task2.pending.user.number.one@example.com",
                "password_hash": "pending-user-number-hash-one",
                "access_reason": "Task 2 pending user number coverage.",
                "status": "pending",
                "requested_at": datetime.now(UTC),
            },
        )
        db_session.commit()

        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    """
                    insert into admin_access_requests (
                        request_id,
                        user_number,
                        name,
                        department_id,
                        email,
                        email_normalized,
                        password_hash,
                        access_reason,
                        status,
                        requested_at
                    ) values (
                        :request_id,
                        :user_number,
                        :name,
                        :department_id,
                        :email,
                        :email_normalized,
                        :password_hash,
                        :access_reason,
                        :status,
                        :requested_at
                    )
                    """
                ),
                {
                    "request_id": str(uuid4()),
                    "user_number": user_number,
                    "name": "Task 2 Pending User Number Two",
                    "department_id": department_id,
                    "email": "task2.pending.user.number.two@example.com",
                    "email_normalized": "task2.pending.user.number.two@example.com",
                    "password_hash": "pending-user-number-hash-two",
                    "access_reason": "Task 2 pending user number coverage.",
                    "status": "pending",
                    "requested_at": datetime.now(UTC),
                },
            )
            db_session.commit()
        db_session.rollback()
    finally:
        db_session.rollback()
        _purge_admin_access_requests(db_session, request_ids=inserted_request_ids)
        _purge_departments(db_session, department_ids=[department_id])


def test_admin_access_requests_require_password_hash_only_while_pending(
    db_session: Session,
) -> None:
    department_id = _create_department(db_session, dept_number="TASK2-REQ-PASSWORD")
    inserted_request_ids: list[str] = []

    try:
        decided_request_id = str(uuid4())
        inserted_request_ids.append(decided_request_id)
        db_session.execute(
            text(
                """
                insert into admin_access_requests (
                    request_id,
                    user_number,
                    name,
                    department_id,
                    email,
                    email_normalized,
                    password_hash,
                    access_reason,
                    status,
                    requested_at
                ) values (
                    :request_id,
                    :user_number,
                    :name,
                    :department_id,
                    :email,
                    :email_normalized,
                    :password_hash,
                    :access_reason,
                    :status,
                    :requested_at
                )
                """
            ),
            {
                "request_id": decided_request_id,
                "user_number": "TASK2-DECIDED-PASSWORD-NULL",
                "name": "Task 2 Decided Password Null",
                "department_id": department_id,
                "email": "task2.decided.password.null@example.com",
                "email_normalized": "task2.decided.password.null@example.com",
                "password_hash": None,
                "access_reason": "Task 2 decided password retention coverage.",
                "status": "approved",
                "requested_at": datetime.now(UTC),
            },
        )
        db_session.commit()

        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    """
                    insert into admin_access_requests (
                        request_id,
                        user_number,
                        name,
                        department_id,
                        email,
                        email_normalized,
                        password_hash,
                        access_reason,
                        status,
                        requested_at
                    ) values (
                        :request_id,
                        :user_number,
                        :name,
                        :department_id,
                        :email,
                        :email_normalized,
                        :password_hash,
                        :access_reason,
                        :status,
                        :requested_at
                    )
                    """
                ),
                {
                    "request_id": str(uuid4()),
                    "user_number": "TASK2-PENDING-PASSWORD-NULL",
                    "name": "Task 2 Pending Password Null",
                    "department_id": department_id,
                    "email": "task2.pending.password.null@example.com",
                    "email_normalized": "task2.pending.password.null@example.com",
                    "password_hash": None,
                    "access_reason": "Task 2 pending password retention coverage.",
                    "status": "pending",
                    "requested_at": datetime.now(UTC),
                },
            )
            db_session.commit()
        db_session.rollback()
    finally:
        db_session.rollback()
        _purge_admin_access_requests(db_session, request_ids=inserted_request_ids)
        _purge_departments(db_session, department_ids=[department_id])


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
        self.scalars_statement: Any | None = None
        self.scalar_statement: Any | None = None
        self.scalar_result: Any | None = None
        self.deleted: list[Any] = []
        self.flush_count = 0
        self.nested_transactions = 0

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    def flush(self) -> None:
        self.flush_count += 1

    def begin_nested(self) -> "_FakeNestedTransaction":
        self.nested_transactions += 1
        return _FakeNestedTransaction()

    def get(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def delete(self, instance: Any) -> None:
        self.deleted.append(instance)

    def scalar(self, statement: Any) -> Any | None:
        self.scalar_statement = statement
        return self.scalar_result

    def scalars(self, statement: Any) -> "_EmptyScalars":
        self.scalars_statement = statement
        return _EmptyScalars()


class _FakeNestedTransaction:
    def __enter__(self) -> "_FakeNestedTransaction":
        return self

    def __exit__(self, *_exc_info: object) -> Literal[False]:
        return False


class _EmptyScalars:
    def __iter__(self) -> Iterator[Any]:
        return iter(())


def _purge_admin_users(db_session: Session, user_ids: list[str]) -> None:
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
    db_session.commit()


def _purge_service_membership_rows(
    db_session: Session,
    *,
    user_id: str,
    service_id: str,
) -> None:
    db_session.execute(
        text(
            "delete from user_service_roles "
            "where user_id = :user_id or service_id = :service_id"
        ),
        {"user_id": user_id, "service_id": service_id},
    )
    db_session.execute(
        text("delete from admin_user_roles where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from admin_sessions where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from services where service_id = :service_id"),
        {"service_id": service_id},
    )
    db_session.commit()


def _create_department(db_session: Session, *, dept_number: str) -> str:
    department_id = str(uuid4())
    unique_dept_number = f"{dept_number}-{uuid4()}"
    now = datetime.now(UTC)
    db_session.execute(
        text(
            """
            insert into departments (
                id,
                dept_number,
                name,
                use_yn,
                created_by,
                updated_by,
                created_at,
                updated_at
            ) values (
                :id,
                :dept_number,
                :name,
                'Y',
                'test',
                'test',
                :created_at,
                :updated_at
            )
            """
        ),
        {
            "id": department_id,
            "dept_number": unique_dept_number,
            "name": f"{dept_number} Department",
            "created_at": now,
            "updated_at": now,
        },
    )
    db_session.commit()
    return department_id


def _purge_admin_access_requests(db_session: Session, *, request_ids: list[str]) -> None:
    if not request_ids:
        return

    db_session.execute(
        text("delete from admin_access_requests where request_id = any(:request_ids)"),
        {"request_ids": request_ids},
    )
    db_session.commit()


def _purge_departments(db_session: Session, *, department_ids: list[str]) -> None:
    if not department_ids:
        return

    db_session.execute(
        text("delete from departments where id = any(:department_ids)"),
        {"department_ids": department_ids},
    )
    db_session.commit()
