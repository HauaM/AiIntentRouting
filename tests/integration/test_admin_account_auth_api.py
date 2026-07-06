from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.db import models
from intent_routing.db.repositories import IntentRoutingRepository


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
