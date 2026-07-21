# Release-Owned Environment Runtime Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move environment ownership from Service registration to Release/API key/runtime resolution so one logical Service can be tested, released to `dev`, `qa`, and `prod`, and called by runtime API keys without running one backend process per environment.

**Architecture:** Services become logical authorization units. Releases and API keys carry `environment`, runtime resolves environment from the verified API key record, and an operator allowlist limits which environments one backend process may serve. Admin UI and Admin API RBAC are updated so `service_owner` owns release/API-key/member operations for assigned Services, while `service_developer` can manage intents and tests but only read releases and runtime logs.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL/pgvector, pytest, React, TypeScript, Umi 4, Ant Design, ProComponents, Umi `request`, Vitest.

## Global Constraints

- Supported release/runtime environments are exactly `dev`, `qa`, and `prod`.
- Service creation must not collect or return `environment`.
- Service creation must not collect or return `default_threshold_preset`.
- Policy and threshold preset selection belong to policy/test-run flow, not Service registration.
- A passed test run may be reused to create one release per environment.
- API keys are bound to `service_id + environment + app_id` and follow the active release for that environment.
- Runtime environment must come from verified API key metadata, never from a caller-supplied environment header.
- Runtime backend may serve only environments included in `ALLOWED_RUNTIME_ENVIRONMENTS`.
- `system_admin` has all permissions and creates Services plus initial `service_owner`.
- `service_owner` can manage assigned-Service members, intents, tests, releases, API keys, and runtime logs, but cannot access Organization Directory, Permission Management, or Audit Logs.
- `service_developer` can manage assigned-Service intents and test runs, can read releases and runtime logs, but cannot access API Keys or Audit Logs and cannot write releases.
- Existing Services/releases/API keys do not need a data-preserving migration; local data will be deleted and re-registered.
- Normal Admin UI requests must keep using account-session cookies and Umi `request`; do not add browser trusted headers or axios.
- Removing Service-owned fields is a repository-wide contract change. Search and update every Service creation payload, direct `models.Service(...)` fixture, seed script, and frontend consumer before treating Task 1 as complete.
- `pilot` may remain a deployment/runbook scenario name, but it is not a supported runtime `environment` value after this change. Live runtime/release/API key environments must be `dev`, `qa`, or `prod`.
- Do not shrink `service_operator` or `auditor` permissions unless an explicit later decision says so. This plan only removes Audit Logs access from `service_owner` and `service_developer`, matching the accepted matrix.
- Runtime logs written before API key authentication can have `environment = NULL`. Admin UI must show them as `환경 미상`; unfiltered log views include them, while an explicit environment filter returns only that environment.
- `ALLOWED_RUNTIME_ENVIRONMENTS` must be validated through the config layer and must not surface as request-time 500s from raw parsing errors.

---

## File Map

- Modify: `src/intent_routing/config.py` - parse and validate supported runtime environment allowlist using the module's existing injectable environment mapping pattern.
- Modify: `src/intent_routing/main.py` - validate runtime environment allowlist during app creation/startup when practical.
- Modify: `src/intent_routing/db/models.py` - remove Service environment/default preset fields and add RuntimeLog environment.
- Create: `alembic/versions/0012_release_owned_environment.py` - destructive schema change without data backfill.
- Modify: `src/intent_routing/api/dependencies.py` - include authenticated key environment in `AuthContext` and enforce allowlist.
- Modify: `src/intent_routing/api/runtime.py` - load active release by `auth.environment` and log runtime environment.
- Modify: `src/intent_routing/logging/trace.py` - carry environment into runtime log inserts for success and error paths.
- Modify: `src/intent_routing/db/repositories.py` - support environment-aware runtime logs, log export, metrics, and release candidate checks.
- Modify: `src/intent_routing/api/admin.py` - update Service, Release, API key, runtime setup, membership, audit, and RBAC contracts.
- Modify: `src/intent_routing/versions/releases.py` - verify there is no global one-release-per-test-run validation; change only if such validation exists.
- Modify: `frontend/intent-routing-console/src/types/api.d.ts` - remove Service environment/default preset and add runtime log environment.
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts` - add route/action gates matching the accepted RBAC matrix.
- Modify: `frontend/intent-routing-console/src/components/adminShellNavigation.ts` - hide API Keys and Audit Logs for `service_developer`, hide Audit Logs for `service_owner`.
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx` - pass navigation roles without tying menu visibility only to the currently selected Service.
- Modify: `frontend/intent-routing-console/src/components/ServiceScopeBar.tsx` - remove Service environment badge because Service no longer owns environment.
- Modify: `frontend/intent-routing-console/src/pages/Services/serviceForm.ts` and `frontend/intent-routing-console/src/pages/Services/index.tsx` - remove Service environment/preset fields and allow `service_owner` membership management.
- Modify: `frontend/intent-routing-console/src/pages/Services/ServiceMembershipPanel.tsx` - copy and disabled states for owner-managed membership.
- Modify: `frontend/intent-routing-console/src/pages/Releases/index.tsx` and `ReleaseCandidateSelect.tsx` - environment selector and owner-only writes.
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx` - release/environment-first key creation for `service_owner`.
- Modify: `frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx` and `RuntimeLogsTable.tsx` - environment column/filter.
- Modify: `frontend/intent-routing-console/src/pages/AuditLogs/index.tsx` - hide Audit Logs from `service_owner` and `service_developer`; retain existing `auditor` access unless separately decided.
- Modify: `docs/api/admin-runtime-setup-contracts.md`, `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`, `docs/AdminUI_Handbook/v04/E2E_DX_QA_CHECKLIST.md` - contract and QA updates.
- Modify: `.env.example`, `.env.closed-network.example`, `.github/workflows/ci.yml`, `scripts/run_local_dev_stack.sh`, `scripts/run_local_dev_stack_macos.sh`, `scripts/seed_pilot.py`, and `scripts/rotate_api_key.py` - replace Service environment assumptions and keep script-created releases/API keys on `dev`/`qa`/`prod`.
- Modify: `docs/ops/intent-routing-pilot-runbook.md`, `docs/ops/pilot-e2e-smoke.md`, `docs/ops/ci-verification.md`, `docs/ops/closed-network-deployment.md`, and related contract-tested ops docs - remove `pilot` as runtime environment value.
- Test: `tests/integration/test_release_flow.py`
- Test: `tests/integration/test_runtime_api.py`
- Test: `tests/integration/test_admin_runtime_setup_api.py`
- Test: `tests/integration/test_admin_service_rbac_flow.py`
- Test: every test fixture currently passing `environment` or `default_threshold_preset` to Service creation, including catalog, permission, log retention, metrics, runtime, trace, seed, and pilot rehearsal tests.
- Test: `tests/unit/test_env_contract.py`
- Test: `tests/unit/test_ci_workflow_contract.py`
- Test: `tests/unit/test_closed_network_packaging_contract.py`
- Test: `tests/unit/test_seed_pilot.py`
- Test: `tests/unit/test_operator_docs_contract.py`
- Test: `frontend/intent-routing-console/src/models/adminSession.test.ts`
- Test: `frontend/intent-routing-console/src/components/adminShellNavigation.test.ts`
- Test: `frontend/intent-routing-console/src/pages/Services/serviceForm.test.ts`
- Test: `frontend/intent-routing-console/src/pages/Releases/releasesPageContract.test.ts`
- Test: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`
- Test: `frontend/intent-routing-console/src/components/runtimeLogsTableContract.test.ts`

---

## Task 1: Schema And Service Contract Reset

