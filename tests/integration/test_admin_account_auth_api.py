from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import get_admin_session
from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.main import create_app
from intent_routing.security.admin_passwords import hash_admin_password
from intent_routing.security.admin_sessions import ADMIN_SESSION_COOKIE_NAME


def test_admin_account_repository_flow_uses_global_and_service_scoped_roles(
    db_session: Session,
) -> None:
    service_id = "svc-account-auth-it"
    user_id = "admin-user-it"
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)

    _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)
    try:
        repository.create_service(
            service_id=service_id,
            display_name="Account Auth IT",
            environment="test",
            created_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        user = repository.create_admin_user(
            user_id=user_id,
            email="admin-auth-it@example.com",
            display_name="Admin Auth IT",
            password_hash="password-hash",
            status="active",
            admin_access_reason="repository auth integration test",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user.user_id,
            role="system_admin",
            assigned_by="bootstrap",
            assigned_at=now,
        )
        repository.assign_user_service_role(
            user_id=user.user_id,
            service_id=service_id,
            role="service_developer",
            assigned_by="bootstrap",
            assigned_at=now,
        )
        session = repository.create_admin_session(
            session_id="admin-session-it",
            user_id=user.user_id,
            token_hash="session-token-hash-it",
            created_at=now,
            expires_at=now + timedelta(hours=8),
        )

        db_session.commit()

        assert repository.get_admin_user(user_id) == user
        assert repository.get_admin_user_by_email("admin-auth-it@example.com") == user
        assert repository.get_admin_user_by_email("ADMIN-AUTH-IT@EXAMPLE.COM") == user
        assert [role.role for role in repository.list_admin_user_roles(user_id)] == [
            "system_admin"
        ]
        assert [
            role.role for role in repository.list_user_service_roles(user_id, service_id)
        ] == ["service_developer"]
        assert [
            (role.service_id, role.role)
            for role in repository.list_service_roles_for_user(user_id)
        ] == [(service_id, "service_developer")]
        assert (
            repository.get_admin_session_by_token_hash("session-token-hash-it")
            == session
        )
        session_context = repository.get_active_admin_session_context(
            "session-token-hash-it",
            now=now + timedelta(minutes=1),
        )
        assert session_context is not None
        assert session_context.user == user
        assert session_context.admin_session == session
        assert session_context.global_roles == frozenset({"system_admin"})
        assert [
            (role.service_id, role.role) for role in session_context.service_roles
        ] == [(service_id, "service_developer")]
        assert session.last_seen_at == now + timedelta(minutes=1)

        repository.update_admin_user_login(user, last_login_at=now + timedelta(minutes=2))
        repository.revoke_admin_session(
            session,
            revoked_at=now + timedelta(minutes=3),
        )
        db_session.commit()

        assert user.last_login_at == now + timedelta(minutes=2)
        assert user.updated_at == now + timedelta(minutes=2)
        assert session.revoked_at == now + timedelta(minutes=3)
        assert (
            repository.get_active_admin_session_context(
                "session-token-hash-it",
                now=now + timedelta(minutes=4),
            )
            is None
        )
        assert db_session.get(
            models.UserServiceRole,
            (user_id, "*", "system_admin"),
        ) is None
    finally:
        _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)


