from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.responses import Response

from intent_routing.api import admin as admin_module
from intent_routing.api import admin_auth as admin_auth_module
from intent_routing.api.admin_dependencies import (
    get_admin_session,
    require_admin_session_context,
)
from intent_routing.main import create_app
from intent_routing.security.admin_sessions import (
    ADMIN_SESSION_COOKIE_MAX_AGE_SECONDS,
    ADMIN_SESSION_COOKIE_NAME,
)


def test_auth_router_is_included_in_app_routes() -> None:
    paths = create_app().openapi()["paths"]

    assert "post" in paths["/admin/v1/auth/bootstrap-admin"]
    assert "post" in paths["/admin/v1/auth/login"]
    assert "post" in paths["/admin/v1/auth/logout"]
    assert "get" in paths["/admin/v1/auth/me"]


def test_app_startup_runs_system_admin_provisioning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def fake_configure(session_scope_factory: object) -> str:
        calls.append(session_scope_factory)
        return "skipped"

    monkeypatch.setattr(
        "intent_routing.main.configure_startup_system_admin",
        fake_configure,
    )

    with TestClient(create_app()):
        pass

    assert len(calls) == 1


def test_auth_openapi_contract_does_not_expose_secret_fields() -> None:
    openapi = create_app().openapi()
    auth_schema_names = {
        name
        for name in openapi["components"]["schemas"]
        if name.startswith("AdminAuth") or name.startswith("AdminCurrent")
    }
    serialized_auth_schemas = "\n".join(
        str(openapi["components"]["schemas"][name]) for name in sorted(auth_schema_names)
    )

    assert auth_schema_names
    assert "password_hash" not in serialized_auth_schemas
    assert "token_hash" not in serialized_auth_schemas
    assert "session_token" not in serialized_auth_schemas


def test_logout_clears_session_cookie_without_db_session() -> None:
    class FakeSession:
        def scalar(self, _statement: object) -> None:
            return None

        def close(self) -> None:
            return None

    app = create_app()

    def override_session() -> Iterator[FakeSession]:
        yield FakeSession()

    app.dependency_overrides[get_admin_session] = override_session
    client = TestClient(app)
    client.cookies.set(ADMIN_SESSION_COOKIE_NAME, "raw-session-token")

    response = client.post("/admin/v1/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"success": True}
    set_cookie = response.headers["set-cookie"]
    assert f"{ADMIN_SESSION_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_bootstrap_admin_is_blocked_after_initial_system_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRepository:
        def __init__(self, _session: object) -> None:
            pass

        def acquire_advisory_xact_lock(self, lock_key: str) -> None:
            assert lock_key == "admin-bootstrap-system-admin"

        def admin_user_role_exists(self, role: str) -> bool:
            assert role == "system_admin"
            return True

        def get_admin_user_by_email(self, _email: str) -> None:
            raise AssertionError("bootstrap should stop before email lookup")

    app = create_app()

    def override_session() -> Iterator[object]:
        yield object()

    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-token")
    monkeypatch.setattr(admin_auth_module, "IntentRoutingRepository", FakeRepository)
    app.dependency_overrides[get_admin_session] = override_session

    response = TestClient(app).post(
        "/admin/v1/auth/bootstrap-admin",
        headers={"X-Admin-Token": "bootstrap-token"},
        json={
            "email": "admin@example.com",
            "display_name": "Admin",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_session_cookie_can_be_secure_for_deployed_environments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_SESSION_COOKIE_SECURE", "true")
    response = Response()

    admin_auth_module._set_admin_session_cookie(response, "raw-session-token")

    set_cookie = response.headers["set-cookie"]
    assert f"{ADMIN_SESSION_COOKIE_NAME}=raw-session-token" in set_cookie
    assert f"Max-Age={ADMIN_SESSION_COOKIE_MAX_AGE_SECONDS}" in set_cookie
    assert "Path=/" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Secure" in set_cookie


def test_me_services_rejects_trusted_headers_without_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    def override_session() -> Iterator[object]:
        yield object()

    monkeypatch.setenv("ADMIN_AUTH_MODE", "trusted_headers")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-token")
    app.dependency_overrides[get_admin_session] = override_session

    response = TestClient(app).get(
        "/admin/v1/me/services",
        headers={
            "X-Admin-Token": "bootstrap-token",
            "X-Actor-Id": "header-admin",
            "X-Actor-Roles": "system_admin",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_me_services_system_admin_response_uses_session_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRepository:
        def __init__(self, _session: object) -> None:
            pass

        def list_services(self) -> list[SimpleNamespace]:
            return [
                SimpleNamespace(
                    service_id="svc-a",
                    display_name="Service A",
                    environment="test",
                    status="active",
                )
            ]

    app = create_app()
    session_context = SimpleNamespace(
        user=SimpleNamespace(user_id="session-admin"),
        global_roles=frozenset({"system_admin"}),
        service_roles=(),
    )

    def override_session() -> Iterator[object]:
        yield object()

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[require_admin_session_context] = lambda: session_context
    monkeypatch.setattr(admin_module, "IntentRoutingRepository", FakeRepository)

    response = TestClient(app).get(
        "/admin/v1/me/services",
        headers={
            "X-Actor-Id": "header-user",
            "X-Actor-Roles": "service_developer",
            "X-Service-Scope": "svc-b",
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "service_id": "svc-a",
            "display_name": "Service A",
            "environment": "test",
            "status": "active",
            "roles": ["system_admin"],
        }
    ]