**Files:**
- Create: `alembic/versions/0012_release_owned_environment.py`
- Modify: `src/intent_routing/db/models.py`
- Modify: `src/intent_routing/api/admin.py`
- Modify: `tests/integration/test_release_flow.py`
- Modify: `tests/integration/test_admin_runtime_setup_api.py`
- Modify: all Service creation fixtures in `tests/integration`, `tests/unit`, and `scripts/seed_pilot.py`
- Modify: frontend Service consumers including `frontend/intent-routing-console/src/components/ServiceScopeBar.tsx`

**Interfaces:**
- Produces: `ServiceCreateRequest(service_id: str, display_name: str, max_input_tokens: int = 256)`
- Produces: `ServiceResponse` and `AccessibleServiceResponse` without `environment` or `default_threshold_preset`
- Produces: `RuntimeLog.environment: str | None`

- [ ] **Step 1: Write failing schema assertions**

Add or update the existing schema test in `tests/integration/test_release_flow.py`:

```python
def test_service_schema_drops_environment_and_default_preset(
    db_session: Session,
) -> None:
    columns = {
        row.column_name
        for row in db_session.execute(
            text(
                "select column_name from information_schema.columns "
                "where table_schema = 'public' and table_name = 'services'"
            )
        )
    }

    assert "service_id" in columns
    assert "display_name" in columns
    assert "max_input_tokens" in columns
    assert "environment" not in columns
    assert "default_threshold_preset" not in columns


def test_runtime_logs_include_environment_column(db_session: Session) -> None:
    columns = {
        row.column_name: row.data_type
        for row in db_session.execute(
            text(
                "select column_name, data_type from information_schema.columns "
                "where table_schema = 'public' and table_name = 'runtime_logs'"
            )
        )
    }

    assert columns["environment"] == "text"
```

- [ ] **Step 2: Run schema tests to verify failure**

Run:

```bash
uv run pytest tests/integration/test_release_flow.py::test_service_schema_drops_environment_and_default_preset tests/integration/test_release_flow.py::test_runtime_logs_include_environment_column -q
```

Expected: first test fails because `services.environment` and `services.default_threshold_preset` still exist; second test fails because `runtime_logs.environment` is missing.

- [ ] **Step 3: Add destructive Alembic revision**

Create `alembic/versions/0012_release_owned_environment.py`:

```python
"""release owned environment

Revision ID: 0012_release_owned_environment
Revises: 0011_api_key_optional_expiry
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0012_release_owned_environment"
down_revision: str | None = "0011_api_key_optional_expiry"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("services", "default_threshold_preset")
    op.drop_column("services", "environment")
    op.add_column("runtime_logs", sa.Column("environment", sa.Text(), nullable=True))
    op.create_index(
        "ix_runtime_logs_service_environment_created",
        "runtime_logs",
        ["service_id", "environment", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_logs_service_environment_created",
        table_name="runtime_logs",
    )
    op.drop_column("runtime_logs", "environment")
    op.add_column(
        "services",
        sa.Column("environment", sa.Text(), nullable=False, server_default="dev"),
    )
    op.add_column(
        "services",
        sa.Column(
            "default_threshold_preset",
            sa.Text(),
            nullable=False,
            server_default="balanced",
        ),
    )
```

- [ ] **Step 4: Update SQLAlchemy models**

In `src/intent_routing/db/models.py`, remove these fields from `Service`:

```python
environment: Mapped[str] = mapped_column(Text)
default_threshold_preset: Mapped[str] = mapped_column(
    Text, server_default=text("'balanced'")
)
```

Add this field to `RuntimeLog` near `service_id`:

```python
environment: Mapped[str | None] = mapped_column(Text)
```

- [ ] **Step 5: Update Service API schemas and create path**

In `src/intent_routing/api/admin.py`, change `ServiceCreateRequest`, `ServiceResponse`, and `AccessibleServiceResponse`:

```python
class ServiceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    max_input_tokens: int = Field(default=256, ge=1)


class ServiceResponse(BaseModel):
    service_id: str
    display_name: str
    max_input_tokens: int
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class AccessibleServiceResponse(BaseModel):
    service_id: str
    display_name: str
    status: str
    roles: list[str]
```

Update `create_service` so repository creation no longer passes environment or default preset:

```python
service = repository.create_service(
    service_id=request.service_id,
    display_name=request.display_name,
    max_input_tokens=request.max_input_tokens,
    status="active",
    created_by=context.actor_id,
    created_at=now,
    updated_at=now,
)
```

Update `_service_response` and `_accessible_service_response` to omit the removed fields.

- [ ] **Step 6: Update every Service creation fixture and consumer**

First enumerate all affected paths:

```bash
rg -n "default_threshold_preset|environment=.*balanced|\"environment\": \"dev\"|\"environment\": \"test\"|models\.Service\(" tests scripts src frontend/intent-routing-console/src
rg -n "selectedService\?\.environment|selectedService\.environment|row\.environment" frontend/intent-routing-console/src
```

Change Service create API payloads from:

```python
json={
    "service_id": service_id,
    "display_name": "Runtime Setup Service",
    "environment": "dev",
    "default_threshold_preset": "balanced",
    "max_input_tokens": 256,
}
```

to:

```python
json={
    "service_id": service_id,
    "display_name": "Runtime Setup Service",
    "max_input_tokens": 256,
}
```

Remove `environment=` and `default_threshold_preset=` from direct `models.Service(...)` fixtures. Update `scripts/seed_pilot.py` so its `--environment` argument is used for release/API key creation only, not Service creation.

Remove Service environment rendering from `ServiceScopeBar.tsx` and Services page Service cards/tables. Environment should appear only in Release/API Key/Runtime Log contexts.

- [ ] **Step 7: Run schema and service creation tests**

Run:

```bash
uv run pytest tests/integration/test_release_flow.py::test_service_schema_drops_environment_and_default_preset tests/integration/test_release_flow.py::test_runtime_logs_include_environment_column tests/integration/test_admin_runtime_setup_api.py -q
uv run pytest tests/integration/test_admin_catalog_api.py tests/integration/test_admin_service_rbac_flow.py tests/integration/test_catalog_version_management_api.py tests/integration/test_permission_management_api.py tests/integration/test_runtime_api.py tests/integration/test_trace_audit_logs.py tests/unit/test_seed_pilot.py tests/unit/test_permission_management_repository.py -q
cd frontend/intent-routing-console && ./node_modules/.bin/tsc --noEmit
```

Expected: PASS for changed contract tests after the DB schema is at Alembic head, and no TypeScript references to removed Service fields remain.

---

## Task 2: Runtime Environment Resolution From API Key

**Files:**
- Modify: `src/intent_routing/config.py`
- Modify: `src/intent_routing/main.py`
- Modify: `src/intent_routing/api/dependencies.py`
- Modify: `src/intent_routing/api/runtime.py`
- Modify: `src/intent_routing/logging/trace.py`
- Modify: `tests/integration/test_runtime_api.py`
- Modify: `tests/unit/test_env_contract.py`

**Interfaces:**
- Consumes: `ApiKeyRecord.environment`
- Produces: `AuthContext.environment: str`
- Produces: `get_allowed_runtime_environments() -> frozenset[str]`
- Produces: runtime release lookup using `auth.environment`

- [ ] **Step 1: Write failing allowlist unit tests**

Add tests in `tests/unit/test_env_contract.py`:

