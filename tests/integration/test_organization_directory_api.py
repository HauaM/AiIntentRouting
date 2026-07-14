from collections.abc import Iterator
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import (
    get_admin_session,
    require_admin_context,
    require_admin_session_context,
)
from intent_routing.db import models
from intent_routing.main import create_app


def _client(db_session: Session) -> TestClient:
    return _session_client(db_session, global_roles=frozenset({"system_admin"}))


def _session_client(
    db_session: Session,
    *,
    global_roles: frozenset[str],
) -> TestClient:
    app = create_app()
    session_context = SimpleNamespace(
        user=SimpleNamespace(user_id="system-admin"),
        global_roles=global_roles,
        service_roles=(),
    )

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[require_admin_session_context] = lambda: session_context
    app.dependency_overrides[require_admin_context] = lambda: (_ for _ in ()).throw(
        AssertionError("organization directory routes should build admin context internally")
    )
    return TestClient(app)


def test_system_admin_manages_departments_and_organization_users(
    db_session: Session,
) -> None:
    client = _client(db_session)
    suffix = uuid4().hex[:8]
    dept_number = f"0969-{suffix}"
    user_number = f"21P0031-{suffix}"

    dept_response = client.post(
        "/admin/v1/departments",
        json={"dept_number": dept_number, "name": "IT지원부"},
    )
    assert dept_response.status_code == 201
    department = dept_response.json()

    user_response = client.post(
        "/admin/v1/organization-users",
        json={
            "user_number": user_number,
            "name": "홍길동",
            "department_id": department["id"],
        },
    )
    assert user_response.status_code == 201
    assert user_response.json()["use_yn"] == "Y"

    list_response = client.get(f"/admin/v1/organization-users?query={user_number}")
    assert list_response.status_code == 200
    assert list_response.json()[0]["user_number"] == user_number


def test_organization_directory_patch_updates_records(
    db_session: Session,
) -> None:
    client = _client(db_session)
    suffix = uuid4().hex[:8]

    dept_response = client.post(
        "/admin/v1/departments",
        json={"dept_number": f"1000-{suffix}", "name": "전산운영부"},
    )
    assert dept_response.status_code == 201
    department = dept_response.json()

    second_dept_response = client.post(
        "/admin/v1/departments",
        json={"dept_number": f"1001-{suffix}", "name": "보안운영부"},
    )
    assert second_dept_response.status_code == 201
    second_department = second_dept_response.json()

    patched_department_response = client.patch(
        f"/admin/v1/departments/{department['id']}",
        json={"dept_number": f"2000-{suffix}", "name": "인프라운영부"},
    )
    assert patched_department_response.status_code == 200
    patched_department = patched_department_response.json()
    assert patched_department["dept_number"] == f"2000-{suffix}"
    assert patched_department["name"] == "인프라운영부"

    user_response = client.post(
        "/admin/v1/organization-users",
        json={
            "user_number": f"31P0001-{suffix}",
            "name": "김철수",
            "department_id": department["id"],
        },
    )
    assert user_response.status_code == 201
    organization_user = user_response.json()

    patched_user_response = client.patch(
        f"/admin/v1/organization-users/{organization_user['id']}",
        json={
            "user_number": f"31P0002-{suffix}",
            "name": "김영희",
            "department_id": second_department["id"],
            "use_yn": "N",
        },
    )
    assert patched_user_response.status_code == 200
    patched_user = patched_user_response.json()
    assert patched_user["user_number"] == f"31P0002-{suffix}"
    assert patched_user["name"] == "김영희"
    assert patched_user["department_id"] == second_department["id"]
    assert patched_user["department"]["id"] == second_department["id"]
    assert patched_user["use_yn"] == "N"


def test_department_delete_conflicts_when_active_organization_users_remain(
    db_session: Session,
) -> None:
    client = _client(db_session)
    suffix = uuid4().hex[:8]

    dept_response = client.post(
        "/admin/v1/departments",
        json={"dept_number": f"3000-{suffix}", "name": "IT지원부"},
    )
    assert dept_response.status_code == 201
    department = dept_response.json()

    user_response = client.post(
        "/admin/v1/organization-users",
        json={
            "user_number": f"41P0001-{suffix}",
            "name": "박민수",
            "department_id": department["id"],
        },
    )
    assert user_response.status_code == 201
    organization_user = user_response.json()

    conflict_response = client.delete(f"/admin/v1/departments/{department['id']}")
    assert conflict_response.status_code == 409
    assert conflict_response.json()["error"]["code"] == "INVALID_REQUEST"

    deactivate_user_response = client.delete(
        f"/admin/v1/organization-users/{organization_user['id']}"
    )
    assert deactivate_user_response.status_code == 200
    assert deactivate_user_response.json()["use_yn"] == "N"

    deactivate_department_response = client.delete(
        f"/admin/v1/departments/{department['id']}"
    )
    assert deactivate_department_response.status_code == 200
    assert deactivate_department_response.json()["use_yn"] == "N"


