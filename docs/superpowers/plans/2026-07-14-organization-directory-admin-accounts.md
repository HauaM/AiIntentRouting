# Organization Directory And Admin Accounts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add organization user and department CRUD while keeping Admin Console login and RBAC in `admin_users`, `admin_user_roles`, and `user_service_roles`.

**Architecture:** Introduce an organization directory bounded context with `departments` and `users`, then link `admin_users` to `users` through nullable `organization_user_id`. The organization directory is not an authorization source; Admin access continues to be derived from the authenticated Admin session and RBAC tables. Normal browser requests continue to use Umi `request` and the `irt_admin_session` HttpOnly cookie.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy ORM, Alembic, PostgreSQL, pytest, React 18, TypeScript, Umi Max 4, Ant Design 5, Ant Design ProComponents, Vitest, Umi `request`.

## Global Constraints

- Use `departments` and `users` for organization directory data.
- Keep `admin_users` as the Admin Console login account table.
- Do not add `users.admin_yn`, `users.adminYn`, or any organization-user authorization flag.
- Service roles continue to target `admin_users.user_id`.
- Organization user API paths must use `/admin/v1/organization-users`; keep `/admin/v1/users` for Admin account lookup used by Service membership.
- Normal Admin UI browser requests must not send `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, `X-Service-Scope`, or `Authorization: Bearer`.
- Do not introduce React Query or axios.
- Dangerous deactivation actions must use `ConfirmActionButton` or the same `Modal.confirm` behavior.

---

## File Structure

- Create: `alembic/versions/0007_organization_directory.py`
  - Creates `departments`, `users`, and `admin_users.organization_user_id`.
- Modify: `src/intent_routing/db/models.py`
  - Adds `Department`, `OrganizationUser`, and the optional relationship from `AdminUser`.
- Modify: `src/intent_routing/db/repositories.py`
  - Adds organization directory CRUD helpers and linked Admin authentication filtering.
- Modify: `src/intent_routing/api/admin_auth.py`
  - Ensures login response can still serialize Admin users with or without an organization link.
- Modify: `src/intent_routing/api/admin.py`
  - Adds department and organization user Pydantic schemas and CRUD endpoints.
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
  - Adds department and organization user types.
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
  - Adds department and organization user service functions using Umi `request`.
- Modify: `frontend/intent-routing-console/config/config.ts`
  - Adds route `/organization-directory`.
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`
  - Adds navigation item for Users & Departments.
- Create: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts`
  - Owns form-to-request conversion and UI validation constants.
- Create: `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`
  - Adds tabbed department and user management screen.
- Test: `tests/unit/test_organization_directory_schema.py`
- Test: `tests/integration/test_organization_directory_api.py`
- Test: `frontend/intent-routing-console/src/services/adminServices.test.ts`
- Test: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts`

## Task 1: Database Schema Contract

**Files:**
- Create: `tests/unit/test_organization_directory_schema.py`
- Create: `alembic/versions/0007_organization_directory.py`
- Modify: `src/intent_routing/db/models.py`

**Interfaces:**
- Produces: tables `departments`, `users`; column `admin_users.organization_user_id`.
- Consumes: existing `admin_users.user_id` and SQLAlchemy `Base`.

- [ ] **Step 1: Write the failing schema test**

```python
from sqlalchemy import inspect


def test_organization_directory_tables_exist(db_session):
    inspector = inspect(db_session.bind)

    assert "departments" in inspector.get_table_names()
    assert "users" in inspector.get_table_names()

    department_columns = {column["name"] for column in inspector.get_columns("departments")}
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    admin_columns = {column["name"] for column in inspector.get_columns("admin_users")}

    assert {
        "id",
        "dept_number",
        "name",
        "use_yn",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    } <= department_columns
    assert {
        "id",
        "user_number",
        "name",
        "department_id",
        "use_yn",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    } <= user_columns
    assert "organization_user_id" in admin_columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_organization_directory_schema.py -q`

