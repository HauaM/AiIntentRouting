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
    owner_snapshot = _capture_system_admin_owner_state(db_session)
    _purge_admin(db_session, email)
    try:
        _set_system_admin_owner_present(db_session, owner_snapshot, present=False)
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
        _set_system_admin_owner_present(db_session, owner_snapshot, present=True)


def test_configure_startup_system_admin_leaves_matching_admin_unchanged(
    db_session: Session,
) -> None:
    email = "startup-match@example.com"
    now = datetime.now(UTC)
    owner_snapshot = _capture_system_admin_owner_state(db_session)
    _purge_admin(db_session, email)
    try:
        _set_system_admin_owner_present(db_session, owner_snapshot, present=False)
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
        _set_system_admin_owner_present(db_session, owner_snapshot, present=True)


def test_configure_startup_system_admin_updates_different_password(
    db_session: Session,
) -> None:
    email = "startup-update@example.com"
    now = datetime.now(UTC)
    owner_snapshot = _capture_system_admin_owner_state(db_session)
    _purge_admin(db_session, email)
    try:
        _set_system_admin_owner_present(db_session, owner_snapshot, present=False)
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
        _set_system_admin_owner_present(db_session, owner_snapshot, present=True)


def test_configure_startup_system_admin_refuses_different_email_when_owner_exists(
    db_session: Session,
) -> None:
    suffix = datetime.now(UTC).strftime("%H%M%S%f")
    configured_email = "startup-other@example.com"
    created_owner_email: str | None = None
    _purge_admin(db_session, configured_email)
    try:
        repository = IntentRoutingRepository(db_session)
        owner_user_id = db_session.scalar(
            text(
                "select user_id from admin_user_roles "
                "where role = 'system_admin' limit 1"
            )
        )
        if owner_user_id is None:
            now = datetime.now(UTC)
            owner_email = f"startup-owner-{suffix}@example.com"
            created_owner_email = owner_email
            owner = repository.create_admin_user(
                user_id=f"startup-existing-owner-{suffix}",
                email=owner_email,
                display_name="Startup Existing Owner",
                password_hash=hash_admin_password("existing-owner-password"),
                status="active",
                admin_access_reason="unit test setup",
                created_at=now,
                updated_at=now,
            )
            repository.assign_admin_user_role(
                user_id=owner.user_id,
                role="system_admin",
                assigned_by="test",
                assigned_at=now,
            )
            db_session.commit()
        else:
            owner = repository.get_admin_user(owner_user_id)
            assert owner is not None
        original_roles = [
            role.role for role in repository.list_admin_user_roles(owner.user_id)
        ]

        with pytest.raises(
            ValueError,
            match="Configured startup system_admin email does not match existing owner",
        ):
            configure_startup_system_admin(
                lambda: _session_scope(db_session),
                env={
                    "ADMIN_SYSTEM_ADMIN_EMAIL": configured_email,
                    "ADMIN_SYSTEM_ADMIN_PASSWORD": "new-admin-password",
                },
            )

        assert repository.get_admin_user_by_email(configured_email) is None
        assert [
            role.role for role in repository.list_admin_user_roles(owner.user_id)
        ] == original_roles
    finally:
        if created_owner_email is not None:
            _purge_admin(db_session, created_owner_email)
        _purge_admin(db_session, configured_email)


def test_configure_startup_system_admin_assigns_missing_system_admin_role(
    db_session: Session,
) -> None:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    owner_user_id = db_session.scalar(
        text("select user_id from admin_user_roles where role = 'system_admin' limit 1")
    )
    created_owner = owner_user_id is None
    owner_email = "startup-role@example.com"
    owner_user = None
    if created_owner:
        _purge_admin(db_session, owner_email)
    try:
        if owner_user_id is None:
            owner_user = repository.create_admin_user(
                user_id="startup-role-admin",
                email=owner_email,
                display_name="Startup Role",
                password_hash=hash_admin_password("local-admin-password"),
                status="active",
                admin_access_reason="unit test setup",
                created_at=now,
                updated_at=now,
            )
            repository.assign_admin_user_role(
                user_id=owner_user.user_id,
                role="system_admin",
                assigned_by="test",
                assigned_at=now,
            )
            db_session.commit()
        else:
            owner_user = repository.get_admin_user(owner_user_id)
            assert owner_user is not None
            repository.update_admin_user_password(
                owner_user,
                password_hash=hash_admin_password("local-admin-password"),
                updated_at=now,
            )
            db_session.commit()

        repository.delete_admin_user_role_by_key(owner_user.user_id, "system_admin")
        db_session.commit()

        result = configure_startup_system_admin(
            lambda: _session_scope(db_session),
            env={
                "ADMIN_SYSTEM_ADMIN_EMAIL": owner_user.email,
                "ADMIN_SYSTEM_ADMIN_PASSWORD": "local-admin-password",
            },
        )

        assert result == "role_assigned"
        assert "system_admin" in [
            role.role for role in repository.list_admin_user_roles(owner_user.user_id)
        ]
    finally:
        if created_owner:
            _purge_admin(db_session, owner_email)


def _capture_system_admin_owner_state(
    db_session: Session,
) -> tuple[str, list[str]] | None:
    repository = IntentRoutingRepository(db_session)
    owner_user_id = db_session.scalar(
        text("select user_id from admin_user_roles where role = 'system_admin' limit 1")
    )
    if owner_user_id is None:
        return None
    return (
        owner_user_id,
        [role.role for role in repository.list_admin_user_roles(owner_user_id)],
    )


def _set_system_admin_owner_present(
    db_session: Session,
    snapshot: tuple[str, list[str]] | None,
    *,
    present: bool,
) -> None:
    if snapshot is None:
        return
    repository = IntentRoutingRepository(db_session)
    user_id, original_roles = snapshot
    current_roles = {
        role.role for role in repository.list_admin_user_roles(user_id)
    }
    if present:
        if "system_admin" not in current_roles and "system_admin" in original_roles:
            repository.ensure_admin_user_role(
                user_id=user_id,
                role="system_admin",
                assigned_by="integration-test-restore",
                assigned_at=datetime.now(UTC),
            )
    else:
        if "system_admin" in current_roles:
            repository.delete_admin_user_role_by_key(user_id, "system_admin")
    db_session.commit()


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