```python
def test_runtime_environment_allowlist_defaults_to_dev_qa_prod(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOWED_RUNTIME_ENVIRONMENTS", raising=False)

    from intent_routing.config import get_allowed_runtime_environments

    assert get_allowed_runtime_environments() == frozenset({"dev", "qa", "prod"})


def test_runtime_environment_allowlist_rejects_unknown_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOWED_RUNTIME_ENVIRONMENTS", "dev,test,prod")

    from intent_routing.config import get_allowed_runtime_environments

    with pytest.raises(ValueError, match="unsupported runtime environment"):
        get_allowed_runtime_environments()
```

- [ ] **Step 2: Implement allowlist parser and startup validation**

Add to `src/intent_routing/config.py`:

```python
SUPPORTED_RUNTIME_ENVIRONMENTS = frozenset({"dev", "qa", "prod"})


class RuntimeEnvironmentConfigError(ValueError):
    """Raised when runtime environment allowlist configuration is invalid."""


def get_allowed_runtime_environments(
    environ: Mapping[str, str] | None = None,
) -> frozenset[str]:
    env = process_environ if environ is None else environ
    raw_value = env.get("ALLOWED_RUNTIME_ENVIRONMENTS", "dev,qa,prod")
    values = frozenset(
        value.strip()
        for value in raw_value.split(",")
        if value.strip()
    )
    unknown = values - SUPPORTED_RUNTIME_ENVIRONMENTS
    if unknown:
        raise RuntimeEnvironmentConfigError(
            "unsupported runtime environment values: " + ", ".join(sorted(unknown))
        )
    if not values:
        raise RuntimeEnvironmentConfigError("ALLOWED_RUNTIME_ENVIRONMENTS must not be empty")
    return values
```

Use the existing `from os import environ as process_environ` pattern in this module. Validate the allowlist once during app creation/startup where the app already validates configuration. If startup validation cannot be wired cleanly without broad refactoring, catch `RuntimeEnvironmentConfigError` in `require_api_key` and convert it to the existing runtime error envelope instead of leaking a raw 500.

- [ ] **Step 3: Write failing runtime auth tests**

In `tests/integration/test_runtime_api.py`, add:

```python
def test_intent_route_uses_api_key_environment_for_release_lookup(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOWED_RUNTIME_ENVIRONMENTS", "dev,qa,prod")
    service_id = f"svc-runtime-key-env-{uuid4().hex}"
    secret = "valid-runtime-secret"
    key_id = "key-live"
    app = create_app()
    app.dependency_overrides[get_api_key_lookup] = lambda: lambda _key_id: _record_for(
        secret,
        service_id=service_id,
        environment="qa",
    )
    client = TestClient(app)

    _seed_successful_release(
        db_session,
        service_id=service_id,
        environment="qa",
        release_version=f"rel-{service_id}-qa",
    )

    response = client.post(
        "/v1/intent-route",
        headers=_headers(
            secret,
            **{
                "X-Key-Id": key_id,
                "X-App-Id": "app-a",
                "X-Service-Id": service_id,
                "X-Request-Id": "runtime-key-env-001",
            },
        ),
        json=_runtime_payload(workflow_run_id="runtime-key-env-001"),
    )

    assert response.status_code == 200
    assert response.json()["release_version"] == f"rel-{service_id}-qa"
```

Use the existing runtime release fixture helpers where available; if they are named differently, extend the existing helper rather than creating a second fixture family. In the current runtime tests, `_record_for(...)` must accept `service_id` instead of hard-coding `"svc-a"`, and `_seed_runtime_state`/active-release helpers must accept `environment`.

Also add these cases in the same `TestClient` app instance:

- A `dev` API key and a `prod` API key for the same Service route to different active release versions, proving one backend serves multiple allowed environments.
- `ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa` rejects a valid `prod` key with `401` and `AUTHENTICATION_FAILED`.
- Invalid allowlist configuration is caught at startup or mapped to an intentional error path; it must not appear as an unhandled request-time `ValueError`.

- [ ] **Step 4: Add environment to AuthContext**

In `src/intent_routing/api/dependencies.py`, change:

```python
@dataclass(frozen=True)
class AuthContext:
    key_id: str
    app_id: str
    service_id: str
    environment: str
    request_id: str | None
    allowed_intents: list[str]
    allowed_route_keys: list[str]
```

Import `get_allowed_runtime_environments` and replace the process-environment equality check. Remove `environment: Depends(get_runtime_environment)` from `require_api_key`; `get_runtime_environment` must not be a hidden dependency that tests can override without effect.

```python
allowed_environments = get_allowed_runtime_environments()
if record.environment not in allowed_environments:
    _raise_authentication_failed(request_id)
```

Return:

```python
return AuthContext(
    key_id=record.key_id,
    app_id=record.app_id,
    service_id=record.service_id,
    environment=record.environment,
    request_id=request_id,
    allowed_intents=record.allowed_intents,
    allowed_route_keys=record.allowed_route_keys,
)
```

Keep `X-App-Id`, `X-Service-Id`, `X-Key-Id`, and Bearer secret checks unchanged.

- [ ] **Step 5: Runtime loads release from authenticated key environment**

In `src/intent_routing/api/runtime.py`, remove the dependency parameter:

```python
environment: Annotated[str, Depends(get_runtime_environment)],
```

Then change release lookup:

```python
release = _load_active_release(
    repository,
    service_id=auth.service_id,
    environment=auth.environment,
)
```

Pass `environment=auth.environment` into runtime trace logging once Task 3 adds that parameter.

- [ ] **Step 6: Run runtime tests**

Run:

```bash
uv run pytest tests/unit/test_env_contract.py tests/integration/test_runtime_api.py -q
rg -n "get_runtime_environment" src/intent_routing tests/integration/test_runtime_api.py tests/integration/test_release_flow.py
```

Expected: PASS. Remaining `get_runtime_environment` matches must be either deleted or explicitly documented as legacy non-routing configuration; runtime auth and release lookup must not depend on it.

---

## Task 3: Runtime Logs And Metrics Environment Visibility

**Files:**
- Modify: `src/intent_routing/logging/trace.py`
- Modify: `src/intent_routing/api/runtime.py`
- Modify: `src/intent_routing/db/repositories.py`
- Modify: `src/intent_routing/api/admin.py`
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/components/RuntimeLogsTable.tsx`
- Modify: `frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx`
- Test: `tests/integration/test_trace_audit_logs.py`
- Test: `frontend/intent-routing-console/src/components/runtimeLogsTableContract.test.ts`

**Interfaces:**
- Produces: runtime log responses include `environment: str | None`
- Produces: Admin API supports `GET /admin/v1/services/{sid}/runtime-logs?environment=qa`
- Produces: runtime log export and metrics either filter by environment or explicitly document that they aggregate all environments
- Produces: pre-authentication runtime errors remain visible with `environment = NULL`

- [ ] **Step 1: Write failing backend runtime log assertion**

In `tests/integration/test_trace_audit_logs.py`, add an assertion after a successful runtime call:

```python
runtime_log = db_session.scalar(
    select(models.RuntimeLog).where(models.RuntimeLog.request_id == "trace-env-001")
)
assert runtime_log is not None
assert runtime_log.environment == "qa"
```

- [ ] **Step 2: Carry environment through runtime trace logger**

In `src/intent_routing/logging/trace.py`, add `environment: str | None` to `log_success` and error logging payload methods. Ensure `repository.insert_runtime_log` receives:

```python
environment=environment,
```

In `src/intent_routing/api/runtime.py`, call those methods with:

```python
environment=auth.environment,
```

For `log_runtime_preflight_error`, do not invent an environment from a client header. Store `environment=None` and ensure the response/list path can display that row as `환경 미상`.

- [ ] **Step 3: Add repository filtering for list, export, and metrics**

In `src/intent_routing/db/repositories.py`, extend masked runtime log list methods:

```python
def list_masked_runtime_logs(
    self,
    service_id: str,
    *,
    environment: str | None = None,
    limit: int = 100,
) -> list[Mapping[str, Any]]:
    statement = select(*_masked_runtime_log_columns()).where(
        models.RuntimeLog.service_id == service_id
    )
    if environment is not None:
        statement = statement.where(models.RuntimeLog.environment == environment)
    ...