Expected: FAIL because `departments`, `users`, or `organization_user_id` do not exist.

- [ ] **Step 3: Add the Alembic migration**

Create `alembic/versions/0007_organization_directory.py` with this structure:

```python
"""Add organization directory schema.

Revision ID: 0007_organization_directory
Revises: 0006_governed_workflow_requests
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_organization_directory"
down_revision: str | None = "0006_governed_workflow_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMPTZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dept_number", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("use_yn", sa.Text(), nullable=False, server_default=sa.text("'Y'")),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False),
        sa.CheckConstraint("use_yn in ('Y', 'N')", name="ck_departments_use_yn"),
        sa.UniqueConstraint("dept_number", name="uq_departments_dept_number"),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_number", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("use_yn", sa.Text(), nullable=False, server_default=sa.text("'Y'")),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Text(), nullable=False),
        sa.Column("created_at", TIMESTAMPTZ, nullable=False),
        sa.Column("updated_at", TIMESTAMPTZ, nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.CheckConstraint("use_yn in ('Y', 'N')", name="ck_users_use_yn"),
        sa.UniqueConstraint("user_number", name="uq_users_user_number"),
    )
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.add_column(
        "admin_users",
        sa.Column("organization_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_admin_users_organization_user_id",
        "admin_users",
        ["organization_user_id"],
    )
    op.create_foreign_key(
        "fk_admin_users_organization_user_id_users",
        "admin_users",
        "users",
        ["organization_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_admin_users_organization_user_id_users",
        "admin_users",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_admin_users_organization_user_id",
        "admin_users",
        type_="unique",
    )
    op.drop_column("admin_users", "organization_user_id")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_table("users")
    op.drop_table("departments")
```

- [ ] **Step 4: Add ORM models**

In `src/intent_routing/db/models.py`, add imports if needed and define:

```python
class Department(Base):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dept_number: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    use_yn: Mapped[str] = mapped_column(Text, server_default=text("'Y'"))
    created_by: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("use_yn in ('Y', 'N')", name="ck_departments_use_yn"),
        UniqueConstraint("dept_number", name="uq_departments_dept_number"),
    )


class OrganizationUser(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_number: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("departments.id"))
    use_yn: Mapped[str] = mapped_column(Text, server_default=text("'Y'"))
    created_by: Mapped[str] = mapped_column(Text)
    updated_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    department: Mapped[Department] = relationship()

    __table_args__ = (
        CheckConstraint("use_yn in ('Y', 'N')", name="ck_users_use_yn"),
        UniqueConstraint("user_number", name="uq_users_user_number"),
        Index("ix_users_department_id", "department_id"),
    )
```

Add to `AdminUser`:

```python
organization_user_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("users.id"),
)
organization_user: Mapped[OrganizationUser | None] = relationship()
```

- [ ] **Step 5: Run schema test**

Run: `uv run pytest tests/unit/test_organization_directory_schema.py -q`

Expected: PASS.

## Task 2: Repository And Authentication Semantics

**Files:**
- Modify: `src/intent_routing/db/repositories.py`
- Test: `tests/unit/test_organization_directory_schema.py`

**Interfaces:**
- Consumes: `models.Department`, `models.OrganizationUser`.
- Produces: `create_department`, `list_departments`, `update_department`, `deactivate_department`, `create_organization_user`, `list_organization_users`, `update_organization_user`, `deactivate_organization_user`.

- [ ] **Step 1: Write repository tests**

Add:

