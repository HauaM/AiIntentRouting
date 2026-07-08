from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.security.admin_passwords import (
    hash_admin_password,
    verify_admin_password,
)
from intent_routing.security.admin_provisioning import (
    AdminProvisioningConfig,
    configure_startup_system_admin,
    load_admin_provisioning_config,
)


def test_load_admin_provisioning_config_skips_when_credentials_absent() -> None:
    assert (
        load_admin_provisioning_config(
            {
                "ADMIN_SYSTEM_ADMIN_EMAIL": "",
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "",
            }
        )
        is None
    )


def test_load_admin_provisioning_config_skips_when_credentials_are_blank() -> None:
    assert (
        load_admin_provisioning_config(
            {
                "ADMIN_SYSTEM_ADMIN_EMAIL": "   ",
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "   ",
            }
        )
        is None
    )


def test_load_admin_provisioning_config_rejects_partial_credentials() -> None:
    with pytest.raises(
        ValueError,
        match="both ADMIN_SYSTEM_ADMIN_EMAIL and ADMIN_SYSTEM_ADMIN_PASSWORD",
    ):
        load_admin_provisioning_config(
            {"ADMIN_SYSTEM_ADMIN_EMAIL": "admin@example.com"}
        )


def test_load_admin_provisioning_config_rejects_blank_password() -> None:
    with pytest.raises(
        ValueError,
        match="both ADMIN_SYSTEM_ADMIN_EMAIL and ADMIN_SYSTEM_ADMIN_PASSWORD",
    ):
        load_admin_provisioning_config(
            {
                "ADMIN_SYSTEM_ADMIN_EMAIL": "admin@example.com",
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "        ",
            }
        )


def test_load_admin_provisioning_config_requires_minimum_password_length() -> None:
    with pytest.raises(ValueError, match="at least 8 characters"):
        load_admin_provisioning_config(
            {
                "ADMIN_SYSTEM_ADMIN_EMAIL": "admin@example.com",
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "short",
            }
        )


def test_load_admin_provisioning_config_defaults_display_name() -> None:
    config = load_admin_provisioning_config(
        {
            "ADMIN_SYSTEM_ADMIN_EMAIL": " Admin@Example.COM ",
            "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
        }
    )

    assert config == AdminProvisioningConfig(
        email="Admin@Example.COM",
        password="local-admin-password",
        display_name="Admin",
    )


def test_configure_startup_system_admin_skips_without_opening_session() -> None:
    @contextmanager
    def raising_session_scope() -> Iterator[Session]:
        raise AssertionError("session should not be opened without credentials")
        yield

    assert configure_startup_system_admin(raising_session_scope, env={}) == "skipped"


def test_configure_startup_system_admin_creates_missing_admin(
    db_session: Session,
) -> None:
    email = "startup-create@example.com"
    _purge_admin(db_session, email)
    try:
        result = configure_startup_system_admin(
            lambda: _session_scope(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
                "ADMIN_SYSTEM_ADMIN_DISPLAY_NAME": "Startup Create",
            },
        )
        repository = IntentRoutingRepository(db_session)
        user = repository.get_admin_user_by_email(email)

        assert result == "created"
        assert user is not None
        assert user.email == email
        assert user.display_name == "Startup Create"
        assert user.status == "active"
        assert verify_admin_password("local-admin-password", user.password_hash)
        assert [role.role for role in repository.list_admin_user_roles(user.user_id)] == [
            "system_admin"
        ]
    finally:
        _purge_admin(db_session, email)


def test_configure_startup_system_admin_leaves_matching_admin_unchanged(
    db_session: Session,
) -> None:
    email = "startup-match@example.com"
    now = datetime.now(UTC)
    _purge_admin(db_session, email)
    try:
        repository = IntentRoutingRepository(db_session)
        user = repository.create_admin_user(
            user_id="startup-match-admin",
            email=email,
            display_name="Startup Match",
            password_hash=hash_admin_password("local-admin-password"),
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user.user_id,
            role="system_admin",
            assigned_by="test",
            assigned_at=now,
        )
        original_hash = user.password_hash
        db_session.commit()

        result = configure_startup_system_admin(
            lambda: _session_scope(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
            },
        )

        assert result == "unchanged"
        assert user.password_hash == original_hash
        assert user.updated_at == now
    finally:
        _purge_admin(db_session, email)


def test_configure_startup_system_admin_updates_different_password(
    db_session: Session,
) -> None:
    email = "startup-update@example.com"
    now = datetime.now(UTC)
    _purge_admin(db_session, email)
    try:
        repository = IntentRoutingRepository(db_session)
        user = repository.create_admin_user(
            user_id="startup-update-admin",
            email=email,
            display_name="Startup Update",
            password_hash=hash_admin_password("old-admin-password"),
            status="active",
            created_at=now,
            updated_at=now,
        )
        repository.assign_admin_user_role(
            user_id=user.user_id,
            role="system_admin",
            assigned_by="test",
            assigned_at=now,
        )
        old_hash = user.password_hash
        db_session.commit()

        result = configure_startup_system_admin(
            lambda: _session_scope(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "new-admin-password",
            },
        )

        assert result == "updated"
        assert user.password_hash != old_hash
        assert verify_admin_password("new-admin-password", user.password_hash)
    finally:
        _purge_admin(db_session, email)


def test_configure_startup_system_admin_assigns_missing_system_admin_role(
    db_session: Session,
) -> None:
    email = "startup-role@example.com"
    now = datetime.now(UTC)
    _purge_admin(db_session, email)
    try:
        repository = IntentRoutingRepository(db_session)
        user = repository.create_admin_user(
            user_id="startup-role-admin",
            email=email,
            display_name="Startup Role",
            password_hash=hash_admin_password("local-admin-password"),
            status="active",
            created_at=now,
            updated_at=now,
        )
        db_session.commit()

        result = configure_startup_system_admin(
            lambda: _session_scope(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
            },
        )

        assert result == "role_assigned"
        assert [role.role for role in repository.list_admin_user_roles(user.user_id)] == [
            "system_admin"
        ]
    finally:
        _purge_admin(db_session, email)


def _purge_admin(db_session: Session, email: str) -> None:
    existing = IntentRoutingRepository(db_session).get_admin_user_by_email(email)
    if existing is None:
        return
    db_session.execute(
        text("delete from admin_user_roles where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from admin_sessions where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from user_service_roles where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.execute(
        text("delete from admin_users where user_id = :user_id"),
        {"user_id": existing.user_id},
    )
    db_session.commit()


@contextmanager
def _session_scope(db_session: Session) -> Iterator[Session]:
    try:
        yield db_session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