```

Add `models.RuntimeLog.environment` to `_masked_runtime_log_columns()`.

Apply the same field and optional filter to `list_masked_runtime_logs_for_export`. If `runtime_metrics` remains environment-aggregated, rename the plan/file-map wording to make that explicit; otherwise add `environment: str | None = None` to the repository and `ops/metrics.py` path so dev/qa/prod traffic does not collapse into one metric view.

- [ ] **Step 4: Add Admin API query param and response field**

In `src/intent_routing/api/admin.py`, add `environment` to `RuntimeLogResponse` and route:

```python
environment: str | None
```

```python
def list_runtime_logs(
    service_id: str,
    ...,
    environment: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[RuntimeLogResponse]:
    ...
    repository.list_masked_runtime_logs(
        service_id,
        environment=environment,
        limit=limit,
    )
```

The default runtime log response must include `NULL` environment rows. With `?environment=qa`, return only rows whose environment is `qa`.

- [ ] **Step 5: Update frontend table and filter contract**

In `frontend/intent-routing-console/src/types/api.d.ts`, add to `RuntimeLog`:

```ts
environment: string | null;
```

In `RuntimeLogsTable.tsx`, add a compact column:

```tsx
{
  title: 'Environment',
  dataIndex: 'environment',
  width: 120,
  render: (_, row) =>
    row.environment ? <StatusTag status={row.environment} label={row.environment} /> : '없음',
}
```

In `RuntimeLogs/index.tsx`, add an environment filter with `전체`, `dev`, `qa`, and `prod`. `전체` must not send an environment query parameter, so authentication/preflight failures with `environment=null` remain visible.

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/integration/test_trace_audit_logs.py -q
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/components/runtimeLogsTableContract.test.ts
```

Expected: PASS. Add or update assertions proving `environment=None` renders as `환경 미상` and explicit environment filters do not accidentally hide all unfiltered error logs.

---

## Task 4: Release Environment Selection And Candidate Reuse

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Inspect: `src/intent_routing/versions/releases.py`
- Modify: `tests/integration/test_release_flow.py`
- Modify: `frontend/intent-routing-console/src/pages/Releases/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Releases/ReleaseCandidateSelect.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Releases/releasesPageContract.test.ts`

**Interfaces:**
- Consumes: `ReleaseCreateRequest.environment: Literal["dev", "qa", "prod"]`
- Produces: same `test_run_id` may create releases in several environments
- Produces: release writes require `service_owner` or `system_admin`

- [ ] **Step 1: Write failing backend release reuse test**

In `tests/integration/test_release_flow.py`, add:

```python
def test_passed_test_run_can_release_to_dev_qa_and_prod(
    db_session: Session,
) -> None:
    client, service_id, owner = _client_with_service_owner(db_session)
    test_run = _seed_gate_passed_test_run(db_session, service_id)

    versions = []
    for environment in ("dev", "qa", "prod"):
        response = client.post(
            f"/admin/v1/services/{service_id}/releases",
            json={
                "environment": environment,
                "policy_version": test_run.policy_version,
                "intent_catalog_version": test_run.intent_catalog_version,
                "test_run_id": test_run.test_run_id,
                "rollback_target": None,
            },
        )
        assert response.status_code == 201, response.text
        versions.append(response.json()["release_version"])

    assert len(set(versions)) == 3
```

Adapt helper names to the existing fixture style in the file. The important assertions are three `201` responses and three distinct releases.

- [ ] **Step 2: Remove Service environment validation**

In `src/intent_routing/api/admin.py`, delete this check from `create_release`:

```python
if request.environment != service.environment:
    _raise_bad_request("Release environment must match service environment.")
```

Replace environment validation with:

```python
if request.environment not in SUPPORTED_RUNTIME_ENVIRONMENTS:
    _raise_bad_request("Release environment must be one of dev, qa, prod.")
```

- [ ] **Step 3: Allow existing release check per selected environment**

In `list_release_candidates`, remove every fallback to `service.environment`; `environment` must be supplied by query parameter or explicitly default to `dev` after validation against `dev`, `qa`, `prod`.

`repository.list_releases(service_id, target_environment)` already filters by environment, so the existing `{release.test_run_id: release}` map is sufficient unless the function is changed to fetch all environments. If it continues to fetch one environment at a time, keep the smaller diff.

Remove the `environment_matches_service` block reason and condition. Keep `gate_passed`, `risk_passed`, and environment-specific existing release checks.

- [ ] **Step 4: Verify release service validation**

Inspect `src/intent_routing/versions/releases.py` and the release table constraints. If there is no validation or unique constraint that assumes one test run has one release globally, record "no code change required" in the task notes instead of adding a new abstraction. Keep dependency checks for policy, catalog, model, vector index, and gate pass.

- [ ] **Step 5: Update Releases UI environment selector**

In `frontend/intent-routing-console/src/pages/Releases/index.tsx`, replace `selectedEnvironment = selectedService?.environment || 'prod'` with local state:

```tsx
const environmentOptions = [
  { label: 'dev', value: 'dev' },
  { label: 'qa', value: 'qa' },
  { label: 'prod', value: 'prod' },
];
const [selectedEnvironment, setSelectedEnvironment] =
  useState<'dev' | 'qa' | 'prod'>('dev');
```

Render a `Select` before candidate load:

```tsx
<Form.Item label={helpLabel('Environment', 'Release를 생성할 대상 환경입니다.')}>
  <Select
    value={selectedEnvironment}
    options={environmentOptions}
    onChange={(value) => {
      setSelectedEnvironment(value);
      form.resetFields();
      setCandidates([]);
      setReleaseRows([]);
    }}
    style={{ width: 180 }}
  />
</Form.Item>
```

Keep `createRelease` payload using `selectedEnvironment`.

- [ ] **Step 6: Owner-only release write gate**

In `frontend/intent-routing-console/src/models/adminSession.ts`, change:

```ts
export const canManageReleases = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin', 'service_owner']);

export const canReadReleases = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin', 'service_owner', 'service_developer']);
```

Use `canReadReleases` for page access/read rendering and `canManageReleases` for create/activate/rollback buttons.

- [ ] **Step 7: Run release tests**

Run:

```bash
uv run pytest tests/integration/test_release_flow.py -q
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/pages/Releases/releasesPageContract.test.ts src/models/adminSession.test.ts
```

Expected: PASS.

---

## Task 5: API Keys By Released Environment

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Modify: `tests/integration/test_admin_runtime_setup_api.py`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
- Modify: `docs/api/admin-runtime-setup-contracts.md`

**Interfaces:**
- Consumes: selected `environment: "dev" | "qa" | "prod"`
- Produces: key creation allowed only for `service_owner` or `system_admin`
- Produces: API key scope candidates come from active release for selected environment
- Produces: both service-scoped and transitional global API key endpoints reject unsupported environments

- [ ] **Step 1: Write failing service_developer API key denial test**

In `tests/integration/test_admin_runtime_setup_api.py`, add:

```python
def test_service_developer_cannot_create_runtime_api_key(
    db_session: Session,
) -> None:
    system_client, _ = _system_admin_client(db_session)
    service_id = f"svc-key-rbac-{uuid4().hex}"
    _create_service(system_client, service_id)
    _seed_active_release(db_session, service_id, environment="qa")
    developer_client, _ = _application_admin_client(
        db_session,
        service_roles=((service_id, "service_developer"),),
    )

    response = developer_client.post(
        f"/admin/v1/services/{service_id}/api-keys",
        json={
            "environment": "qa",
            "app_id": "postman",
            "allowed_intents": [],
            "allowed_route_keys": [],
            "expires_in_days": 90,
        },
    )

    assert response.status_code == 403
```

- [ ] **Step 2: Update API key management access**

In `src/intent_routing/api/admin.py`, change `_require_api_key_management_access`:

```python
def _require_api_key_management_access(
    context: AdminContext,
    service_id: str,
) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_service_role(service_id, "service_owner"):
        return
    raise_admin_forbidden("API key management scope is required for this action.")
```

Update copy in error tests if they assert the old role list.

- [ ] **Step 3: Remove Service environment validation and close global API key bypass**

Replace `_runtime_setup_environment` with explicit environment validation that does not read `service.environment`:

```python
def _runtime_setup_environment(environment: str | None) -> str:
    target_environment = environment or "dev"
    if target_environment not in SUPPORTED_RUNTIME_ENVIRONMENTS:
        _raise_validation_failed("environment must be one of dev, qa, prod.")
    return target_environment
```

Update callers:

```python
target_environment = _runtime_setup_environment(environment)
```

and:

```python
environment = _runtime_setup_environment(request.environment)
```

Apply this to both:

- `POST /admin/v1/services/{service_id}/api-keys`
- transitional `POST /admin/v1/api-keys`

Prefer request-schema validation for `ApiKeyCreateRequest.environment` and `ServiceApiKeyCreateRequest.environment` so unsupported values fail with 422 before database writes. Keep active-release scope candidate loading tied to the selected environment; if key creation requires an active release, assert that in both endpoints and tests.

Also update `list_intent_route_candidates` so `source=active_release` never falls back to `service.environment`; missing or unsupported environment should be a 422-style validation error.

- [ ] **Step 4: API Keys UI environment/release selection**

In `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`, replace selected Service environment usage with state:

```tsx
const environmentOptions = [
  { label: 'dev', value: 'dev' },
  { label: 'qa', value: 'qa' },
  { label: 'prod', value: 'prod' },
];
const [selectedEnvironment, setSelectedEnvironment] =
  useState<'dev' | 'qa' | 'prod'>('dev');
```

Load keys, active release scope candidates, and runtime setup guidance with that state:

```tsx
listServiceApiKeys(serviceId, { environment: selectedEnvironment })
listIntentRouteCandidates(serviceId, {
  source: 'active_release',
  environment: selectedEnvironment,
})
fetchRuntimeSetupGuidance(serviceId, {
  environment: selectedEnvironment,
  app_id: selectedKey?.app_id,
  key_id: selectedKey?.key_id,
})
```

Render a top control:

```tsx
<Form.Item label={helpLabel('Released environment', 'API key가 사용할 active Release 환경입니다.')}>
  <Select
    value={selectedEnvironment}
    options={environmentOptions}
    onChange={(value) => {
      setSelectedEnvironment(value);
      setCreatedKey(undefined);
      setKeys([]);
      setScopeCandidates([]);
      setRuntimeSetup(undefined);
    }}
    style={{ width: 180 }}
  />
</Form.Item>
```

- [ ] **Step 5: Owner-only UI gate**

In `frontend/intent-routing-console/src/models/adminSession.ts`, change:

```ts
export const canManageApiKeys = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin', 'service_owner']);

export const canManageRuntimeSetup = (session: AdminSession) =>
  canManageApiKeys(session);
```

Update `runtimeSetup.test.ts` to assert page copy says `system_admin` or `service_owner`, not `service_developer`.

- [ ] **Step 6: Run API key tests**

Run:

```bash
uv run pytest tests/integration/test_admin_runtime_setup_api.py -q
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/pages/ApiKeys/runtimeSetup.test.ts src/models/adminSession.test.ts
```

Expected: PASS.

---

## Task 6: Service Membership Delegation To service_owner

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Modify: `tests/integration/test_admin_service_rbac_flow.py`
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
- Modify: `frontend/intent-routing-console/src/pages/Services/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Services/ServiceMembershipPanel.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Services/membershipPanelContract.test.ts`

**Interfaces:**
- Produces: `service_owner` can list/grant/revoke roles for its assigned Service only
- Produces: `service_developer` can access Services page read-only

- [ ] **Step 1: Write failing owner membership test**

In `tests/integration/test_admin_service_rbac_flow.py`, add:

```python
def test_service_owner_can_manage_members_only_for_assigned_service(
    db_session: Session,
) -> None:
    system_client, service_a, service_b, owner_user, target_user = (
        _seed_two_services_with_owner_and_target(db_session)
    )
    owner_client = _client_for_admin_user(db_session, owner_user)

    allowed = owner_client.post(
        f"/admin/v1/services/{service_a}/members/{target_user}/roles",
        json={"role": "service_developer"},
    )
    denied = owner_client.post(
        f"/admin/v1/services/{service_b}/members/{target_user}/roles",
        json={"role": "service_developer"},
    )

    assert allowed.status_code == 200
    assert denied.status_code == 403
```

Use existing helper patterns in this file; do not create a second client/session framework.

- [ ] **Step 2: Add membership access helper**

In `src/intent_routing/api/admin.py`, add:

```python
def _require_service_membership_management_access(
    context: AdminContext,
    service_id: str,
) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_service_role(service_id, "service_owner"):
        return
    raise_admin_forbidden("Service owner scope is required for membership management.")
```

Use it in:

```python
list_service_members
grant_service_member_role
revoke_service_member_role
```

Keep `/admin/v1/users` search `system_admin` only unless the implementation adds a Service-scoped user lookup endpoint. If keeping `/users` system-admin-only blocks owner membership UI, add `GET /admin/v1/services/{service_id}/member-candidates?query=` guarded by `_require_service_membership_management_access`.

- [ ] **Step 3: Update Services UI gates**

In `frontend/intent-routing-console/src/models/adminSession.ts`, change:

```ts
export const canManageServiceMembers = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin', 'service_owner']);

export const canUseServicesPage = (session: AdminSession) =>
  Boolean(
    session.authenticated &&
      session.user &&
      (session.serviceId.trim() || canCreateServices(session)),
  );
```

Ensure create Service remains:

```ts
export const canCreateServices = (session: AdminSession) =>
  session.globalRoles.includes('system_admin');
```

- [ ] **Step 4: Update membership copy**

In `ServiceMembershipPanel.tsx`, replace forbidden copy:

```tsx
? '멤버 목록을 보려면 system_admin 또는 service_owner 권한이 필요합니다.'
```

and:

```tsx
? '관리자 계정 검색에는 system_admin 또는 service_owner 권한이 필요합니다.'
```

If a Service-scoped member candidate endpoint is added, switch `searchAdminUsers` to `searchServiceMemberCandidates(serviceId, { query, limit: 25 })`.

- [ ] **Step 5: Run membership tests**

Run:

```bash
uv run pytest tests/integration/test_admin_service_rbac_flow.py -q
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/pages/Services/membershipPanelContract.test.ts src/models/adminSession.test.ts
```

Expected: PASS.

---

## Task 7: Admin UI Navigation And Action Matrix

**Files:**
- Modify: `frontend/intent-routing-console/src/components/adminShellNavigation.ts`
- Modify: `frontend/intent-routing-console/src/components/adminShellNavigation.test.ts`
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/AuditLogs/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Releases/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`

**Interfaces:**
- Produces: navigation filtered by global roles plus the union of accessible Service roles, not only the currently selected Service role
- Produces: Audit Logs menu hidden for `service_owner` and `service_developer`; keep existing `auditor` visibility unless a later decision removes it
- Produces: API Keys menu visible to `system_admin` and `service_owner`

- [ ] **Step 1: Write failing navigation tests**

In `adminShellNavigation.test.ts`, add:

```ts
it('matches service owner navigation without platform admin screens or audit logs', () => {
  const routePaths = paths(['service_owner']);

  expect(routePaths).toContain('/services');
  expect(routePaths).toContain('/intents');
  expect(routePaths).toContain('/test-runs');
  expect(routePaths).toContain('/releases');
  expect(routePaths).toContain('/api-keys');
  expect(routePaths).toContain('/runtime-logs');
  expect(routePaths).not.toContain('/organization-directory');
  expect(routePaths).not.toContain('/permission-management');
  expect(routePaths).not.toContain('/audit-logs');
});

it('matches service developer navigation with read-only releases and no api keys', () => {
  const routePaths = paths(['service_developer']);

  expect(routePaths).toContain('/services');
  expect(routePaths).toContain('/intents');
  expect(routePaths).toContain('/test-runs');
  expect(routePaths).toContain('/releases');
  expect(routePaths).toContain('/runtime-logs');
  expect(routePaths).not.toContain('/api-keys');
  expect(routePaths).not.toContain('/audit-logs');
});

it('keeps existing auditor audit-log navigation', () => {
  const routePaths = paths(['auditor']);

  expect(routePaths).toContain('/audit-logs');
});
```

- [ ] **Step 2: Make route specs role-aware**

Change `AdminShellRouteSpec`:

```ts
export type AdminShellRouteSpec = {
  path: string;
  name: string;
  icon: AdminShellRouteIcon;
  allowedRoles?: string[];
};
```

Set route specs:

```ts
{ path: '/organization-directory', name: '조직 디렉터리', icon: 'organizationDirectory', allowedRoles: ['system_admin'] },
{ path: '/permission-management', name: '권한관리', icon: 'permissionManagement', allowedRoles: ['system_admin'] },
{ path: '/api-keys', name: 'API Keys', icon: 'apiKeys', allowedRoles: ['system_admin', 'service_owner'] },
{ path: '/audit-logs', name: 'Audit Logs', icon: 'auditLogs', allowedRoles: ['system_admin', 'auditor'] },
```

Implement:

```ts
export function getAdminShellRouteSpecs(navigationRoles: readonly string[] = []) {
  const roleSet = new Set(navigationRoles);

  return ADMIN_SHELL_ROUTE_SPECS.filter(
    (route) =>
      !route.allowedRoles ||
      route.allowedRoles.some((role) => roleSet.has(role)),
  );
}
```

- [ ] **Step 3: Ensure AdminShell passes stable navigation roles**

In `AdminShell.tsx`, pass navigation roles derived from global roles plus all roles from accessible Services. Do not use only `getDisplayRoles(session)` if that value depends solely on the currently selected Service; otherwise `/api-keys` can disappear before a user selects a Service.

```tsx
const routeSpecs = getAdminShellRouteSpecs(navigationRoles);
```

Page-level read/write gates must still use the selected Service role so an owner of Service A cannot manage Service B.

- [ ] **Step 4: Add action gate tests**

In `adminSession.test.ts`, assert:

```ts
expect(canManageReleases(ownerSession)).toBe(true);
expect(canManageReleases(developerSession)).toBe(false);
expect(canManageApiKeys(ownerSession)).toBe(true);
expect(canManageApiKeys(developerSession)).toBe(false);
expect(canManageServiceMembers(ownerSession)).toBe(true);
expect(canManageServiceMembers(developerSession)).toBe(false);
```

- [ ] **Step 5: Run navigation tests**

Run:

```bash
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/components/adminShellNavigation.test.ts src/models/adminSession.test.ts
```

Expected: PASS.

---

## Task 8: Backend RBAC Tightening For Releases, API Keys, Logs, And Audit

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Modify: `tests/integration/test_admin_service_rbac_flow.py`
- Modify: `tests/integration/test_admin_runtime_setup_api.py`
- Modify: `tests/integration/test_trace_audit_logs.py`

**Interfaces:**
- Produces: service_owner write access for release/API key
- Produces: service_developer read access for releases/runtime logs but no API key or audit log access
- Produces: Audit Logs access removed from `service_owner` and `service_developer`; existing `service_operator`/`auditor` policy is retained unless separately decided
- Produces: governed publish activation cannot be used by `service_developer` to activate releases

- [ ] **Step 1: Write failing RBAC tests**

Add assertions:

```python
def test_service_developer_can_read_releases_but_cannot_create_release(
    db_session: Session,
) -> None:
    service_id = f"svc-release-rbac-{uuid4().hex}"
    developer_client = _client_with_service_role(
        db_session,
        service_id=service_id,
        role="service_developer",
    )

    list_response = developer_client.get(f"/admin/v1/services/{service_id}/releases")
    create_response = developer_client.post(
        f"/admin/v1/services/{service_id}/releases",
        json={
            "environment": "qa",
            "policy_version": "pol-missing",
            "intent_catalog_version": "cat-missing",
            "test_run_id": "tr-missing",
        },
    )

    assert list_response.status_code == 200
    assert create_response.status_code == 403
```

```python
def test_service_owner_and_developer_cannot_read_service_audit_logs(
    db_session: Session,
) -> None:
    for role in ("service_owner", "service_developer"):
        service_id = f"svc-audit-rbac-{role}-{uuid4().hex}"
        client = _client_with_service_role(
            db_session,
            service_id=service_id,
            role=role,
        )
        response = client.get(f"/admin/v1/services/{service_id}/audit-logs")
        assert response.status_code == 403
```

- [ ] **Step 2: Split role constants**

In `src/intent_routing/api/admin.py`, replace broad constants with:

```python
SERVICE_CATALOG_WRITE_ROLES = frozenset({"service_owner", "service_developer"})
SERVICE_RELEASE_WRITE_ROLES = frozenset({"service_owner"})
SERVICE_API_KEY_WRITE_ROLES = frozenset({"service_owner"})
SERVICE_LOG_READ_ROLES = frozenset({"service_owner", "service_developer", "service_operator", "auditor"})
SERVICE_METRICS_READ_ROLES = frozenset({"service_owner", "service_developer", "service_operator"})
SERVICE_AUDIT_LOG_READ_ROLES = frozenset({"service_operator", "auditor"})
```

Then update:

```python
_require_service_catalog_access
_require_release_management_access
_require_api_key_management_access
_require_runtime_log_access
_require_runtime_metrics_access
_require_service_audit_log_access
```

so `system_admin` still bypasses all checks.

- [ ] **Step 3: Release read endpoint remains developer-readable**

Prefer reusing the existing `_require_release_review_access` for release list/candidate/read endpoints if its role set still matches the retained `auditor` behavior. Introduce a new helper only if there is a confirmed reason to make release list/read stricter than release diff/review.

```python
def _require_release_read_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(
        service_id,
        {"service_owner", "service_developer", "auditor"},
    ):
        return
    raise_admin_forbidden("Release read scope is required for this action.")
```

Use the chosen release-read helper for `list_releases`, `list_release_candidates`, and active release reads. Keep create/activate/rollback on `_require_release_management_access`.

- [ ] **Step 4: Close governed publish release-write bypass**

Inspect `_require_publish_request_access`, `_require_publish_decision_access`, and `_require_publish_activation_access`.

Accepted policy:

- `service_developer` may create a publish request only if that request does not create, activate, or rollback a release.
- Publish decision and publish activation are release-write operations and require `service_owner` or `system_admin`.
- If the governed publish flow no longer matches the accepted "no separate approval, owner releases" policy, leave request read/proposal behavior intact but prevent developer activation.

Add a regression test proving `service_developer` cannot activate a governed publish/release path.

- [ ] **Step 5: Run backend RBAC tests**

Run:

```bash
uv run pytest tests/integration/test_admin_service_rbac_flow.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_trace_audit_logs.py -q
uv run pytest tests/integration -k publish -q
```

Expected: PASS.

---

## Task 9: Admin UI Service, Release, API Key, And Log UX

**Files:**
- Modify: `frontend/intent-routing-console/src/components/ServiceScopeBar.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Services/serviceForm.ts`
- Modify: `frontend/intent-routing-console/src/pages/Services/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Releases/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/RuntimeLogs/index.tsx`
- Test: `frontend/intent-routing-console/src/pages/Services/serviceForm.test.ts`
- Test: `frontend/intent-routing-console/src/pages/Services/servicesPagePresentation.test.ts`
- Test: `frontend/intent-routing-console/src/pages/Releases/releasesPageContract.test.ts`
- Test: `frontend/intent-routing-console/src/pages/ApiKeys/runtimeSetup.test.ts`

**Interfaces:**
- Produces: Service create form only collects service ID, display name, max input tokens
- Produces: Releases page has `dev/qa/prod` selector and owner-only writes
- Produces: API Keys page has released environment selector and owner-only access
- Produces: Service scope bar no longer displays an environment owned by Service
- Produces: Runtime Logs page can filter by `dev`/`qa`/`prod` while preserving the all-environments default

- [ ] **Step 1: Update Service form helper test**

In `serviceForm.test.ts`, assert:

```ts
expect(serviceFormInitialValues).toEqual({
  max_input_tokens: 256,
});
expect(toServiceCreateRequest({
  service_id: ' svc ',
  display_name: ' Service ',
  max_input_tokens: 512,
})).toEqual({
  service_id: 'svc',
  display_name: 'Service',
  max_input_tokens: 512,
});
```

- [ ] **Step 2: Update Service form types**

In `serviceForm.ts`, replace:

```ts
export type ServiceFormValues = {
  service_id: string;
  display_name: string;
  max_input_tokens: number | null;
};

export const serviceFormInitialValues: Pick<ServiceFormValues, 'max_input_tokens'> = {
  max_input_tokens: 256,
};

export const toServiceCreateRequest = (
  values: ServiceFormValues,
): API.ServiceCreateRequest => ({
  service_id: values.service_id.trim(),
  display_name: values.display_name.trim(),
  max_input_tokens: Number(
    values.max_input_tokens ?? serviceFormInitialValues.max_input_tokens,
  ),
});
```

- [ ] **Step 3: Remove Service environment/preset form controls**

In `Services/index.tsx`, remove `environmentOptions`, `presetOptions`, and `Form.Item` blocks for `environment` and `default_threshold_preset`. Remove Service table/card environment fields that depend on `service.environment`; keep status if still returned by the API.

In `ServiceScopeBar.tsx`, remove the selected Service environment tag. If an environment indicator is needed later, it must come from the current page's release/API-key/log filter state, not from `AccessibleService`.

- [ ] **Step 4: Releases page contract**

In `releasesPageContract.test.ts`, assert:

```ts
expect(source).toContain("value: 'dev'");
expect(source).toContain("value: 'qa'");
expect(source).toContain("value: 'prod'");
expect(source).toContain('canManageReleases(session)');
expect(source).not.toContain('selectedService?.environment');
expect(source).not.toContain('Release environment는 서비스 environment와 반드시 같아야 합니다.');
```

- [ ] **Step 5: API Keys page contract**

In `runtimeSetup.test.ts`, assert:

```ts
expect(source).toContain('Released environment');
expect(source).toContain("value: 'qa'");
expect(source).toContain('canManageRuntimeSetup(session)');
expect(source).not.toContain('selectedService?.environment');
expect(source).not.toContain('service_owner/service_developer');
```

- [ ] **Step 6: Runtime Logs page contract**

In the Runtime Logs page and table contract tests, assert:

```ts
expect(source).toContain("value: 'dev'");
expect(source).toContain("value: 'qa'");
expect(source).toContain("value: 'prod'");
expect(source).toContain('environment');
expect(source).toContain('환경 미상');
```

- [ ] **Step 7: Run frontend tests**

Run:

```bash
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/pages/Services/serviceForm.test.ts src/pages/Services/servicesPagePresentation.test.ts src/pages/Releases/releasesPageContract.test.ts src/pages/ApiKeys/runtimeSetup.test.ts src/components/runtimeLogsTableContract.test.ts
cd frontend/intent-routing-console && ./node_modules/.bin/tsc --noEmit
```

Expected: PASS.

---

## Task 10: Documentation And Operator Runbooks

**Files:**
- Modify: `.env.example`
- Modify: `.env.closed-network.example`
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/run_local_dev_stack.sh`
- Modify: `scripts/run_local_dev_stack_macos.sh`
- Modify: `scripts/seed_pilot.py`
- Modify: `docs/api/admin-runtime-setup-contracts.md`
- Modify: `docs/api/openapi-runtime-examples.md`
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- Modify: `docs/AdminUI_Handbook/v04/E2E_DX_QA_CHECKLIST.md`
- Modify: `README.md`
- Modify: `docs/ops/intent-routing-local-runbook.md`
- Modify: `docs/ops/intent-routing-pilot-runbook.md`
- Modify: `docs/ops/pilot-e2e-smoke.md`
- Modify: `docs/ops/ci-verification.md`
- Modify: `docs/ops/closed-network-deployment.md`
- Test: `tests/unit/test_admin_runtime_setup_contract_docs.py`
- Test: `tests/unit/test_admin_ui_handbook_docs_contract.py`
- Test: `tests/unit/test_operator_docs_contract.py`
- Test: `tests/unit/test_env_contract.py`
- Test: `tests/unit/test_ci_workflow_contract.py`
- Test: `tests/unit/test_closed_network_packaging_contract.py`
- Test: `tests/unit/test_seed_pilot.py`

**Interfaces:**
- Produces: docs describe release-owned environment and key-owned runtime resolution
- Produces: docs stop telling operators to use Service environment as runtime source of truth

- [ ] **Step 1: Update runtime setup contract**

In `docs/api/admin-runtime-setup-contracts.md`, update the core rule text to:

```markdown
Runtime environment is resolved from the verified API key metadata. The client
must not send an environment header. Admin API key creation chooses one of
`dev`, `qa`, or `prod` after an active release exists for the selected Service
and environment.
```

Update error table rows:

```markdown
| Invalid `environment` | 422 | Must be one of `dev`, `qa`, or `prod` |
| Runtime key environment outside backend allowlist | 401 | Existing runtime auth contract |
```

- [ ] **Step 2: Update Admin UI pattern kit role matrix**

In `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`, replace Current Role Gates with:

```markdown
- `system_admin`: all permissions, Service creation, initial service_owner grants, system monitoring.
- `service_owner`: assigned-Service membership, Intent Catalog, Test Runs, Releases, API Keys, Runtime Logs.
- `service_developer`: assigned-Service Intent Catalog and Test Runs writes, Releases read, Runtime Logs read.
- `service_operator` and `auditor`: retained governed/security roles until a later decision changes or removes them.
```

Explicitly state that Organization Directory and Permission Management are system-admin-only, and Audit Logs are not shown to service_owner or service_developer.

- [ ] **Step 3: Update env examples, CI, scripts, and runbooks**

Replace examples that say:

```bash
export INTENT_ROUTING_ENVIRONMENT=dev
```

with:

```bash
export ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod
```

Expose `ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod` in `.env.example` and update `EXPECTED_LOCAL_ENV` in `tests/unit/test_env_contract.py`. Keep any legacy `INTENT_ROUTING_ENVIRONMENT` mention only when explaining that runtime routing no longer uses it as the active release selector.

For closed-network and pilot docs/scripts, replace `pilot` as a runtime environment value with one of `dev`, `qa`, or `prod`. Recommended first migration is:

- Local/CI pilot evidence uses `dev`.
- QA rehearsal examples use `qa`.
- Production-like closed-network examples use `prod` only when the text truly describes production runtime behavior.

The word `pilot` may remain in Service IDs, filenames, evidence paths, and scenario descriptions. It must not be passed as `--environment pilot` to release/API key creation after this change.

Update `scripts/seed_pilot.py` and its tests so Service creation omits environment/preset and the script's environment argument applies to release/API key creation only. Update local stack scripts so `ALLOWED_RUNTIME_ENVIRONMENTS` is exported to the backend process and seed scripts pass an allowed release environment.

- [ ] **Step 4: Run docs tests**

Run:

```bash
uv run pytest tests/unit/test_admin_runtime_setup_contract_docs.py tests/unit/test_admin_ui_handbook_docs_contract.py tests/unit/test_operator_docs_contract.py -q
uv run pytest tests/unit/test_env_contract.py tests/unit/test_ci_workflow_contract.py tests/unit/test_closed_network_packaging_contract.py tests/unit/test_seed_pilot.py -q
```

Expected: PASS.

---

## Task 11: End-To-End Verification

**Files:**
- No production file edits in this task.
- Use existing scripts and Admin UI.

**Interfaces:**
- Consumes: all previous tasks.
- Produces: evidence that one backend can serve `dev`, `qa`, and `prod` based on API key metadata.
- Produces: evidence that unsupported runtime environments cannot be created through Admin API or served through runtime auth.

- [ ] **Step 1: Backend verification**

Run:

```bash
uv run pytest tests/unit/test_env_contract.py tests/unit/test_ci_workflow_contract.py tests/unit/test_closed_network_packaging_contract.py tests/unit/test_seed_pilot.py tests/integration/test_release_flow.py tests/integration/test_runtime_api.py tests/integration/test_admin_runtime_setup_api.py tests/integration/test_admin_service_rbac_flow.py tests/integration/test_trace_audit_logs.py -q
uv run pytest -q
```

Expected: targeted tests PASS and full backend suite has no new failures compared with the pre-change baseline.

- [ ] **Step 2: Frontend verification**

Run:

```bash
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run src/models/adminSession.test.ts src/components/adminShellNavigation.test.ts src/pages/Services/serviceForm.test.ts src/pages/Services/membershipPanelContract.test.ts src/pages/Releases/releasesPageContract.test.ts src/pages/ApiKeys/runtimeSetup.test.ts src/components/runtimeLogsTableContract.test.ts
cd frontend/intent-routing-console && ./node_modules/.bin/vitest run
```

Expected: targeted tests PASS and full frontend test suite has no new failures.

- [ ] **Step 3: Type checks**

Run:

```bash
uv run mypy src
cd frontend/intent-routing-console && ./node_modules/.bin/tsc --noEmit
```

Expected: PASS.

- [ ] **Step 4: Local runtime smoke**

Start backend with:

```bash
ALLOWED_RUNTIME_ENVIRONMENTS=dev,qa,prod ./scripts/run_local_dev_stack_macos.sh
```

In Admin UI:

1. Create a Service without environment or default preset.
2. Grant `service_owner` on that Service.
3. Create intents and a catalog version.
4. Run a passing test run.
5. Create releases for `dev`, `qa`, and `prod` from the same test run.
6. Activate the `dev`, `qa`, and `prod` releases. Release creation alone is not enough because newly created releases start inactive.
7. Create API keys for at least `dev` and `qa`.
8. Call `/v1/intent-route` against the same backend process with both keys.
9. Confirm each response `release_version` matches the active release for that key's environment.
10. Confirm Runtime Logs show `environment=dev` and `environment=qa`, and that unfiltered logs also show any `환경 미상` preflight failures.

Then start a backend with a narrower allowlist:

```bash
ALLOWED_RUNTIME_ENVIRONMENTS=dev ./scripts/run_local_dev_stack_macos.sh
```

Call with a valid `qa` or `prod` key and confirm runtime returns `401` with `AUTHENTICATION_FAILED`.

- [ ] **Step 5: Guardrail search**

Run:

```bash
rg -n "service\\.environment|default_threshold_preset|INTENT_ROUTING_ENVIRONMENT|Release environment must match service environment|service_owner/service_developer" src tests frontend/intent-routing-console/src docs
```

Expected: remaining matches are either historical ADR/review references, migration downgrade defaults, compatibility notes saying the old model has been replaced, or non-routing legacy configuration text that is explicitly documented as no longer selecting active releases.

---

## Self-Review

External review incorporation:

- Accepted: F-1, F-2, F-3, F-6, F-7, F-8, F-9, F-10, F-15, F-16, F-17, M-1, M-2, M-4, M-5, T-1, T-2, T-3, T-4, and T-5. The plan now expands Service fixture cleanup, removes `service.environment` fallbacks, adds `ServiceScopeBar`, validates allowlist configuration, closes global API key environment bypass, handles preflight `NULL` log environments, covers governed publish activation, adds release activation to smoke verification, and adds broader full-suite checks.
- Partially accepted: F-4, F-5, F-11, F-12, F-13, F-18, F-19, S-1, and S-2. `pilot` is rejected as a runtime environment value but retained as a scenario/service naming term. Audit Logs are removed for `service_owner` and `service_developer`, while existing `service_operator`/`auditor` behavior is retained pending a separate decision. Release candidate existing-release maps should stay minimal if repository filtering already scopes by environment. Existing release review helpers should be reused when role semantics match. Metrics must either become environment-aware or be explicitly documented as aggregated.
- Accepted as verification/no-op: F-14. The plan now tells implementers to verify that no global one-release-per-test-run validation exists instead of requiring a nonexistent code change.
- Deferred: removing or redesigning `service_operator`/`auditor` roles, adding new runtime environments beyond `dev`/`qa`/`prod`, and adding a global ServiceScopeBar environment indicator. These require explicit product decisions outside the accepted matrix.

Spec coverage:

- Decisions `1-A`, `2-A`, `3-A`, `4-A`, `5-B`, `6-A`, `8-B`, `9-A`, and destructive re-registration are covered by Tasks 1 through 11.
- `7 기타` is covered by owner-only release/API-key writes without separate approval.
- The accepted role matrix is covered by Tasks 6, 7, 8, and 10.

Placeholder scan:

- This plan intentionally avoids placeholder tasks. Every task names exact files, target interfaces, representative test code, implementation snippets, and verification commands.

Type consistency:

- Environment literals are consistently `dev`, `qa`, and `prod`.
- `service_owner` is the release/API-key writer.
- `service_developer` is catalog/test writer and release/runtime-log reader.
- API keys remain environment-scoped and active-release-following, not release-version-bound.
