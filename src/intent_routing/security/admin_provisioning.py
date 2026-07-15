from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from os import environ
from uuid import uuid4

from sqlalchemy.orm import Session

from intent_routing.db.repositories import IntentRoutingRepository
from intent_routing.security.admin_passwords import (
    hash_admin_password,
    verify_admin_password,
)

MIN_STARTUP_ADMIN_PASSWORD_LENGTH = 8
STARTUP_ADMIN_LOCK_KEY = "startup-system-admin-provisioning"


@dataclass(frozen=True, slots=True)
class AdminProvisioningConfig:
    email: str
    password: str
    display_name: str


def load_admin_provisioning_config(
    env: Mapping[str, str] | None = None,
) -> AdminProvisioningConfig | None:
    values = environ if env is None else env
    email = values.get("ADMIN_SYSTEM_ADMIN_EMAIL", "").strip()
    password = values.get("ADMIN_SYSTEM_ADMIN_PASSWORD", "")
    has_password = bool(password.strip())
    display_name = values.get("ADMIN_SYSTEM_ADMIN_DISPLAY_NAME", "").strip()

    if not email and not has_password:
        return None
    if not email or not has_password:
        raise ValueError(
            "both ADMIN_SYSTEM_ADMIN_EMAIL and ADMIN_SYSTEM_ADMIN_PASSWORD must be set"
        )
    if len(password) < MIN_STARTUP_ADMIN_PASSWORD_LENGTH:
        raise ValueError("ADMIN_SYSTEM_ADMIN_PASSWORD must be at least 8 characters")

    return AdminProvisioningConfig(
        email=email,
        password=password,
        display_name=display_name or email.split("@", 1)[0],
    )


def configure_startup_system_admin(
    session_scope_factory: Callable[[], AbstractContextManager[Session]],
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    config = load_admin_provisioning_config(env)
    if config is None:
        return "skipped"

    with session_scope_factory() as session:
        repository = IntentRoutingRepository(session)
        repository.acquire_advisory_xact_lock(STARTUP_ADMIN_LOCK_KEY)
        now = datetime.now(UTC)
        user = repository.get_admin_user_by_email(config.email)

        if user is None:
            user = repository.create_admin_user(
                user_id=f"admin_{uuid4().hex}",
                email=config.email,
                display_name=config.display_name,
                password_hash=hash_admin_password(config.password),
                status="active",
                admin_access_reason="startup system admin provisioning",
                created_at=now,
                updated_at=now,
            )
            repository.ensure_admin_user_role(
                user_id=user.user_id,
                role="system_admin",
                assigned_by="startup-provisioning",
                assigned_at=now,
            )
            return "created"

        has_matching_password = verify_admin_password(config.password, user.password_hash)
        roles_before = {
            role.role for role in repository.list_admin_user_roles(user.user_id)
        }
        if not has_matching_password:
            repository.update_admin_user_password(
                user,
                password_hash=hash_admin_password(config.password),
                updated_at=now,
            )
        repository.ensure_admin_user_role(
            user_id=user.user_id,
            role="system_admin",
            assigned_by="startup-provisioning",
            assigned_at=now,
        )

        if not has_matching_password:
            return "updated"
        if "system_admin" not in roles_before:
            return "role_assigned"
        return "unchanged"