def test_admin_auth_api_bootstrap_login_me_logout_flow(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = "admin-auth-api-it"
    email = "Admin.Auth.API@example.com"
    service_id = "svc-admin-auth-api-it"
    password = "correct horse battery staple"
    now = datetime.now(UTC)

    _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)
    _purge_account_auth_rows(
        db_session,
        user_id="second-admin-auth-api-it",
        service_id=service_id,
    )
    db_session.execute(
        text("delete from admin_users where email_normalized = :email_normalized"),
        {"email_normalized": email.lower()},
    )
    db_session.commit()
    existing_system_admin = db_session.execute(
        text(
            "select user_id from admin_user_roles "
            "where role = 'system_admin' and user_id != :user_id limit 1"
        ),
        {"user_id": user_id},
    ).first()
    if existing_system_admin is not None:
        pytest.skip("bootstrap flow requires no pre-existing system_admin account")

    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-auth-api-it")
    client = TestClient(app)

    try:
        bootstrap_response = client.post(
            "/admin/v1/auth/bootstrap-admin",
            headers={"X-Admin-Token": "bootstrap-auth-api-it"},
            json={
                "user_id": user_id,
                "email": email,
                "display_name": "Admin Auth API",
                "password": password,
            },
        )

        assert bootstrap_response.status_code == 201
        bootstrap_body = bootstrap_response.json()
        assert bootstrap_body["user"]["email"] == email
        assert bootstrap_body["global_roles"] == ["system_admin"]
        assert "password_hash" not in str(bootstrap_body)
        assert "token_hash" not in str(bootstrap_body)

        second_bootstrap_response = client.post(
            "/admin/v1/auth/bootstrap-admin",
            headers={"X-Admin-Token": "bootstrap-auth-api-it"},
            json={
                "user_id": "second-admin-auth-api-it",
                "email": "second-admin-auth-api@example.com",
                "display_name": "Second Admin Auth API",
                "password": password,
            },
        )

        assert second_bootstrap_response.status_code == 409

        repository = IntentRoutingRepository(db_session)
        repository.create_service(
            service_id=service_id,
            display_name="Admin Auth API",
            environment="test",
            created_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        repository.assign_user_service_role(
            user_id=user_id,
            service_id=service_id,
            role="service_operator",
            assigned_by="integration-test",
            assigned_at=now,
        )
        db_session.commit()

        login_response = client.post(
            "/admin/v1/auth/login",
            json={"email": email.upper(), "password": password},
        )

        assert login_response.status_code == 200
        assert ADMIN_SESSION_COOKIE_NAME in login_response.cookies
        set_cookie = login_response.headers["set-cookie"]
        assert "HttpOnly" in set_cookie
        assert "SameSite=lax" in set_cookie
        login_body = login_response.json()
        assert login_body["user"]["user_id"] == user_id
        assert login_body["global_roles"] == ["system_admin"]
        assert login_body["service_roles"] == [
            {"service_id": service_id, "role": "service_operator"}
        ]
        assert password not in str(login_body)
        assert "password_hash" not in str(login_body)
        assert "token_hash" not in str(login_body)

        me_response = client.get("/admin/v1/auth/me")

        assert me_response.status_code == 200
        assert me_response.json()["user"]["user_id"] == user_id

        logout_response = client.post("/admin/v1/auth/logout")

        assert logout_response.status_code == 200
        assert logout_response.json() == {"success": True}
        assert ADMIN_SESSION_COOKIE_NAME not in client.cookies
        assert client.get("/admin/v1/auth/me").status_code == 401
    finally:
        _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)
        _purge_account_auth_rows(
            db_session,
            user_id="second-admin-auth-api-it",
            service_id=service_id,
        )


def test_admin_auth_login_rejects_active_admin_linked_to_inactive_organization_user(
    db_session: Session,
) -> None:
    user_id = "inactive-org-login-admin"
    email = "inactive-org-login@example.com"
    password = "correct horse battery staple"
    dept_number = "inactive-org-login-dept"
    user_number = "inactive-org-login-user"
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    client = TestClient(app)

    _purge_linked_org_admin_rows(
        db_session,
        user_id=user_id,
        email=email,
        dept_number=dept_number,
        user_number=user_number,
    )
    try:
        department = repository.create_department(
            dept_number=dept_number,
            name="보안운영부",
            use_yn="Y",
            created_by="integration-test",
            updated_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        organization_user = repository.create_organization_user(
            user_number=user_number,
            name="비활성관리자",
            department_id=department.id,
            use_yn="N",
            created_by="integration-test",
            updated_by="integration-test",
            created_at=now,
            updated_at=now,
        )
        repository.create_admin_user(
            user_id=user_id,
            email=email,
            display_name="Inactive Linked Admin",
            password_hash=hash_admin_password(password),
            status="active",
            organization_user_id=organization_user.id,
            admin_access_reason="inactive linked organization user login test",
            created_at=now,
            updated_at=now,
        )
        db_session.commit()

        response = client.post(
            "/admin/v1/auth/login",
            json={"email": email, "password": password},
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
        assert ADMIN_SESSION_COOKIE_NAME not in response.cookies
        assert ADMIN_SESSION_COOKIE_NAME not in response.headers.get("set-cookie", "")
        assert repository.get_admin_user_by_email(email) is not None
        assert repository.list_admin_user_roles(user_id) == []
        assert db_session.scalar(
            text("select count(*) from admin_sessions where user_id = :user_id"),
            {"user_id": user_id},
        ) == 0
    finally:
        _purge_linked_org_admin_rows(
            db_session,
            user_id=user_id,
            email=email,
            dept_number=dept_number,
            user_number=user_number,
        )


def test_application_admin_can_login_without_service_roles(db_session: Session) -> None:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    client = TestClient(app)
    repository = IntentRoutingRepository(db_session)
    suffix = uuid4().hex
    user_id = f"app-admin-{suffix}"
    email = f"app-admin-{suffix}@example.com"
    service_id = f"svc-app-admin-{suffix}"
    now = datetime.now(UTC)
    password = "application-admin-password"

    _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)
    try:
        user = repository.create_admin_user(
            user_id=user_id,
            email=email,
            display_name="Application Admin",
            password_hash=hash_admin_password(password),
            status="active",
            admin_access_reason="approved request",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user.user_id,
            role="application_admin",
            assigned_by="system-admin",
            assigned_at=now,
        )
        db_session.commit()

        response = client.post(
            "/admin/v1/auth/login",
            json={"email": user.email, "password": password},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["global_roles"] == ["application_admin"]
        assert body["service_roles"] == []
        assert password not in str(body)
        assert "password_hash" not in str(body)
        assert "token_hash" not in str(body)
    finally:
        _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)


def test_admin_user_without_access_role_cannot_login(db_session: Session) -> None:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    client = TestClient(app)
    repository = IntentRoutingRepository(db_session)
    suffix = uuid4().hex
    user_id = f"no-role-{suffix}"
    email = f"no-role-{suffix}@example.com"
    service_id = f"svc-no-role-{suffix}"
    now = datetime.now(UTC)
    password = "no-role-password"

    _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)
    try:
        user = repository.create_admin_user(
            user_id=user_id,
            email=email,
            display_name="No Role",
            password_hash=hash_admin_password(password),
            status="active",
            admin_access_reason="missing access role test",
            created_at=now,
            updated_at=now,
        )
        db_session.commit()

        response = client.post(
            "/admin/v1/auth/login",
            json={"email": user.email, "password": password},
        )

        assert response.status_code == 401
    finally:
        _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)


