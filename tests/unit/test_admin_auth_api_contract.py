from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.responses import Response

from intent_routing.api import admin as admin_module
from intent_routing.api import admin_auth as admin_auth_module
from intent_routing.api.admin_dependencies import (
    get_admin_session,
    require_admin_context,
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


def test_organization_directory_openapi_contract_is_registered() -> None:
    paths = create_app().openapi()["paths"]

    assert "get" in paths["/admin/v1/departments"]
    assert "post" in paths["/admin/v1/departments"]
    assert "patch" in paths["/admin/v1/departments/{department_id}"]
    assert "delete" in paths["/admin/v1/departments/{department_id}"]
    assert "get" in paths["/admin/v1/organization-users"]
    assert "post" in paths["/admin/v1/organization-users"]
    assert "patch" in paths["/admin/v1/organization-users/{organization_user_id}"]
    assert "delete" in paths["/admin/v1/organization-users/{organization_user_id}"]


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


def test_c2_membership_openapi_contract_is_registered() -> None:
    openapi = create_app().openapi()
    paths = openapi["paths"]

    assert "get" in paths["/admin/v1/users"]
    assert "get" in paths["/admin/v1/services/{service_id}/members"]
    assert "post" in paths["/admin/v1/services/{service_id}/members/{user_id}/roles"]
    assert (
        "delete"
        in paths["/admin/v1/services/{service_id}/members/{user_id}/roles/{role}"]
    )


def test_c2_membership_openapi_contract_matches_plan_schemas() -> None:
    openapi = create_app().openapi()
    schemas = openapi["components"]["schemas"]
    expected_schema_fields = {
        "AdminUserLookupResponse": {
            "user_id",
            "email",
            "display_name",
            "status",
        },
        "ServiceMemberRoleResponse": {"role", "assigned_by", "assigned_at"},
        "ServiceMemberResponse": {"service_id", "user", "roles"},
        "ServiceRoleGrantRequest": {"role"},
        "ServiceRoleGrantResponse": {
            "service_id",
            "user_id",
            "role",
            "assigned_by",
            "assigned_at",
        },
        "ServiceRoleRevokeResponse": {
            "service_id",
            "user_id",
            "role",
            "revoked_by",
            "revoked_at",
        },
    }

    assert expected_schema_fields.keys() <= schemas.keys()
    for schema_name, expected_fields in expected_schema_fields.items():
        assert set(schemas[schema_name]["properties"]) == expected_fields


def test_c2_users_openapi_contract_has_bounded_lookup_query() -> None:
    openapi = create_app().openapi()
    users_get = openapi["paths"]["/admin/v1/users"]["get"]
    parameters = {
        parameter["name"]: parameter for parameter in users_get.get("parameters", [])
    }

    assert {"query", "limit"} <= parameters.keys()
    assert parameters["query"]["required"] is False
    assert parameters["limit"]["required"] is False
    assert parameters["limit"]["schema"]["maximum"] == 25


def test_c2_membership_openapi_contract_omits_secret_fields() -> None:
    openapi = create_app().openapi()
    schemas = openapi["components"]["schemas"]
    c2_schema_names = {
        "AdminUserLookupResponse",
        "ServiceMemberRoleResponse",
        "ServiceMemberResponse",
        "ServiceRoleGrantRequest",
        "ServiceRoleGrantResponse",
        "ServiceRoleRevokeResponse",
    }
    assert c2_schema_names <= schemas.keys()
    schema_text = "\n".join(
        str(schemas[name])
        for name in sorted(c2_schema_names)
    )

    assert "password_hash" not in schema_text
    assert "token_hash" not in schema_text
    assert "session_token" not in schema_text


def test_c2_users_rejects_trusted_headers_without_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    def override_session() -> Iterator[object]:
        yield object()

    monkeypatch.setenv("ADMIN_AUTH_MODE", "trusted_headers")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-token")
    app.dependency_overrides[get_admin_session] = override_session

    response = TestClient(app).get(
        "/admin/v1/users",
        headers={
            "X-Admin-Token": "bootstrap-token",
            "X-Actor-Id": "header-admin",
            "X-Actor-Roles": "system_admin",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_c2_membership_mutation_rejects_trusted_headers_without_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()

    def override_session() -> Iterator[object]:
        yield object()

    monkeypatch.setenv("ADMIN_AUTH_MODE", "trusted_headers")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-token")
    app.dependency_overrides[get_admin_session] = override_session

    response = TestClient(app).post(
        "/admin/v1/services/svc-a/members/user-a/roles",
        headers={
            "X-Admin-Token": "bootstrap-token",
            "X-Actor-Id": "header-admin",
            "X-Actor-Roles": "system_admin",
        },
        json={"role": "service_developer"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_c2_membership_mutation_session_wins_over_trusted_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    session_context = _service_role_session_context("service_developer")

    monkeypatch.setenv("ADMIN_AUTH_MODE", "trusted_headers")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", "bootstrap-token")
    app.dependency_overrides[require_admin_session_context] = lambda: session_context
    app.dependency_overrides[get_admin_session] = lambda: object()
    monkeypatch.setattr(
        admin_module,
        "IntentRoutingRepository",
        lambda _session: (_ for _ in ()).throw(
            AssertionError("auth denial must happen before repository access")
        ),
    )

    client = TestClient(app)
    client.cookies.set(ADMIN_SESSION_COOKIE_NAME, "session-token")

    response = client.post(
        "/admin/v1/services/svc-a/members/user-a/roles",
        headers={
            "X-Admin-Token": "bootstrap-token",
            "X-Actor-Id": "header-admin",
            "X-Actor-Roles": "system_admin",
        },
        json={"role": "service_developer"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


@pytest.mark.parametrize(
    ("role", "expected_service_roles"),
    [
        ("service_owner", ("service_owner",)),
        ("service_developer", ("service_developer",)),
        ("service_operator", ("service_operator",)),
        ("auditor", ("auditor",)),
        (None, ()),
    ],
)
def test_c2_membership_mutations_reject_non_system_admin_session(
    monkeypatch: pytest.MonkeyPatch,
    role: str | None,
    expected_service_roles: tuple[str, ...],
) -> None:
    app = create_app()
    session_context = _service_role_session_context(role)

    app.dependency_overrides[require_admin_session_context] = lambda: session_context
    app.dependency_overrides[get_admin_session] = lambda: object()
    monkeypatch.setattr(
        admin_module,
        "IntentRoutingRepository",
        lambda _session: (_ for _ in ()).throw(
            AssertionError("auth denial must happen before repository access")
        ),
    )

    client = TestClient(app)

    grant_response = client.post(
        "/admin/v1/services/svc-a/members/user-a/roles",
        json={"role": "service_developer"},
    )
    revoke_response = client.delete(
        "/admin/v1/services/svc-a/members/user-a/roles/service_developer",
    )

    assert tuple(role.role for role in session_context.service_roles) == (
        expected_service_roles
    )
    assert grant_response.status_code == 403
    assert grant_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
    assert revoke_response.status_code == 403
    assert revoke_response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"


def test_c2_membership_api_success_flow_uses_repository_and_omits_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    assigned_at = datetime(2026, 7, 10, 1, 2, 3, tzinfo=UTC)
    session_context = SimpleNamespace(
        user=SimpleNamespace(user_id="session-admin"),
        global_roles=frozenset({"system_admin"}),
        service_roles=(),
    )
    repository = _FakeMembershipRepository(
        users=[
            SimpleNamespace(
                user_id="user-a",
                email="developer-c2@example.com",
                display_name="Developer C2",
                status="active",
                password_hash="password-hash",
            )
        ],
        service=SimpleNamespace(service_id="svc-a"),
        member_roles=[],
    )
    fake_session = _FakeSession(repository.calls)

    app.dependency_overrides[require_admin_session_context] = lambda: session_context
    app.dependency_overrides[require_admin_context] = lambda: (_ for _ in ()).throw(
        AssertionError("C-2 membership routes must use session context")
    )
    app.dependency_overrides[get_admin_session] = lambda: fake_session
    monkeypatch.setattr(
        admin_module,
        "IntentRoutingRepository",
        lambda _session: repository,
    )
    monkeypatch.setattr(
        admin_module,
        "datetime",
        SimpleNamespace(now=lambda _timezone: assigned_at),
    )

    client = TestClient(app)

    users_response = client.get("/admin/v1/users?query=developer-c2&limit=25")
    members_response = client.get("/admin/v1/services/svc-a/members")
    grant_response = client.post(
        "/admin/v1/services/svc-a/members/user-a/roles",
        json={"role": "service_developer"},
    )
    duplicate_grant_response = client.post(
        "/admin/v1/services/svc-a/members/user-a/roles",
        json={"role": "service_developer"},
    )
    members_after_grant_response = client.get("/admin/v1/services/svc-a/members")
    revoke_response = client.delete(
        "/admin/v1/services/svc-a/members/user-a/roles/service_developer",
    )
    duplicate_revoke_response = client.delete(
        "/admin/v1/services/svc-a/members/user-a/roles/service_developer",
    )
    members_after_revoke_response = client.get("/admin/v1/services/svc-a/members")
    response_text = "\n".join(
        [
            users_response.text,
            members_response.text,
            grant_response.text,
            duplicate_grant_response.text,
            members_after_grant_response.text,
            revoke_response.text,
            duplicate_revoke_response.text,
            members_after_revoke_response.text,
        ]
    )

    assert users_response.status_code == 200
    assert users_response.json() == [
        {
            "user_id": "user-a",
            "email": "developer-c2@example.com",
            "display_name": "Developer C2",
            "status": "active",
        }
    ]
    assert members_response.status_code == 200
    assert members_response.json() == []
    assert grant_response.status_code == 200
    assert grant_response.json() == {
        "service_id": "svc-a",
        "user_id": "user-a",
        "role": "service_developer",
        "assigned_by": "session-admin",
        "assigned_at": "2026-07-10T01:02:03Z",
    }
    assert duplicate_grant_response.status_code == 200
    assert duplicate_grant_response.json() == {
        "service_id": "svc-a",
        "user_id": "user-a",
        "role": "service_developer",
        "assigned_by": "session-admin",
        "assigned_at": "2026-07-10T01:02:03Z",
    }
    assert members_after_grant_response.status_code == 200
    assert members_after_grant_response.json() == [
        {
            "service_id": "svc-a",
            "user": {
                "user_id": "user-a",
                "email": "developer-c2@example.com",
                "display_name": "Developer C2",
                "status": "active",
            },
            "roles": [
                {
                    "role": "service_developer",
                    "assigned_by": "session-admin",
                    "assigned_at": "2026-07-10T01:02:03Z",
                }
            ],
        }
    ]
    assert revoke_response.status_code == 200
    assert revoke_response.json() == {
        "service_id": "svc-a",
        "user_id": "user-a",
        "role": "service_developer",
        "revoked_by": "session-admin",
        "revoked_at": "2026-07-10T01:02:03Z",
    }
    assert duplicate_revoke_response.status_code == 404
    assert duplicate_revoke_response.json()["error"]["code"] == "INVALID_REQUEST"
    assert members_after_revoke_response.status_code == 200
    assert members_after_revoke_response.json() == []
    assert repository.calls == [
        ("list_admin_users", "developer-c2", 25),
        ("get_service", "svc-a"),
        ("list_service_member_roles", "svc-a"),
        ("get_service", "svc-a"),
        ("get_admin_user", "user-a"),
        (
            "ensure_user_service_role_with_created",
            {
                "service_id": "svc-a",
                "user_id": "user-a",
                "role": "service_developer",
                "assigned_by": "session-admin",
                "assigned_at": assigned_at,
            },
            True,
        ),
        (
            "insert_audit_log",
            "service_membership.role_granted",
            "svc-a:user-a:service_developer",
        ),
        ("commit",),
        ("get_service", "svc-a"),
        ("get_admin_user", "user-a"),
        (
            "ensure_user_service_role_with_created",
            {
                "service_id": "svc-a",
                "user_id": "user-a",
                "role": "service_developer",
                "assigned_by": "session-admin",
                "assigned_at": assigned_at,
            },
            False,
        ),
        ("commit",),
        ("get_service", "svc-a"),
        ("list_service_member_roles", "svc-a"),
        ("get_service", "svc-a"),
        ("delete_user_service_role_by_key", "user-a", "svc-a", "service_developer"),
        (
            "insert_audit_log",
            "service_membership.role_revoked",
            "svc-a:user-a:service_developer",
        ),
        ("commit",),
        ("get_service", "svc-a"),
        ("delete_user_service_role_by_key", "user-a", "svc-a", "service_developer"),
        ("get_service", "svc-a"),
        ("list_service_member_roles", "svc-a"),
    ]
    assert len(repository.audit_logs) == 2
    grant_audit, revoke_audit = repository.audit_logs
    assert grant_audit["event_type"] == "service_membership.role_granted"
    assert grant_audit["actor_id"] == "session-admin"
    assert grant_audit["service_id"] == "svc-a"
    assert grant_audit["target_type"] == "user_service_role"
    assert grant_audit["target_id"] == "svc-a:user-a:service_developer"
    assert grant_audit["before_state"] is None
    assert grant_audit["after_state"] == grant_response.json()
    assert grant_audit["created_at"] == assigned_at
    assert revoke_audit["event_type"] == "service_membership.role_revoked"
    assert revoke_audit["actor_id"] == "session-admin"
    assert revoke_audit["service_id"] == "svc-a"
    assert revoke_audit["target_type"] == "user_service_role"
    assert revoke_audit["target_id"] == "svc-a:user-a:service_developer"
    assert revoke_audit["before_state"] == {
        "service_id": "svc-a",
        "user_id": "user-a",
        "role": "service_developer",
        "assigned_by": "session-admin",
        "assigned_at": "2026-07-10T01:02:03Z",
    }
    assert revoke_audit["after_state"] == revoke_response.json()
    assert revoke_audit["created_at"] == assigned_at
    assert "password_hash" not in response_text
    assert "token_hash" not in response_text
    assert "session_token" not in response_text


class _FakeSession:
    def __init__(self, calls: list[object]) -> None:
        self._calls = calls

    def commit(self) -> None:
        self._calls.append(("commit",))


class _FakeMembershipRepository:
    def __init__(
        self,
        *,
        users: list[SimpleNamespace],
        service: SimpleNamespace | None,
        member_roles: list[SimpleNamespace],
    ) -> None:
        self.calls: list[object] = []
        self.audit_logs: list[dict[str, object]] = []
        self._users = users
        self._service = service
        self._users_by_id = {user.user_id: user for user in users}
        self._roles_by_key: dict[tuple[str, str, str], SimpleNamespace] = {}
        for role_record in member_roles:
            self._roles_by_key[
                (role_record.user_id, role_record.service_id, role_record.role)
            ] = role_record

    def list_admin_users(
        self,
        *,
        query: str | None,
        limit: int,
    ) -> list[SimpleNamespace]:
        self.calls.append(("list_admin_users", query, limit))
        return self._users

    def get_service(self, service_id: str) -> SimpleNamespace | None:
        self.calls.append(("get_service", service_id))
        return self._service

    def list_service_member_roles(self, service_id: str) -> list[SimpleNamespace]:
        self.calls.append(("list_service_member_roles", service_id))
        return [
            role_record
            for role_record in self._roles_by_key.values()
            if role_record.service_id == service_id
        ]

    def get_admin_user(self, user_id: str) -> SimpleNamespace | None:
        self.calls.append(("get_admin_user", user_id))
        return next((user for user in self._users if user.user_id == user_id), None)

    def ensure_user_service_role(self, **values: object) -> SimpleNamespace:
        key = (
            str(values["user_id"]),
            str(values["service_id"]),
            str(values["role"]),
        )
        existing = self._roles_by_key.get(key)
        self.calls.append(("ensure_user_service_role", values))
        if existing is not None:
            return existing
        role_record = SimpleNamespace(**values)
        self._roles_by_key[key] = role_record
        return role_record

    def ensure_user_service_role_with_created(
        self,
        **values: object,
    ) -> tuple[SimpleNamespace, bool]:
        key = (
            str(values["user_id"]),
            str(values["service_id"]),
            str(values["role"]),
        )
        existing = self._roles_by_key.get(key)
        if existing is not None:
            self.calls.append(("ensure_user_service_role_with_created", values, False))
            return existing, False
        user = self._users_by_id[str(values["user_id"])]
        role_record = SimpleNamespace(**values, user=user)
        self._roles_by_key[key] = role_record
        self.calls.append(("ensure_user_service_role_with_created", values, True))
        return role_record, True

    def get_user_service_role(
        self,
        user_id: str,
        service_id: str,
        role: str,
    ) -> SimpleNamespace | None:
        self.calls.append(("get_user_service_role", user_id, service_id, role))
        return self._roles_by_key.get((user_id, service_id, role))

    def delete_user_service_role(self, role_record: SimpleNamespace) -> None:
        self._roles_by_key.pop(
            (role_record.user_id, role_record.service_id, role_record.role),
            None,
        )
        self.calls.append(
            (
                "delete_user_service_role",
                role_record.user_id,
                role_record.service_id,
                role_record.role,
            )
        )

    def delete_user_service_role_by_key(
        self,
        user_id: str,
        service_id: str,
        role: str,
    ) -> SimpleNamespace | None:
        self.calls.append(("delete_user_service_role_by_key", user_id, service_id, role))
        return self._roles_by_key.pop((user_id, service_id, role), None)

    def insert_audit_log(self, **values: object) -> SimpleNamespace:
        self.audit_logs.append(values)
        self.calls.append(
            (
                "insert_audit_log",
                values["event_type"],
                values["target_id"],
            )
        )
        return SimpleNamespace(**values)


@pytest.mark.parametrize("role", [" ", "service_admin"])
def test_c2_membership_grant_rejects_invalid_body_role(
    role: str,
) -> None:
    app = create_app()
    app.dependency_overrides[require_admin_session_context] = (
        _system_admin_session_context
    )
    app.dependency_overrides[require_admin_context] = lambda: (_ for _ in ()).throw(
        AssertionError("C-2 membership routes must use session context")
    )

    response = TestClient(app).post(
        "/admin/v1/services/svc-a/members/user-a/roles",
        json={"role": role},
    )

    assert response.status_code == 422


def test_c2_membership_revoke_rejects_unknown_path_role() -> None:
    app = create_app()
    app.dependency_overrides[require_admin_session_context] = (
        _system_admin_session_context
    )
    app.dependency_overrides[require_admin_context] = lambda: (_ for _ in ()).throw(
        AssertionError("C-2 membership routes must use session context")
    )

    response = TestClient(app).delete(
        "/admin/v1/services/svc-a/members/user-a/roles/service_admin",
    )

    assert response.status_code == 422


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


def test_me_services_reads_session_context_service_roles_per_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_service_roles: list[SimpleNamespace] = []

    class FakeRepository:
        def __init__(self, _session: object) -> None:
            pass

        def list_services_for_user(self, user_id: str) -> list[SimpleNamespace]:
            assert user_id == "developer-a"
            if not current_service_roles:
                return []
            return [
                SimpleNamespace(
                    service_id="svc-a",
                    display_name="Service A",
                    environment="test",
                    status="active",
                )
            ]

    app = create_app()

    def override_session_context() -> SimpleNamespace:
        return SimpleNamespace(
            user=SimpleNamespace(user_id="developer-a"),
            global_roles=frozenset(),
            service_roles=tuple(current_service_roles),
        )

    def override_session() -> Iterator[object]:
        yield object()

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[require_admin_session_context] = override_session_context
    monkeypatch.setattr(admin_module, "IntentRoutingRepository", FakeRepository)
    client = TestClient(app)

    initial_response = client.get("/admin/v1/me/services")
    current_service_roles.append(
        SimpleNamespace(service_id="svc-a", role="service_developer")
    )
    granted_response = client.get("/admin/v1/me/services")
    current_service_roles.clear()
    revoked_response = client.get("/admin/v1/me/services")

    assert initial_response.status_code == 200
    assert initial_response.json() == []
    assert granted_response.status_code == 200
    assert granted_response.json() == [
        {
            "service_id": "svc-a",
            "display_name": "Service A",
            "environment": "test",
            "status": "active",
            "roles": ["service_developer"],
        }
    ]
    assert revoked_response.status_code == 200
    assert revoked_response.json() == []


def _system_admin_session_context() -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(user_id="session-admin"),
        global_roles=frozenset({"system_admin"}),
        service_roles=(),
    )


def _service_role_session_context(role: str | None) -> SimpleNamespace:
    service_roles: tuple[SimpleNamespace, ...] = ()
    if role is not None:
        service_roles = (SimpleNamespace(service_id="svc-a", role=role),)
    return SimpleNamespace(
        user=SimpleNamespace(user_id=f"session-{role or 'no-role'}"),
        global_roles=frozenset(),
        service_roles=service_roles,
    )