def test_department_patch_conflicts_when_deactivating_with_active_organization_users(
    db_session: Session,
) -> None:
    client = _client(db_session)
    suffix = uuid4().hex[:8]

    dept_response = client.post(
        "/admin/v1/departments",
        json={"dept_number": f"3100-{suffix}", "name": "고객지원부"},
    )
    assert dept_response.status_code == 201
    department = dept_response.json()

    user_response = client.post(
        "/admin/v1/organization-users",
        json={
            "user_number": f"42P0001-{suffix}",
            "name": "이은지",
            "department_id": department["id"],
        },
    )
    assert user_response.status_code == 201

    conflict_response = client.patch(
        f"/admin/v1/departments/{department['id']}",
        json={"use_yn": "N"},
    )

    assert conflict_response.status_code == 409
    assert conflict_response.json()["error"]["code"] == "INVALID_REQUEST"

    persisted = db_session.get(models.Department, department["id"])
    assert persisted is not None
    assert persisted.use_yn == "Y"


def test_organization_directory_rejects_whitespace_only_directory_fields(
    db_session: Session,
) -> None:
    client = _client(db_session)
    suffix = uuid4().hex[:8]

    department_response = client.post(
        "/admin/v1/departments",
        json={"dept_number": f"3200-{suffix}", "name": "플랫폼운영부"},
    )
    assert department_response.status_code == 201
    department = department_response.json()

    user_response = client.post(
        "/admin/v1/organization-users",
        json={
            "user_number": f"43P0001-{suffix}",
            "name": "정다은",
            "department_id": department["id"],
        },
    )
    assert user_response.status_code == 201
    organization_user = user_response.json()

    invalid_create_requests = [
        (
            "/admin/v1/departments",
            {"dept_number": "   ", "name": "유효한부서명"},
        ),
        (
            "/admin/v1/departments",
            {"dept_number": f"3201-{suffix}", "name": "   "},
        ),
        (
            "/admin/v1/organization-users",
            {
                "user_number": "   ",
                "name": "유효한이름",
                "department_id": department["id"],
            },
        ),
        (
            "/admin/v1/organization-users",
            {
                "user_number": f"43P0002-{suffix}",
                "name": "   ",
                "department_id": department["id"],
            },
        ),
    ]

    for path, payload in invalid_create_requests:
        response = client.post(path, json=payload)
        body = response.json()
        assert response.status_code == 422
        assert body["error"]["code"] == "INVALID_REQUEST"

    invalid_patch_requests = [
        (
            f"/admin/v1/departments/{department['id']}",
            {"dept_number": "   "},
        ),
        (
            f"/admin/v1/departments/{department['id']}",
            {"name": "   "},
        ),
        (
            f"/admin/v1/organization-users/{organization_user['id']}",
            {"user_number": "   "},
        ),
        (
            f"/admin/v1/organization-users/{organization_user['id']}",
            {"name": "   "},
        ),
    ]

    for path, payload in invalid_patch_requests:
        response = client.patch(path, json=payload)
        body = response.json()
        assert response.status_code == 422
        assert body["error"]["code"] == "INVALID_REQUEST"

    persisted_department = db_session.get(models.Department, department["id"])
    assert persisted_department is not None
    assert persisted_department.dept_number == f"3200-{suffix}"
    assert persisted_department.name == "플랫폼운영부"

    persisted_user = db_session.scalar(
        select(models.OrganizationUser).where(
            models.OrganizationUser.id == organization_user["id"]
        )
    )
    assert persisted_user is not None
    assert persisted_user.user_number == f"43P0001-{suffix}"
    assert persisted_user.name == "정다은"


def test_organization_directory_routes_require_system_admin(
    db_session: Session,
) -> None:
    client = _session_client(db_session, global_roles=frozenset())
    missing_id = "11111111-1111-1111-1111-111111111111"
    suffix = uuid4().hex[:8]
    requests = [
        ("get", "/admin/v1/departments", None),
        (
            "post",
            "/admin/v1/departments",
            {"dept_number": f"5000-{suffix}", "name": "권한없음"},
        ),
        ("patch", f"/admin/v1/departments/{missing_id}", {"name": "권한없음"}),
        ("delete", f"/admin/v1/departments/{missing_id}", None),
        ("get", "/admin/v1/organization-users", None),
        (
            "post",
            "/admin/v1/organization-users",
            {
                "user_number": f"51P0001-{suffix}",
                "name": "권한없음",
                "department_id": missing_id,
            },
        ),
        ("patch", f"/admin/v1/organization-users/{missing_id}", {"name": "권한없음"}),
        ("delete", f"/admin/v1/organization-users/{missing_id}", None),
    ]

    for method, path, payload in requests:
        if payload is None:
            response = getattr(client, method)(path)
        else:
            response = getattr(client, method)(path, json=payload)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "SERVICE_SCOPE_DENIED"