```python
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from intent_routing.db.repositories import IntentRoutingRepository


def test_repository_creates_and_lists_departments(db_session):
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)

    department = repository.create_department(
        dept_number="0969",
        name="IT지원부",
        use_yn="Y",
        created_by="admin-a",
        updated_by="admin-a",
        created_at=now,
        updated_at=now,
    )

    assert department.dept_number == "0969"
    assert repository.list_departments(query="IT", use_yn="Y", limit=20)[0].id == department.id


def test_repository_rejects_duplicate_department_number(db_session):
    repository = IntentRoutingRepository(db_session)
    now = datetime.now(UTC)
    payload = {
        "dept_number": "0969",
        "name": "IT지원부",
        "use_yn": "Y",
        "created_by": "admin-a",
        "updated_by": "admin-a",
        "created_at": now,
        "updated_at": now,
    }

    repository.create_department(**payload)
    with pytest.raises(IntegrityError):
        repository.create_department(**payload)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_organization_directory_schema.py -q`

Expected: FAIL because repository helpers do not exist.

- [ ] **Step 3: Add repository helpers**

Implement these methods in `IntentRoutingRepository`:

```python
def create_department(self, **values: Any) -> models.Department:
    return self._add_and_flush(models.Department(**values))


def list_departments(
    self,
    *,
    query: str | None = None,
    use_yn: str | None = None,
    limit: int = 100,
) -> list[models.Department]:
    limit = max(1, min(limit, 100))
    statement = select(models.Department)
    if query is not None and query.strip():
        pattern = f"%{query.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.Department.dept_number).like(pattern),
                func.lower(models.Department.name).like(pattern),
            )
        )
    if use_yn is not None:
        statement = statement.where(models.Department.use_yn == use_yn)
    return list(
        self.session.scalars(
            statement.order_by(models.Department.dept_number).limit(limit)
        )
    )
```

Add matching helpers for organization users:

```python
def create_organization_user(self, **values: Any) -> models.OrganizationUser:
    return self._add_and_flush(models.OrganizationUser(**values))


def list_organization_users(
    self,
    *,
    query: str | None = None,
    department_id: UUID | None = None,
    use_yn: str | None = None,
    limit: int = 100,
) -> list[models.OrganizationUser]:
    limit = max(1, min(limit, 100))
    statement = select(models.OrganizationUser).join(models.Department)
    if query is not None and query.strip():
        pattern = f"%{query.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(models.OrganizationUser.user_number).like(pattern),
                func.lower(models.OrganizationUser.name).like(pattern),
                func.lower(models.Department.dept_number).like(pattern),
                func.lower(models.Department.name).like(pattern),
            )
        )
    if department_id is not None:
        statement = statement.where(models.OrganizationUser.department_id == department_id)
    if use_yn is not None:
        statement = statement.where(models.OrganizationUser.use_yn == use_yn)
    return list(
        self.session.scalars(
            statement.order_by(
                models.Department.dept_number,
                models.OrganizationUser.user_number,
            ).limit(limit)
        )
    )
```

- [ ] **Step 4: Update active session lookup**

In `get_active_admin_session_context`, require linked organization users to be active:

```python
admin_session = self.session.scalar(
    select(models.AdminSession)
    .join(models.AdminUser)
    .outerjoin(models.OrganizationUser)
    .where(models.AdminSession.token_hash == token_hash)
    .where(models.AdminSession.revoked_at.is_(None))
    .where(models.AdminSession.expires_at > now)
    .where(models.AdminUser.status == "active")
    .where(
        or_(
            models.AdminUser.organization_user_id.is_(None),
            models.OrganizationUser.use_yn == "Y",
        )
    )
)
```

- [ ] **Step 5: Run repository tests**

Run: `uv run pytest tests/unit/test_organization_directory_schema.py -q`

Expected: PASS.

## Task 3: Admin API Contract

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Test: `tests/integration/test_organization_directory_api.py`

**Interfaces:**
- Consumes: repository helpers from Task 2.
- Produces: department and organization user CRUD endpoints.

- [ ] **Step 1: Write API tests**

Create `tests/integration/test_organization_directory_api.py`:

