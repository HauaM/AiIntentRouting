from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.orm import Session

from intent_routing.api import admin_dependencies
from intent_routing.api.admin_dependencies import require_admin_context
from intent_routing.security.admin_auth import (
    AdminContext,
    require_trusted_header_admin_context,
)


def test_service_role_on_one_service_does_not_authorize_another_service() -> None:
    context = AdminContext(
        actor_id="developer-user",
        roles=frozenset(),
        service_scope=frozenset({"svc-a", "svc-b"}),
        all_service_scopes=False,
        service_roles={"svc-a": frozenset({"service_developer"})},
    )

    assert context.has_service_role("svc-a", "service_developer")
    assert not context.has_service_role("svc-b", "service_developer")


def test_system_admin_has_all_service_roles_globally() -> None:
    context = AdminContext(
        actor_id="admin-user",
        roles=frozenset({"system_admin"}),
        service_scope=frozenset(),
        all_service_scopes=True,
        service_roles={},
    )

    assert context.has_service_role("svc-any", "service_developer")
    assert context.has_any_service_role("svc-any", {"auditor", "service_operator"})


def test_trusted_headers_scope_service_roles_to_named_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")

    context = require_trusted_header_admin_context(
        admin_token="local-admin-token",
        actor_id="developer-user",
        actor_roles="service_developer",
        service_scope="svc-a",
    )

    assert context.roles == frozenset()
    assert context.has_service_role("svc-a", "service_developer")
    assert not context.has_service_role("svc-b", "service_developer")


def test_session_cookie_takes_precedence_over_trusted_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSession:
        committed = False

        def commit(self) -> None:
            self.committed = True

    class FakeRepository:
        def __init__(self, session: FakeSession) -> None:
            self.session = session

        def get_active_admin_session_context(
            self,
            token_hash: str,
            *,
            now: object,
        ) -> SimpleNamespace:
            return SimpleNamespace(
                user=SimpleNamespace(user_id="session-user"),
                global_roles=frozenset(),
                service_roles=(
                    SimpleNamespace(
                        service_id="svc-a",
                        role="service_developer",
                    ),
                ),
            )

    monkeypatch.setenv("ADMIN_AUTH_MODE", "trusted_headers")
    monkeypatch.setattr(admin_dependencies, "IntentRoutingRepository", FakeRepository)
    fake_session = FakeSession()

    context = require_admin_context(
        session=cast(Session, fake_session),
        admin_session_token="valid-cookie-token",
        admin_token="wrong-header-token",
        actor_id="header-user",
        actor_roles="system_admin",
        service_scope="svc-b",
    )

    assert fake_session.committed
    assert context.actor_id == "session-user"
    assert context.roles == frozenset()
    assert context.has_service_role("svc-a", "service_developer")
    assert not context.has_role("system_admin")


def test_default_admin_context_rejects_trusted_headers_without_explicit_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_AUTH_MODE", raising=False)
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "local-admin-token")

    with pytest.raises(Exception) as exc:
        require_admin_context(
            session=cast(Session, object()),
            admin_session_token=None,
            admin_token="local-admin-token",
            actor_id="header-user",
            actor_roles="system_admin",
            service_scope="svc-a",
        )

    assert getattr(exc.value, "status_code", None) == 401