def test_auth_me_rejects_existing_session_after_application_admin_role_revocation(
    db_session: Session,
) -> None:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    client = TestClient(app)
    repository = IntentRoutingRepository(db_session)
    suffix = uuid4().hex
    user_id = f"revoked-app-admin-{suffix}"
    email = f"revoked-app-admin-{suffix}@example.com"
    service_id = f"svc-revoked-app-admin-{suffix}"
    now = datetime.now(UTC)
    password = "revoked-app-admin-password"

    _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)
    try:
        user = repository.create_admin_user(
            user_id=user_id,
            email=email,
            display_name="Revoked Application Admin",
            password_hash=hash_admin_password(password),
            status="active",
            admin_access_reason="session revocation test",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user.user_id,
            role="application_admin",
            assigned_by="system-admin",
            assigned_at=now,
        )
        db_session.commit()

        login_response = client.post(
            "/admin/v1/auth/login",
            json={"email": user.email, "password": password},
        )

        assert login_response.status_code == 200
        assert login_response.json()["global_roles"] == ["application_admin"]
        assert ADMIN_SESSION_COOKIE_NAME in client.cookies

        me_response = client.get("/admin/v1/auth/me")

        assert me_response.status_code == 200
        assert me_response.json()["global_roles"] == ["application_admin"]

        db_session.execute(
            text(
                "delete from admin_user_roles "
                "where user_id = :user_id and role = 'application_admin'"
            ),
            {"user_id": user.user_id},
        )
        db_session.commit()

        revoked_me_response = client.get("/admin/v1/auth/me")

        assert revoked_me_response.status_code == 401
    finally:
        _purge_account_auth_rows(db_session, user_id=user_id, service_id=service_id)


def test_admin_startup_provisioning_creates_login_account(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    email = "startup-login@example.com"
    password = "startup-login-password"

    _purge_admin_by_email(db_session, email)
    monkeypatch.setenv("ADMIN_SYSTEM_ADMIN_EMAIL", email)
    monkeypatch.setenv("ADMIN_SYSTEM_ADMIN_PASSWORD", password)
    monkeypatch.setenv("ADMIN_SYSTEM_ADMIN_DISPLAY_NAME", "Startup Login")

    @contextmanager
    def override_lifespan_session() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    monkeypatch.setattr(
        "intent_routing.main.session_scope",
        override_lifespan_session,
    )
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/admin/v1/auth/login",
                json={"email": email, "password": password},
            )

        assert response.status_code == 200
        assert response.json()["user"]["email"] == email
        assert response.json()["global_roles"] == ["system_admin"]
    finally:
        _purge_admin_by_email(db_session, email)


def _purge_admin_by_email(db_session: Session, email: str) -> None:
    existing = IntentRoutingRepository(db_session).get_admin_user_by_email(email)
    if existing is None:
        return
    db_session.execute(
        text("delete from user_service_roles where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from admin_user_roles where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from admin_sessions where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.commit()


def _purge_linked_org_admin_rows(
    db_session: Session,
    *,
    user_id: str,
    email: str,
    dept_number: str,
    user_number: str,
) -> None:
    _purge_admin_by_email(db_session, email)
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": user_id},
    )
    db_session.execute(
        text("delete from users where user_number = :user_number"),
        {"user_number": user_number},
    )
    db_session.execute(
        text("delete from departments where dept_number = :dept_number"),
        {"dept_number": dept_number},
    )
    db_session.commit()


def _purge_account_auth_rows(
    db_session: Session,
    *,
    user_id: str,
    service_id: str,
) -> None:
    db_session.execute(
        text("delete from user_service_roles where user_id = :user_id"),
        {"user_id": user_id},
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