```python
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from intent_routing.api.admin_dependencies import get_admin_session, require_admin_session_context
from intent_routing.main import create_app


def _client(db_session):
    app = create_app()
    session_context = SimpleNamespace(
        user=SimpleNamespace(user_id="system-admin"),
        global_roles=frozenset({"system_admin"}),
        service_roles=(),
    )

    def override_session() -> Iterator[object]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    app.dependency_overrides[require_admin_session_context] = lambda: session_context
    return TestClient(app)


def test_system_admin_manages_departments_and_organization_users(db_session):
    client = _client(db_session)

    dept_response = client.post(
        "/admin/v1/departments",
        json={"dept_number": "0969", "name": "IT지원부"},
    )
    assert dept_response.status_code == 201
    department = dept_response.json()

    user_response = client.post(
        "/admin/v1/organization-users",
        json={
            "user_number": "21P0031",
            "name": "홍길동",
            "department_id": department["id"],
        },
    )
    assert user_response.status_code == 201
    assert user_response.json()["use_yn"] == "Y"

    list_response = client.get("/admin/v1/organization-users?query=21P0031")
    assert list_response.status_code == 200
    assert list_response.json()[0]["user_number"] == "21P0031"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_organization_directory_api.py -q`

Expected: FAIL because the endpoints are not registered.

- [ ] **Step 3: Add Pydantic schemas**

Add to `src/intent_routing/api/admin.py`:

```python
class DepartmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dept_number: str = Field(min_length=1)
    name: str = Field(min_length=1)


class DepartmentPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dept_number: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)
    use_yn: Literal["Y", "N"] | None = None


class DepartmentResponse(BaseModel):
    id: UUID
    dept_number: str
    name: str
    use_yn: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class OrganizationUserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_number: str = Field(min_length=1)
    name: str = Field(min_length=1)
    department_id: UUID


class OrganizationUserPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_number: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)
    department_id: UUID | None = None
    use_yn: Literal["Y", "N"] | None = None


class OrganizationUserResponse(BaseModel):
    id: UUID
    user_number: str
    name: str
    department_id: UUID
    department: DepartmentResponse
    use_yn: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Add endpoint handlers**

Add endpoints under the existing Admin router. Every handler must call
`_require_system_admin(context)`.

```python
@router.post("/departments", response_model=DepartmentResponse, status_code=201)
def create_department(...):
    context = admin_context_from_session_record(session_context)
    _require_system_admin(context)
    now = datetime.now(UTC)
    department = repository.create_department(
        dept_number=request.dept_number.strip(),
        name=request.name.strip(),
        use_yn="Y",
        created_by=context.actor_id,
        updated_by=context.actor_id,
        created_at=now,
        updated_at=now,
    )
    session.commit()
    return _department_response(department)
```

Use `PATCH` for edits and `DELETE` for deactivation. Department deactivation
must return `409` when active users exist in the department.

- [ ] **Step 5: Run API tests**

Run: `uv run pytest tests/integration/test_organization_directory_api.py -q`

Expected: PASS.

## Task 4: Frontend Service Layer And Types

**Files:**
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Test: `frontend/intent-routing-console/src/services/adminServices.test.ts`

**Interfaces:**
- Produces: `listDepartments`, `createDepartment`, `patchDepartment`, `deleteDepartment`, `listOrganizationUsers`, `createOrganizationUser`, `patchOrganizationUser`, `deleteOrganizationUser`.

- [ ] **Step 1: Add failing service tests**

Add to `adminServices.test.ts`:

```ts
it('uses organization directory endpoints without trusted headers', async () => {
  await createDepartment({ dept_number: '0969', name: 'IT지원부' });
  await listDepartments({ query: 'IT', use_yn: 'Y' });
  await createOrganizationUser({
    user_number: '21P0031',
    name: '홍길동',
    department_id: 'dept-1',
  });

  expect(requestMock).toHaveBeenNthCalledWith(1, '/departments', {
    method: 'POST',
    data: { dept_number: '0969', name: 'IT지원부' },
  });
  expect(requestMock).toHaveBeenNthCalledWith(2, '/departments', {
    method: 'GET',
    params: { query: 'IT', use_yn: 'Y', limit: 100 },
  });
  expect(requestMock).toHaveBeenNthCalledWith(3, '/organization-users', {
    method: 'POST',
    data: {
      user_number: '21P0031',
      name: '홍길동',
      department_id: 'dept-1',
    },
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend/intent-routing-console && pnpm vitest run src/services/adminServices.test.ts`

Expected: FAIL because service functions do not exist.

- [ ] **Step 3: Add API types**

Add to `api.d.ts`:

```ts
type UseYn = 'Y' | 'N';

type Department = {
  id: string;
  dept_number: string;
  name: string;
  use_yn: UseYn;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
};

type DepartmentCreateRequest = {
  dept_number: string;
  name: string;
};

type DepartmentPatchRequest = Partial<DepartmentCreateRequest> & {
  use_yn?: UseYn;
};

type OrganizationUser = {
  id: string;
  user_number: string;
  name: string;
  department_id: string;
  department: Department;
  use_yn: UseYn;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
};

type OrganizationUserCreateRequest = {
  user_number: string;
  name: string;
  department_id: string;
};

type OrganizationUserPatchRequest = Partial<OrganizationUserCreateRequest> & {
  use_yn?: UseYn;
};
```

- [ ] **Step 4: Add service functions**

Add to `adminServices.ts`:

```ts
export async function listDepartments(
  params: { query?: string; use_yn?: API.UseYn; limit?: number } = {},
) {
  return request<API.Department[]>('/departments', {
    method: 'GET',
    params: { query: params.query, use_yn: params.use_yn, limit: params.limit ?? 100 },
  });
}

export async function createDepartment(payload: API.DepartmentCreateRequest) {
  return request<API.Department>('/departments', { method: 'POST', data: payload });
}

export async function patchDepartment(
  departmentId: string,
  payload: API.DepartmentPatchRequest,
) {
  return request<API.Department>(`/departments/${encodeURIComponent(departmentId)}`, {
    method: 'PATCH',
    data: payload,
  });
}

export async function deleteDepartment(departmentId: string) {
  return request<API.Department>(`/departments/${encodeURIComponent(departmentId)}`, {
    method: 'DELETE',
  });
}
```

Add matching `/organization-users` functions.

- [ ] **Step 5: Run service tests**

Run: `cd frontend/intent-routing-console && pnpm vitest run src/services/adminServices.test.ts`

Expected: PASS.

## Task 5: Admin UI Page

**Files:**
- Create: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.ts`
- Create: `frontend/intent-routing-console/src/pages/OrganizationDirectory/index.tsx`
- Modify: `frontend/intent-routing-console/config/config.ts`
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`
- Test: `frontend/intent-routing-console/src/pages/OrganizationDirectory/directoryForms.test.ts`

**Interfaces:**
- Consumes: frontend service functions from Task 4.
- Produces: `/organization-directory` Admin UI route.

- [ ] **Step 1: Write form helper tests**

```ts
import {
  toDepartmentCreateRequest,
  toOrganizationUserCreateRequest,
} from './directoryForms';

it('trims department form values', () => {
  expect(toDepartmentCreateRequest({ dept_number: ' 0969 ', name: ' IT지원부 ' })).toEqual({
    dept_number: '0969',
    name: 'IT지원부',
  });
});

it('trims organization user form values', () => {
  expect(
    toOrganizationUserCreateRequest({
      user_number: ' 21P0031 ',
      name: ' 홍길동 ',
      department_id: 'dept-1',
    }),
  ).toEqual({ user_number: '21P0031', name: '홍길동', department_id: 'dept-1' });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend/intent-routing-console && pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts`

Expected: FAIL because `directoryForms.ts` does not exist.

- [ ] **Step 3: Add form helpers**

```ts
export type DepartmentFormValues = {
  dept_number: string;
  name: string;
};

export type OrganizationUserFormValues = {
  user_number: string;
  name: string;
  department_id: string;
};

export const toDepartmentCreateRequest = (
  values: DepartmentFormValues,
): API.DepartmentCreateRequest => ({
  dept_number: values.dept_number.trim(),
  name: values.name.trim(),
});

export const toOrganizationUserCreateRequest = (
  values: OrganizationUserFormValues,
): API.OrganizationUserCreateRequest => ({
  user_number: values.user_number.trim(),
  name: values.name.trim(),
  department_id: values.department_id,
});
```

- [ ] **Step 4: Add page route and nav**

Add route:

```ts
{ path: '/organization-directory', component: './OrganizationDirectory' },
```

Add AdminShell route item:

```tsx
{ path: '/organization-directory', name: 'Users & Departments', icon: <TeamOutlined /> },
```

- [ ] **Step 5: Build `OrganizationDirectory` page**

Use `AdminShell`, `Tabs`, `ProTable`, `Form`, `Modal`, `Select`, `Tag`, and
`ConfirmActionButton`. The page must include:

- Departments tab with columns `dept_number`, `name`, `use_yn`, `updated_at`.
- Users tab with columns `user_number`, `name`, `department.name`, `use_yn`,
  `updated_at`.
- Create and edit modals for each resource.
- Delete buttons that call deactivation endpoints through confirmation.
- `system_admin` gate using the existing `adminSession` model helpers or a local
  `session.globalRoles.includes('system_admin')` helper if no shared helper
  exists.

- [ ] **Step 6: Run frontend verification**

Run: `cd frontend/intent-routing-console && pnpm vitest run src/pages/OrganizationDirectory/directoryForms.test.ts src/services/adminServices.test.ts`

Expected: PASS.

Run: `cd frontend/intent-routing-console && pnpm run typecheck`

Expected: PASS.

## Task 6: End-To-End Verification And Guardrails

**Files:**
- Modify: `tests/integration/test_organization_directory_api.py`
- Modify: `tests/unit/test_admin_auth_api_contract.py`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: regression coverage that organization directory data does not become an authorization source.

- [ ] **Step 1: Add auth guard regression**

Add a test that links `admin_users.organization_user_id` to a `users` row, sets
`users.use_yn = 'N'`, and asserts `/admin/v1/auth/me` or an authenticated Admin
endpoint rejects the session with `401`.

- [ ] **Step 2: Add OpenAPI route registration test**

In `tests/unit/test_admin_auth_api_contract.py`, add:

```python
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
```

- [ ] **Step 3: Run backend verification**

Run:

```bash
uv run pytest \
  tests/unit/test_organization_directory_schema.py \
  tests/unit/test_admin_auth_api_contract.py \
  tests/integration/test_organization_directory_api.py \
  tests/unit/test_admin_sessions.py \
  -q
```

Expected: PASS.

- [ ] **Step 4: Search prohibited frontend assumptions**

Run:

```bash
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|admin_yn|adminYn" frontend/intent-routing-console/src
```

Expected: no implementation matches for prohibited dependencies, trusted actor
headers, or organization-user admin flags.

- [ ] **Step 5: Manual QA**

Run the local stack and verify:

- A `system_admin` can create department `0969`.
- A `system_admin` can create user `21P0031` under department `0969`.
- Editing the user's name and department refreshes the table.
- Deleting a user changes `use_yn` to `N`.
- Deleting a department with active users returns a conflict message.
- Service membership role assignment still searches Admin accounts, not
  organization users.

## Self-Review

- Spec coverage: The plan covers separate `users`, `departments`, and
  `admin_users`, avoids `users.admin_yn`, keeps RBAC on existing role tables,
  and adds Admin UI CRUD.
- Placeholder scan: No placeholder sections are intentionally left open.
- Type consistency: Backend field names use snake_case; frontend types mirror
  Admin API responses and requests.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-14-organization-directory-admin-accounts.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.
