# Admin UI Workflow Candidate Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build backend candidate/list contracts and workflow-oriented Admin UI screens so an operator can move from Intent/Example work to Test Run, Release, and API Key creation without manually copying internal IDs.

**Architecture:** Add service-scoped read endpoints for policy versions, catalog versions, test runs, release candidates, intent/route candidates, and API key inventory. The Admin UI uses these endpoints through Umi `request`, searchable selectors, compact workflow panels, and next-action handoffs while keeping Phase 2 governed approval workflows informational until their backend contracts ship.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic, pytest, Umi Max 4, React 18, Ant Design 5, ProComponents, Vitest.

---

## Design Agent Input

The dedicated design agent returned this rule: users should select from current Service-scoped candidates, not type `pol-*`, `cat-*`, `tr-*`, `rel-*`, `intent_id`, or `route_key` unless creating the source object.

Design recommendations incorporated in this plan:

- Keep `AdminShell`, `ServiceScopeBar`, `ProTable`, `ConfirmActionButton`, `FutureFeatureNotice`, and `FieldHelpLabel`.
- Add `VersionChip`, `WorkflowNextActionBar`, `ValidationBundlePanel`, `ReleaseCandidateSelect`, and `IntentRouteMultiSelect`.
- Intent Catalog remains the source for creating/editing intents and examples.
- Test Runs prepares a validation bundle from selected policy/catalog versions and CSV cases.
- Releases creates from a release candidate instead of manual version fields.
- API Keys scopes allowed intents/routes by selecting known Service values, never by free-form textarea.
- Phase 2 governed flows stay disabled or informational: publish approval, example reject reason, raw query two-person approval, time-limited raw query token, release diff approval, CSV export, server pagination, compound filters, and live polling.

## Current State And Gaps

Existing backend endpoints:

- `GET /admin/v1/services/{service_id}/intents`
- `GET /admin/v1/services/{service_id}/intents/{intent_id}/examples`
- `POST /admin/v1/services/{service_id}/policy-versions`
- `POST /admin/v1/services/{service_id}/catalog-versions`
- `POST /admin/v1/services/{service_id}/test-runs`
- `GET /admin/v1/services/{service_id}/test-runs/{test_run_id}`
- `GET /admin/v1/services/{service_id}/test-runs/{test_run_id}/results`
- `GET /admin/v1/services/{service_id}/releases`
- `POST /admin/v1/api-keys`
- `POST /admin/v1/api-keys/{key_id}:revoke`

Missing contracts for option C:

- List policy versions for a Service.
- List catalog versions for a Service.
- List test runs for a Service.
- List release candidates that can be used to create a Release.
- List intent/route candidates for API key scope selection.
- List API key inventory without exposing secrets.
- Extend test run summary/list responses with `policy_version`, `intent_catalog_version`, `source_filename`, and `created_at`.

No database migration is expected because existing tables already store the required fields.

## File Structure

Documentation and ADR:

- Create: `docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md`
- Create: `docs/api/admin-workflow-candidate-contracts.md`
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- Test: `tests/unit/test_admin_workflow_candidate_contract_docs.py`

Backend:

- Modify: `src/intent_routing/db/repositories.py`
- Modify: `src/intent_routing/api/admin.py`
- Test: `tests/integration/test_admin_workflow_candidates_api.py`
- Test: `tests/integration/test_admin_api_key_inventory_flow.py`

Frontend services and types:

- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`

Frontend workflow components:

- Create: `frontend/intent-routing-console/src/components/VersionChip.tsx`
- Create: `frontend/intent-routing-console/src/components/WorkflowNextActionBar.tsx`
- Create: `frontend/intent-routing-console/src/components/IntentRouteMultiSelect.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/ValidationBundlePanel.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.ts`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.test.ts`
- Create: `frontend/intent-routing-console/src/pages/Releases/ReleaseCandidateSelect.tsx`

Frontend pages:

- Modify: `frontend/intent-routing-console/src/pages/Intents/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Releases/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`

## Workflow Map

1. ServiceScopeBar selects the current Service from `/me/services`.
2. Intent Catalog creates or edits Intent source objects.
3. Intent detail creates and approves positive/negative examples.
4. Test Runs prepares a validation bundle:
   - policy version from a preset,
   - catalog version from approved examples,
   - CSV cases from builder or pasted CSV.
5. Passing test run becomes a release candidate.
6. Releases creates a release from the selected candidate and optionally selects rollback target from existing releases.
7. API Keys create keys from active Service/release intent and route candidates.

Manual internal ID entry remains only for source creation:

- `intent_id` in Intent creation.
- `app_id` in API Key creation.
- CSV `case_id` because it identifies user-authored test cases.

---

### Task 1: Add ADR And API Contract Docs

**Files:**
- Create: `docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md`
- Create: `docs/api/admin-workflow-candidate-contracts.md`
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- Test: `tests/unit/test_admin_workflow_candidate_contract_docs.py`

- [ ] **Step 1: Write failing docs contract test**

Create `tests/unit/test_admin_workflow_candidate_contract_docs.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_workflow_candidate_contract_docs_exist_and_name_required_endpoints() -> None:
    adr = ROOT / "docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md"
    contract = ROOT / "docs/api/admin-workflow-candidate-contracts.md"
    pattern = ROOT / "docs/AdminUI_Handbook/v04/PATTERN_KIT.md"

    assert adr.exists()
    assert contract.exists()

    adr_text = adr.read_text(encoding="utf-8")
    contract_text = contract.read_text(encoding="utf-8")
    pattern_text = pattern.read_text(encoding="utf-8")

    for phrase in [
        "Status",
        "Decision",
        "Alternatives Considered",
        "Consequences",
        "service-scoped candidate endpoints",
    ]:
        assert phrase in adr_text

    for endpoint in [
        "GET /admin/v1/services/{service_id}/policy-versions",
        "GET /admin/v1/services/{service_id}/catalog-versions",
        "GET /admin/v1/services/{service_id}/test-runs",
        "GET /admin/v1/services/{service_id}/release-candidates",
        "GET /admin/v1/services/{service_id}/intent-route-candidates",
        "GET /admin/v1/api-keys",
    ]:
        assert endpoint in contract_text

    for phrase in [
        "Workflow candidate selectors",
        "Manual internal ID entry is transitional",
        "Phase 2 governed workflows remain disabled",
    ]:
        assert phrase in pattern_text
```

- [ ] **Step 2: Run docs contract test and confirm it fails**

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_workflow_candidate_contract_docs.py -q
```

Expected:

```text
FAILED tests/unit/test_admin_workflow_candidate_contract_docs.py::test_workflow_candidate_contract_docs_exist_and_name_required_endpoints
```

- [ ] **Step 3: Create ADR**

Create `docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md`:

```markdown
# ADR: Admin UI Workflow Candidate Contracts

## Status

Accepted

## Context

The Admin UI Phase 1 write screens expose internal identifiers such as policy versions, catalog versions, test run ids, release versions, intent ids, and route keys. Operators can complete the workflow only if they copy values between pages. The product direction in `docs/IntentRouting_PRD_ContextReview_20260624.md` favors templates, presets, examples, and guided operations instead of exposing low-level routing terms as routine inputs.

The current backend can create policy versions, catalog versions, test runs, releases, and API keys, but it does not expose all reloadable candidate lists needed by the UI.

## Decision

Model Admin UI workflow handoffs as service-scoped candidate endpoints. The UI will load policy versions, catalog versions, test runs, release candidates, intent/route candidates, and API key inventory from the server. Operators will select candidates instead of typing internal IDs, except when creating source objects such as a new Intent ID, API key App ID, or CSV case ID.

Phase 2 governed workflows remain disabled or informational until their explicit approval contracts are implemented.

## Alternatives Considered

### Option 1: Keep manual IDs with more help text

* Pros: Smallest implementation.
* Cons: Operators still need to copy internal IDs and understand backend constraints.

### Option 2: UI-only local handoff

* Pros: Fast improvement for values created during the current browser session.
* Cons: Breaks after refresh and cannot load historical candidates.

### Option 3: Service-scoped candidate endpoints

* Pros: Reloadable, auditable, role-scoped, and matches operator workflow.
* Cons: Requires backend contracts, integration tests, and UI refactoring.

## Consequences

Operators can complete the happy path without copying internal IDs. Backend APIs become the source of truth for candidate validity. The UI must not fake history, pagination, or release eligibility. API key inventory must never return raw key secrets.

## Implementation Notes

Add read endpoints under `/admin/v1` for policy versions, catalog versions, test runs, release candidates, intent/route candidates, and API key inventory. Keep normal Admin UI authentication on the `irt_admin_session` cookie. Preserve existing Phase 1 create endpoints.

## Verification

Verify with docs contract tests, backend integration tests, frontend service tests, TypeScript, unit tests, and manual browser QA for Intent Catalog to API Key workflow.

## Rollback or Revisit Conditions

Revisit this decision if the candidate endpoints expose sensitive data, cannot be authorized cleanly by Service scope, or become too broad and need a generalized workflow engine.
```

- [ ] **Step 4: Create API contract document**

Create `docs/api/admin-workflow-candidate-contracts.md`:

```markdown
# Admin Workflow Candidate Contracts

These endpoints support Admin UI workflow selectors. They return Service-scoped, reloadable candidates so users do not manually type internal ids.

## Common Rules

- Base path: `/admin/v1`.
- Authentication: `irt_admin_session` HttpOnly cookie.
- Authorization: server-derived admin context and selected Service roles.
- API key inventory must never return raw key secrets.
- Responses are ordered newest first unless specified otherwise.

## GET /admin/v1/services/{service_id}/policy-versions

Query:

- `limit`: integer, 1 to 100, default 50.

Response: `PolicyVersionResponse[]`.

Authorization: catalog access for the Service.

## GET /admin/v1/services/{service_id}/catalog-versions

Query:

- `limit`: integer, 1 to 100, default 50.

Response: `CatalogVersionListItemResponse[]`.

Each item includes:

- `intent_catalog_version`
- `service_id`
- `intent_count`
- `approved_example_count`
- `created_by`
- `created_at`

Authorization: catalog access for the Service.

## GET /admin/v1/services/{service_id}/test-runs

Query:

- `gate_passed`: optional boolean.
- `risk_passed`: optional boolean. `true` means `risk_pass_rate == 1.0`.
- `limit`: integer, 1 to 100, default 50.

Response: `TestRunListItemResponse[]`.

Each item includes:

- `test_run_id`
- `service_id`
- `test_dataset_version`
- `source_filename`
- `policy_version`
- `intent_catalog_version`
- `threshold_preset`
- `threshold_value`
- `pass_rate`
- `review_rate`
- `risk_pass_rate`
- `gate_passed`
- `block_reasons`
- `recommendations`
- `created_by`
- `created_at`

Authorization: catalog access for the Service.

## GET /admin/v1/services/{service_id}/release-candidates

Query:

- `environment`: optional string. Defaults to the Service environment.
- `limit`: integer, 1 to 100, default 50.

Response: `ReleaseCandidateResponse[]`.

Each item includes:

- `test_run_id`
- `service_id`
- `environment`
- `policy_version`
- `intent_catalog_version`
- `test_dataset_version`
- `source_filename`
- `threshold_preset`
- `pass_rate`
- `risk_pass_rate`
- `gate_passed`
- `eligible`
- `block_reasons`
- `already_released`
- `existing_release_version`
- `created_at`

Authorization: catalog access for reading; release creation remains `system_admin`.

## GET /admin/v1/services/{service_id}/intent-route-candidates

Query:

- `source`: `current_catalog` or `active_release`, default `current_catalog`.
- `environment`: optional string for active release lookup.

Response: `IntentRouteCandidateResponse[]`.

Each item includes:

- `intent_id`
- `display_name`
- `route_key`
- `status`
- `source`

Authorization: catalog access for current catalog; release access for active release snapshot.

## GET /admin/v1/api-keys

Query:

- `service_id`: optional string.
- `environment`: optional string.
- `status`: optional string.
- `limit`: integer, 1 to 100, default 50.

Response: `ApiKeyResponse[]`.

Authorization: `system_admin`.

Security rule: response excludes `api_key` secret.
```

- [ ] **Step 5: Update v04 pattern kit**

Modify `docs/AdminUI_Handbook/v04/PATTERN_KIT.md` by adding this section after `## Phase Model`:

```markdown
## Workflow candidate selectors

Admin UI write screens must prefer service-scoped selectors over manual internal ID entry.

- Intent IDs are manually entered only when creating an Intent.
- Policy versions, catalog versions, test runs, release candidates, rollback targets, allowed intents, and allowed route keys must be loaded from Admin API candidate/list endpoints.
- Manual internal ID entry is transitional and should be removed once candidate endpoints exist.
- Phase 2 governed workflows remain disabled until their backend approval contracts pass.
```

- [ ] **Step 6: Verify docs contract**

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_workflow_candidate_contract_docs.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Commit docs contract**

```bash
cd /home/haua/workspace/AiIntentRouting
git add docs/adr/2026-07-06-admin-ui-workflow-candidate-contracts.md docs/api/admin-workflow-candidate-contracts.md docs/AdminUI_Handbook/v04/PATTERN_KIT.md tests/unit/test_admin_workflow_candidate_contract_docs.py
git commit -m "docs: define admin workflow candidate contracts"
```

---

### Task 2: Add Backend Repository List Methods

**Files:**
- Modify: `src/intent_routing/db/repositories.py`
- Test: `tests/integration/test_admin_workflow_candidates_api.py`

- [ ] **Step 1: Write failing repository-backed API tests**

Create `tests/integration/test_admin_workflow_candidates_api.py` with the first failing tests:

```python
from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import get_admin_session
from intent_routing.main import create_app


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    return TestClient(app, raise_server_exceptions=False)


def _logged_in_system_admin_client(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    service_id: str,
) -> TestClient:
    client = _client(db_session)
    email = f"workflow-{uuid4().hex}@example.com"
    password = "correct horse battery staple"
    bootstrap_token = f"bootstrap-{uuid4().hex}"
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", bootstrap_token)

    bootstrap = client.post(
        "/admin/v1/auth/bootstrap-admin",
        headers={"X-Admin-Token": bootstrap_token},
        json={
            "user_id": f"user-{uuid4().hex}",
            "email": email,
            "display_name": "Workflow Admin",
            "password": password,
        },
    )
    assert bootstrap.status_code == 201

    login = client.post("/admin/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    service = client.post(
        "/admin/v1/services",
        json={
            "service_id": service_id,
            "display_name": "Workflow Candidate Service",
            "environment": "dev",
            "default_threshold_preset": "balanced",
            "max_input_tokens": 256,
        },
    )
    assert service.status_code == 201
    return client


def test_lists_policy_and_catalog_versions(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id = f"svc-workflow-{uuid4().hex}"
    client = _logged_in_system_admin_client(db_session, monkeypatch, service_id)

    policy = client.post(
        f"/admin/v1/services/{service_id}/policy-versions",
        json={
            "threshold_preset": "balanced",
            "clarify_margin": 0.08,
            "min_candidate_score": 0.55,
            "fallback_score": 0.45,
            "risk_policy": {"enabled": True},
            "off_topic_policy": {"enabled": True, "keywords": [], "message": ""},
        },
    )
    assert policy.status_code == 201

    catalog = client.post(f"/admin/v1/services/{service_id}/catalog-versions")
    assert catalog.status_code == 201

    policies = client.get(f"/admin/v1/services/{service_id}/policy-versions")
    catalogs = client.get(f"/admin/v1/services/{service_id}/catalog-versions")

    assert policies.status_code == 200
    assert catalogs.status_code == 200
    assert policies.json()[0]["policy_version"] == policy.json()["policy_version"]
    assert catalogs.json()[0]["intent_catalog_version"] == catalog.json()["intent_catalog_version"]
    assert "intent_count" in catalogs.json()[0]
    assert "approved_example_count" in catalogs.json()[0]
```

- [ ] **Step 2: Run new test and confirm it fails**

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_workflow_candidates_api.py::test_lists_policy_and_catalog_versions -q
```

Expected:

```text
404 Not Found
```

- [ ] **Step 3: Add repository methods**

Modify `src/intent_routing/db/repositories.py`:

```python
    def list_policy_versions(
        self,
        service_id: str,
        *,
        limit: int = 50,
    ) -> list[models.PolicyVersion]:
        return list(
            self.session.scalars(
                select(models.PolicyVersion)
                .where(models.PolicyVersion.service_id == service_id)
                .order_by(
                    models.PolicyVersion.created_at.desc(),
                    models.PolicyVersion.policy_version,
                )
                .limit(limit)
            )
        )

    def list_catalog_versions(
        self,
        service_id: str,
        *,
        limit: int = 50,
    ) -> list[models.IntentCatalogVersion]:
        return list(
            self.session.scalars(
                select(models.IntentCatalogVersion)
                .where(models.IntentCatalogVersion.service_id == service_id)
                .order_by(
                    models.IntentCatalogVersion.created_at.desc(),
                    models.IntentCatalogVersion.intent_catalog_version,
                )
                .limit(limit)
            )
        )

    def list_test_runs(
        self,
        service_id: str,
        *,
        gate_passed: bool | None = None,
        risk_passed: bool | None = None,
        limit: int = 50,
    ) -> list[tuple[models.TestRun, models.TestDataset]]:
        statement = (
            select(models.TestRun, models.TestDataset)
            .join(
                models.TestDataset,
                models.TestDataset.test_dataset_version
                == models.TestRun.test_dataset_version,
            )
            .where(models.TestRun.service_id == service_id)
        )
        if gate_passed is not None:
            statement = statement.where(models.TestRun.gate_passed.is_(gate_passed))
        if risk_passed is True:
            statement = statement.where(models.TestRun.risk_pass_rate == 1)
        if risk_passed is False:
            statement = statement.where(models.TestRun.risk_pass_rate != 1)
        return list(
            self.session.execute(
                statement.order_by(
                    models.TestRun.created_at.desc(),
                    models.TestRun.test_run_id,
                ).limit(limit)
            ).all()
        )

    def list_api_keys(
        self,
        *,
        service_id: str | None = None,
        environment: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[models.ApiKey]:
        statement = select(models.ApiKey)
        if service_id is not None:
            statement = statement.where(models.ApiKey.service_id == service_id)
        if environment is not None:
            statement = statement.where(models.ApiKey.environment == environment)
        if status is not None:
            statement = statement.where(models.ApiKey.status == status)
        return list(
            self.session.scalars(
                statement.order_by(
                    models.ApiKey.created_at.desc(),
                    models.ApiKey.key_id,
                ).limit(limit)
            )
        )
```

- [ ] **Step 4: Run narrow test**

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_workflow_candidates_api.py::test_lists_policy_and_catalog_versions -q
```

Expected:

```text
FAILED ... 404 Not Found
```

The repository methods exist, but the API routes are still missing.

---

### Task 3: Add Backend Candidate/List API Endpoints

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Modify: `src/intent_routing/db/repositories.py`
- Test: `tests/integration/test_admin_workflow_candidates_api.py`
- Test: `tests/integration/test_admin_api_key_inventory_flow.py`

- [ ] **Step 1: Extend API response models**

Modify `src/intent_routing/api/admin.py` near existing response classes:

```python
class CatalogVersionListItemResponse(BaseModel):
    intent_catalog_version: str
    service_id: str
    intent_count: int
    approved_example_count: int
    created_by: str
    created_at: datetime


class TestRunListItemResponse(BaseModel):
    test_run_id: str
    service_id: str
    test_dataset_version: str
    source_filename: str
    policy_version: str
    intent_catalog_version: str
    threshold_preset: str
    threshold_value: float
    pass_rate: float
    review_rate: float
    risk_pass_rate: float
    gate_passed: bool
    block_reasons: list[str]
    recommendations: list[str]
    created_by: str
    created_at: datetime


class ReleaseCandidateResponse(BaseModel):
    test_run_id: str
    service_id: str
    environment: str
    policy_version: str
    intent_catalog_version: str
    test_dataset_version: str
    source_filename: str
    threshold_preset: str
    pass_rate: float
    risk_pass_rate: float
    gate_passed: bool
    eligible: bool
    block_reasons: list[str]
    already_released: bool
    existing_release_version: str | None
    created_at: datetime


class IntentRouteCandidateResponse(BaseModel):
    intent_id: str
    display_name: str
    route_key: str
    status: str
    source: str
```

- [ ] **Step 2: Add response helpers**

Modify `src/intent_routing/api/admin.py` near existing helper functions:

```python
def _catalog_version_list_item_response(
    catalog_version: IntentCatalogVersion,
) -> CatalogVersionListItemResponse:
    snapshot = catalog_version.snapshot or {}
    intents = snapshot.get("intents", [])
    examples = snapshot.get("examples", [])
    return CatalogVersionListItemResponse(
        intent_catalog_version=catalog_version.intent_catalog_version,
        service_id=catalog_version.service_id,
        intent_count=len(intents) if isinstance(intents, list) else 0,
        approved_example_count=len(examples) if isinstance(examples, list) else 0,
        created_by=catalog_version.created_by,
        created_at=catalog_version.created_at,
    )


def _test_run_list_item_response(
    test_run: TestRun,
    dataset: TestDataset,
    results: list[TestResult],
) -> TestRunListItemResponse:
    summary = summarize_test_run(test_run, results)
    return TestRunListItemResponse(
        test_run_id=test_run.test_run_id,
        service_id=test_run.service_id,
        test_dataset_version=test_run.test_dataset_version,
        source_filename=dataset.source_filename,
        policy_version=test_run.policy_version,
        intent_catalog_version=test_run.intent_catalog_version,
        threshold_preset=test_run.threshold_preset,
        threshold_value=float(test_run.threshold_value),
        pass_rate=float(test_run.pass_rate),
        review_rate=float(test_run.review_rate),
        risk_pass_rate=float(test_run.risk_pass_rate),
        gate_passed=test_run.gate_passed,
        block_reasons=summary.block_reasons,
        recommendations=summary.recommendations,
        created_by=test_run.created_by,
        created_at=test_run.created_at,
    )
```

- [ ] **Step 3: Add list endpoints**

Add these routes in `src/intent_routing/api/admin.py` near related current routes:

```python
@router.get(
    "/services/{service_id}/policy-versions",
    response_model=list[PolicyVersionResponse],
    response_model_exclude_none=True,
)
def list_policy_versions(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PolicyVersionResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return [
        _policy_version_response(policy_version)
        for policy_version in repository.list_policy_versions(service_id, limit=limit)
    ]


@router.get(
    "/services/{service_id}/catalog-versions",
    response_model=list[CatalogVersionListItemResponse],
)
def list_catalog_versions(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[CatalogVersionListItemResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    return [
        _catalog_version_list_item_response(catalog_version)
        for catalog_version in repository.list_catalog_versions(service_id, limit=limit)
    ]


@router.get(
    "/services/{service_id}/test-runs",
    response_model=list[TestRunListItemResponse],
)
def list_test_runs(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    gate_passed: bool | None = None,
    risk_passed: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[TestRunListItemResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    rows = repository.list_test_runs(
        service_id,
        gate_passed=gate_passed,
        risk_passed=risk_passed,
        limit=limit,
    )
    return [
        _test_run_list_item_response(test_run, dataset, repository.list_test_results(test_run.test_run_id))
        for test_run, dataset in rows
    ]
```

- [ ] **Step 4: Add release candidates endpoint**

Add to `src/intent_routing/api/admin.py`:

```python
@router.get(
    "/services/{service_id}/release-candidates",
    response_model=list[ReleaseCandidateResponse],
)
def list_release_candidates(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    environment: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ReleaseCandidateResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    target_environment = environment or service.environment
    existing_releases = {
        release.test_run_id: release
        for release in repository.list_releases(service_id, target_environment)
    }
    rows = repository.list_test_runs(
        service_id,
        gate_passed=None,
        risk_passed=None,
        limit=limit,
    )
    candidates: list[ReleaseCandidateResponse] = []
    for test_run, dataset in rows:
        results = repository.list_test_results(test_run.test_run_id)
        summary = summarize_test_run(test_run, results)
        existing_release = existing_releases.get(test_run.test_run_id)
        block_reasons = list(summary.block_reasons)
        if float(test_run.risk_pass_rate) != 1.0:
            block_reasons.append("risk pass rate must be 100%")
        if existing_release is not None:
            block_reasons.append("test run already has a release")
        eligible = test_run.gate_passed and float(test_run.risk_pass_rate) == 1.0 and existing_release is None
        candidates.append(
            ReleaseCandidateResponse(
                test_run_id=test_run.test_run_id,
                service_id=test_run.service_id,
                environment=target_environment,
                policy_version=test_run.policy_version,
                intent_catalog_version=test_run.intent_catalog_version,
                test_dataset_version=test_run.test_dataset_version,
                source_filename=dataset.source_filename,
                threshold_preset=test_run.threshold_preset,
                pass_rate=float(test_run.pass_rate),
                risk_pass_rate=float(test_run.risk_pass_rate),
                gate_passed=test_run.gate_passed,
                eligible=eligible,
                block_reasons=block_reasons,
                already_released=existing_release is not None,
                existing_release_version=(
                    existing_release.release_version if existing_release is not None else None
                ),
                created_at=test_run.created_at,
            )
        )
    return candidates
```

- [ ] **Step 5: Add intent/route candidates endpoint**

Add to `src/intent_routing/api/admin.py`:

```python
@router.get(
    "/services/{service_id}/intent-route-candidates",
    response_model=list[IntentRouteCandidateResponse],
)
def list_intent_route_candidates(
    service_id: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    source: str = "current_catalog",
    environment: str | None = None,
) -> list[IntentRouteCandidateResponse]:
    _require_service_catalog_access(context, service_id)
    repository = IntentRoutingRepository(session)
    service = repository.get_service(service_id)
    if service is None:
        _raise_not_found("Service does not exist.")
    if source == "current_catalog":
        return [
            IntentRouteCandidateResponse(
                intent_id=intent.intent_id,
                display_name=intent.display_name,
                route_key=intent.route_key,
                status=intent.status,
                source=source,
            )
            for intent in repository.list_intents(service_id)
            if intent.status == IntentStatus.active.value
        ]
    if source == "active_release":
        release = repository.get_active_release(service_id, environment or service.environment)
        if release is None:
            return []
        catalog_version = repository.get_catalog_version(
            service_id,
            release.intent_catalog_version,
        )
        if catalog_version is None:
            return []
        intents = catalog_version.snapshot.get("intents", [])
        if not isinstance(intents, list):
            return []
        return [
            IntentRouteCandidateResponse(
                intent_id=str(intent.get("intent_id")),
                display_name=str(intent.get("display_name")),
                route_key=str(intent.get("route_key")),
                status=str(intent.get("status")),
                source=source,
            )
            for intent in intents
            if intent.get("status") == IntentStatus.active.value
        ]
    _raise_bad_request("source must be current_catalog or active_release")
```

- [ ] **Step 6: Add API key inventory endpoint**

Create `tests/integration/test_admin_api_key_inventory_flow.py`:

```python
from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from intent_routing.api.admin_dependencies import get_admin_session
from intent_routing.main import create_app


def _client(db_session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_admin_session] = override_session
    return TestClient(app, raise_server_exceptions=False)


def _logged_in_system_admin_client(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    service_id: str,
) -> TestClient:
    client = _client(db_session)
    email = f"api-key-inventory-{uuid4().hex}@example.com"
    password = "correct horse battery staple"
    bootstrap_token = f"bootstrap-{uuid4().hex}"
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", bootstrap_token)

    bootstrap = client.post(
        "/admin/v1/auth/bootstrap-admin",
        headers={"X-Admin-Token": bootstrap_token},
        json={
            "user_id": f"user-{uuid4().hex}",
            "email": email,
            "display_name": "API Key Inventory Admin",
            "password": password,
        },
    )
    assert bootstrap.status_code == 201

    login = client.post("/admin/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    service = client.post(
        "/admin/v1/services",
        json={
            "service_id": service_id,
            "display_name": "API Key Inventory Service",
            "environment": "dev",
            "default_threshold_preset": "balanced",
            "max_input_tokens": 256,
        },
    )
    assert service.status_code == 201
    return client


def test_api_key_inventory_excludes_secret(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id = f"svc-api-key-{uuid4().hex}"
    client = _logged_in_system_admin_client(db_session, monkeypatch, service_id)

    created = client.post(
        "/admin/v1/api-keys",
        json={
            "service_id": service_id,
            "environment": "dev",
            "app_id": "helpdesk-bot",
            "allowed_intents": [],
            "allowed_route_keys": [],
            "expires_in_days": 90,
        },
    )
    assert created.status_code == 201
    assert "api_key" in created.json()

    inventory = client.get(f"/admin/v1/api-keys?service_id={service_id}")
    assert inventory.status_code == 200
    row = inventory.json()[0]
    assert row["key_id"] == created.json()["key_id"]
    assert row["key_fingerprint"] == created.json()["key_fingerprint"]
    assert "api_key" not in row
```

Add route to `src/intent_routing/api/admin.py`:

```python
@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    service_id: str | None = None,
    environment: str | None = None,
    status: ApiKeyStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ApiKeyResponse]:
    _require_system_admin(context)
    repository = IntentRoutingRepository(session)
    return [
        _api_key_response(api_key)
        for api_key in repository.list_api_keys(
            service_id=service_id,
            environment=environment,
            status=status.value if status is not None else None,
            limit=limit,
        )
    ]
```

- [ ] **Step 7: Complete backend tests**

Extend `tests/integration/test_admin_workflow_candidates_api.py` with:

```python
def test_release_candidates_include_only_service_scoped_test_runs(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id = f"svc-release-candidates-{uuid4().hex}"
    client = _logged_in_system_admin_client(db_session, monkeypatch, service_id)

    candidates = client.get(f"/admin/v1/services/{service_id}/release-candidates")

    assert candidates.status_code == 200
    assert isinstance(candidates.json(), list)


def test_intent_route_candidates_are_selectable_scope_values(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_id = f"svc-intent-route-{uuid4().hex}"
    client = _logged_in_system_admin_client(db_session, monkeypatch, service_id)

    response = client.get(f"/admin/v1/services/{service_id}/intent-route-candidates")

    assert response.status_code == 200
    for row in response.json():
        assert {"intent_id", "display_name", "route_key", "status", "source"} <= set(row)
```

- [ ] **Step 8: Verify backend candidate APIs**

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_workflow_candidates_api.py tests/integration/test_admin_api_key_inventory_flow.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 9: Commit backend contracts**

```bash
cd /home/haua/workspace/AiIntentRouting
git add src/intent_routing/api/admin.py src/intent_routing/db/repositories.py tests/integration/test_admin_workflow_candidates_api.py tests/integration/test_admin_api_key_inventory_flow.py
git commit -m "feat: add admin workflow candidate APIs"
```

---

### Task 4: Add Frontend API Types And Service Functions

**Files:**
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`

- [ ] **Step 1: Add failing frontend service tests**

Modify `frontend/intent-routing-console/src/services/adminServices.test.ts` with tests for new paths:

```ts
import {
  listApiKeys,
  listCatalogVersions,
  listIntentRouteCandidates,
  listPolicyVersions,
  listReleaseCandidates,
  listTestRuns,
} from './adminServices';

it('loads workflow candidate paths', async () => {
  await listPolicyVersions('svc');
  await listCatalogVersions('svc');
  await listTestRuns('svc', { gate_passed: true, risk_passed: true });
  await listReleaseCandidates('svc');
  await listIntentRouteCandidates('svc', { source: 'active_release' });
  await listApiKeys({ service_id: 'svc' });

  expect(request).toHaveBeenCalledWith('/services/svc/policy-versions', {
    method: 'GET',
    params: { limit: 50 },
  });
  expect(request).toHaveBeenCalledWith('/services/svc/catalog-versions', {
    method: 'GET',
    params: { limit: 50 },
  });
  expect(request).toHaveBeenCalledWith('/services/svc/test-runs', {
    method: 'GET',
    params: { gate_passed: true, risk_passed: true, limit: 50 },
  });
  expect(request).toHaveBeenCalledWith('/services/svc/release-candidates', {
    method: 'GET',
    params: { environment: undefined, limit: 50 },
  });
  expect(request).toHaveBeenCalledWith('/services/svc/intent-route-candidates', {
    method: 'GET',
    params: { source: 'active_release', environment: undefined },
  });
  expect(request).toHaveBeenCalledWith('/api-keys', {
    method: 'GET',
    params: { service_id: 'svc', environment: undefined, status: undefined, limit: 50 },
  });
});
```

- [ ] **Step 2: Run frontend service tests and confirm failure**

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm test:unit -- src/services/adminServices.test.ts
```

Expected:

```text
FAIL src/services/adminServices.test.ts
```

- [ ] **Step 3: Add API types**

Modify `frontend/intent-routing-console/src/types/api.d.ts`:

```ts
  type CatalogVersionListItem = {
    intent_catalog_version: string;
    service_id: string;
    intent_count: number;
    approved_example_count: number;
    created_by: string;
    created_at: string;
  };

  type TestRunListItem = TestRunSummary & {
    service_id: string;
    policy_version: string;
    intent_catalog_version: string;
    source_filename: string;
    created_by: string;
    created_at: string;
  };

  type ReleaseCandidate = {
    test_run_id: string;
    service_id: string;
    environment: string;
    policy_version: string;
    intent_catalog_version: string;
    test_dataset_version: string;
    source_filename: string;
    threshold_preset: string;
    pass_rate: number;
    risk_pass_rate: number;
    gate_passed: boolean;
    eligible: boolean;
    block_reasons: string[];
    already_released: boolean;
    existing_release_version: string | null;
    created_at: string;
  };

  type IntentRouteCandidate = {
    intent_id: string;
    display_name: string;
    route_key: string;
    status: IntentStatus;
    source: 'current_catalog' | 'active_release';
  };
```

- [ ] **Step 4: Add service functions**

Modify `frontend/intent-routing-console/src/services/adminServices.ts`:

```ts
export async function listPolicyVersions(serviceId: string, limit = 50) {
  return request<API.PolicyVersion[]>(servicePath(serviceId, '/policy-versions'), {
    method: 'GET',
    params: { limit },
  });
}

export async function listCatalogVersions(serviceId: string, limit = 50) {
  return request<API.CatalogVersionListItem[]>(servicePath(serviceId, '/catalog-versions'), {
    method: 'GET',
    params: { limit },
  });
}

export async function listTestRuns(
  serviceId: string,
  params: { gate_passed?: boolean; risk_passed?: boolean; limit?: number } = {},
) {
  return request<API.TestRunListItem[]>(servicePath(serviceId, '/test-runs'), {
    method: 'GET',
    params: {
      gate_passed: params.gate_passed,
      risk_passed: params.risk_passed,
      limit: params.limit ?? 50,
    },
  });
}

export async function listReleaseCandidates(
  serviceId: string,
  params: { environment?: string; limit?: number } = {},
) {
  return request<API.ReleaseCandidate[]>(servicePath(serviceId, '/release-candidates'), {
    method: 'GET',
    params: { environment: params.environment, limit: params.limit ?? 50 },
  });
}

export async function listIntentRouteCandidates(
  serviceId: string,
  params: { source?: 'current_catalog' | 'active_release'; environment?: string } = {},
) {
  return request<API.IntentRouteCandidate[]>(servicePath(serviceId, '/intent-route-candidates'), {
    method: 'GET',
    params: {
      source: params.source ?? 'current_catalog',
      environment: params.environment,
    },
  });
}

export async function listApiKeys(
  params: {
    service_id?: string;
    environment?: string;
    status?: API.ApiKeyStatus;
    limit?: number;
  } = {},
) {
  return request<API.ApiKey[]>('/api-keys', {
    method: 'GET',
    params: {
      service_id: params.service_id,
      environment: params.environment,
      status: params.status,
      limit: params.limit ?? 50,
    },
  });
}
```

- [ ] **Step 5: Verify frontend services**

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm test:unit -- src/services/adminServices.test.ts
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm typecheck
```

Expected:

```text
adminServices tests pass
tsc --noEmit exits 0
```

- [ ] **Step 6: Commit frontend service contracts**

```bash
cd /home/haua/workspace/AiIntentRouting
git add frontend/intent-routing-console/src/types/api.d.ts frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/services/adminServices.test.ts
git commit -m "feat: add admin workflow candidate services"
```

---

### Task 5: Add Workflow UI Building Blocks

**Files:**
- Create: `frontend/intent-routing-console/src/components/VersionChip.tsx`
- Create: `frontend/intent-routing-console/src/components/WorkflowNextActionBar.tsx`
- Create: `frontend/intent-routing-console/src/components/IntentRouteMultiSelect.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.ts`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.test.ts`

- [ ] **Step 1: Add CSV builder tests**

Create `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.test.ts`:

```ts
import { buildCsvText, type CsvCaseDraft } from './csvCaseBuilder';

it('builds backend-compatible CSV from case drafts', () => {
  const drafts: CsvCaseDraft[] = [
    {
      case_id: 'tc-001',
      query: 'password reset help',
      expected_intent: 'it_password_reset',
      case_type: 'positive',
      memo: 'happy path',
    },
    {
      case_id: 'tc-002',
      query: 'show me payroll',
      expected_intent: '',
      case_type: 'off_topic',
      memo: 'out of scope',
    },
  ];

  expect(buildCsvText(drafts)).toBe(
    [
      'case_id,query,expected_intent,case_type,memo',
      'tc-001,password reset help,it_password_reset,positive,happy path',
      'tc-002,show me payroll,,off_topic,out of scope',
    ].join('\\n'),
  );
});

it('quotes CSV cells containing commas', () => {
  expect(
    buildCsvText([
      {
        case_id: 'tc-003',
        query: 'reset password, please',
        expected_intent: 'it_password_reset',
        case_type: 'positive',
        memo: 'contains comma',
      },
    ]),
  ).toContain('"reset password, please"');
});
```

- [ ] **Step 2: Add CSV builder implementation**

Create `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.ts`:

```ts
export type CsvCaseDraft = {
  case_id: string;
  query: string;
  expected_intent: string;
  case_type: 'positive' | 'confusing' | 'clarify' | 'risk' | 'off_topic' | 'fallback';
  memo: string;
};

const columns: Array<keyof CsvCaseDraft> = [
  'case_id',
  'query',
  'expected_intent',
  'case_type',
  'memo',
];

const escapeCell = (value: string) => {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
};

export const buildCsvText = (drafts: CsvCaseDraft[]) =>
  [
    columns.join(','),
    ...drafts.map((draft) =>
      columns.map((column) => escapeCell(String(draft[column] ?? ''))).join(','),
    ),
  ].join('\n');
```

- [ ] **Step 3: Add VersionChip**

Create `frontend/intent-routing-console/src/components/VersionChip.tsx`:

```tsx
import { Tag, Typography } from 'antd';

type VersionChipProps = {
  label: string;
  value: string | null | undefined;
};

export function VersionChip({ label, value }: VersionChipProps) {
  return (
    <Tag>
      {label}{' '}
      {value ? (
        <Typography.Text copyable code>
          {value}
        </Typography.Text>
      ) : (
        'none'
      )}
    </Tag>
  );
}
```

- [ ] **Step 4: Add WorkflowNextActionBar**

Create `frontend/intent-routing-console/src/components/WorkflowNextActionBar.tsx`:

```tsx
import { Button, Space, Typography } from 'antd';
import type { ReactNode } from 'react';

type WorkflowNextActionBarProps = {
  title: string;
  description?: ReactNode;
  primaryLabel: string;
  onPrimary: () => void;
  disabled?: boolean;
};

export function WorkflowNextActionBar({
  title,
  description,
  primaryLabel,
  onPrimary,
  disabled,
}: WorkflowNextActionBarProps) {
  return (
    <Space className="workflow-next-action-bar" align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
      <Space direction="vertical" size={0}>
        <Typography.Text strong>{title}</Typography.Text>
        {description ? <Typography.Text type="secondary">{description}</Typography.Text> : null}
      </Space>
      <Button type="primary" onClick={onPrimary} disabled={disabled}>
        {primaryLabel}
      </Button>
    </Space>
  );
}
```

- [ ] **Step 5: Add IntentRouteMultiSelect**

Create `frontend/intent-routing-console/src/components/IntentRouteMultiSelect.tsx`:

```tsx
import { Select, Space, Typography } from 'antd';

type IntentRouteMultiSelectProps = {
  value?: string[];
  onChange?: (value: string[]) => void;
  candidates: API.IntentRouteCandidate[];
  mode: 'intent' | 'route';
  placeholder?: string;
};

export function IntentRouteMultiSelect({
  value,
  onChange,
  candidates,
  mode,
  placeholder,
}: IntentRouteMultiSelectProps) {
  return (
    <Select
      mode="multiple"
      allowClear
      showSearch
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      optionFilterProp="label"
      style={{ minWidth: 360 }}
      options={candidates.map((candidate) => ({
        value: mode === 'intent' ? candidate.intent_id : candidate.route_key,
        label: mode === 'intent' ? candidate.intent_id : candidate.route_key,
        children: (
          <Space direction="vertical" size={0}>
            <Typography.Text>
              {mode === 'intent' ? candidate.intent_id : candidate.route_key}
            </Typography.Text>
            <Typography.Text type="secondary">{candidate.display_name}</Typography.Text>
          </Space>
        ),
      }))}
    />
  );
}
```

- [ ] **Step 6: Verify building blocks**

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm test:unit -- src/pages/TestRuns/csvCaseBuilder.test.ts
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm typecheck
```

Expected:

```text
csvCaseBuilder tests pass
tsc --noEmit exits 0
```

- [ ] **Step 7: Commit workflow components**

```bash
cd /home/haua/workspace/AiIntentRouting
git add frontend/intent-routing-console/src/components/VersionChip.tsx frontend/intent-routing-console/src/components/WorkflowNextActionBar.tsx frontend/intent-routing-console/src/components/IntentRouteMultiSelect.tsx frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.ts frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.test.ts
git commit -m "feat: add admin workflow UI primitives"
```

---

### Task 6: Refactor Test Runs Into Validation Bundle Workflow

**Files:**
- Create: `frontend/intent-routing-console/src/pages/TestRuns/ValidationBundlePanel.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Intents/index.tsx`

- [ ] **Step 1: Add ValidationBundlePanel**

Create `frontend/intent-routing-console/src/pages/TestRuns/ValidationBundlePanel.tsx`:

```tsx
import { Button, Segmented, Space, Typography, message } from 'antd';
import { useState } from 'react';
import { VersionChip } from '@/components/VersionChip';
import {
  createCatalogVersion,
  createPolicyVersion,
  listCatalogVersions,
  listPolicyVersions,
} from '@/services/adminServices';

type ValidationBundle = {
  policy_version?: string;
  intent_catalog_version?: string;
  threshold_preset: API.ThresholdPreset;
};

type ValidationBundlePanelProps = {
  serviceId: string;
  value: ValidationBundle;
  onChange: (value: ValidationBundle) => void;
};

const defaultPolicyPayload = (preset: API.ThresholdPreset): API.PolicyVersionCreateRequest => ({
  threshold_preset: preset,
  clarify_margin: 0.08,
  min_candidate_score: 0.55,
  fallback_score: 0.45,
  risk_policy: { enabled: true },
  off_topic_policy: { enabled: true, keywords: [], message: '' },
});

export function ValidationBundlePanel({
  serviceId,
  value,
  onChange,
}: ValidationBundlePanelProps) {
  const [loadingPolicy, setLoadingPolicy] = useState(false);
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [loadingLatest, setLoadingLatest] = useState(false);

  const loadLatest = async () => {
    setLoadingLatest(true);
    try {
      const [policies, catalogs] = await Promise.all([
        listPolicyVersions(serviceId, 1),
        listCatalogVersions(serviceId, 1),
      ]);
      onChange({
        threshold_preset: (policies[0]?.threshold_preset as API.ThresholdPreset) || value.threshold_preset,
        policy_version: policies[0]?.policy_version,
        intent_catalog_version: catalogs[0]?.intent_catalog_version,
      });
      message.success('Latest validation bundle loaded.');
    } finally {
      setLoadingLatest(false);
    }
  };

  const createPolicy = async () => {
    setLoadingPolicy(true);
    try {
      const policy = await createPolicyVersion(serviceId, defaultPolicyPayload(value.threshold_preset));
      onChange({ ...value, policy_version: policy.policy_version });
      message.success('Policy version created.');
    } finally {
      setLoadingPolicy(false);
    }
  };

  const createCatalog = async () => {
    setLoadingCatalog(true);
    try {
      const catalog = await createCatalogVersion(serviceId);
      onChange({ ...value, intent_catalog_version: catalog.intent_catalog_version });
      message.success('Catalog version created.');
    } finally {
      setLoadingCatalog(false);
    }
  };

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Typography.Text strong>Validation bundle</Typography.Text>
      <Segmented
        value={value.threshold_preset}
        onChange={(next) => onChange({ ...value, threshold_preset: next as API.ThresholdPreset })}
        options={[
          { label: 'strict', value: 'strict' },
          { label: 'balanced', value: 'balanced' },
          { label: 'exploratory', value: 'exploratory' },
        ]}
      />
      <Space wrap>
        <Button onClick={loadLatest} loading={loadingLatest}>
          최신 bundle 불러오기
        </Button>
        <Button onClick={createPolicy} loading={loadingPolicy}>
          Policy 생성
        </Button>
        <Button onClick={createCatalog} loading={loadingCatalog}>
          Catalog 생성
        </Button>
      </Space>
      <Space wrap>
        <VersionChip label="policy" value={value.policy_version} />
        <VersionChip label="catalog" value={value.intent_catalog_version} />
      </Space>
    </Space>
  );
}
```

- [ ] **Step 2: Replace manual version fields in Test Runs**

Modify `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`:

- Remove visible `policy_version` and `intent_catalog_version` input fields.
- Keep hidden `Form.Item` values for submit payload.
- Render `ValidationBundlePanel` above CSV controls.
- On panel change, call:

```ts
createForm.setFieldsValue({
  policy_version: bundle.policy_version,
  intent_catalog_version: bundle.intent_catalog_version,
  threshold_preset: bundle.threshold_preset,
});
```

- [ ] **Step 3: Add next-action handoff after successful test run**

In `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`, after a passing summary render:

```tsx
{summary?.gate_passed && summary.risk_pass_rate === 1 ? (
  <WorkflowNextActionBar
    title="Release candidate ready"
    description="이 test run으로 Release 화면에서 후보를 선택할 수 있습니다."
    primaryLabel="Release 화면으로 이동"
    onPrimary={() => history.push('/releases')}
  />
) : null}
```

Import `history` from `@umijs/max` and `WorkflowNextActionBar` from components.

- [ ] **Step 4: Add Intent Catalog next-action**

Modify `frontend/intent-routing-console/src/pages/Intents/index.tsx` to show:

```tsx
<WorkflowNextActionBar
  title="Catalog work ready for validation"
  description="Intent와 Example 정리가 끝나면 Test Run에서 검증 bundle을 만듭니다."
  primaryLabel="Test Runs로 이동"
  onPrimary={() => history.push('/test-runs')}
  disabled={!catalogEditable}
/>
```

Place it above `IntentCatalogTable`.

- [ ] **Step 5: Verify Test Runs workflow**

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm typecheck
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm test:unit
```

Expected:

```text
typecheck exits 0
31+ tests pass
```

- [ ] **Step 6: Commit Test Runs workflow**

```bash
cd /home/haua/workspace/AiIntentRouting
git add frontend/intent-routing-console/src/pages/TestRuns frontend/intent-routing-console/src/pages/Intents/index.tsx
git commit -m "feat: guide test run validation bundle workflow"
```

---

### Task 7: Refactor Releases To Use Release Candidates

**Files:**
- Create: `frontend/intent-routing-console/src/pages/Releases/ReleaseCandidateSelect.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Releases/index.tsx`

- [ ] **Step 1: Add ReleaseCandidateSelect**

Create `frontend/intent-routing-console/src/pages/Releases/ReleaseCandidateSelect.tsx`:

```tsx
import { Select, Space, Tag, Typography } from 'antd';

type ReleaseCandidateSelectProps = {
  value?: string;
  onChange?: (testRunId: string, candidate: API.ReleaseCandidate) => void;
  candidates: API.ReleaseCandidate[];
};

export function ReleaseCandidateSelect({
  value,
  onChange,
  candidates,
}: ReleaseCandidateSelectProps) {
  return (
    <Select
      showSearch
      value={value}
      placeholder="Release candidate 선택"
      optionFilterProp="label"
      style={{ minWidth: 420 }}
      options={candidates.map((candidate) => ({
        value: candidate.test_run_id,
        label: candidate.test_run_id,
        disabled: !candidate.eligible,
        candidate,
        children: (
          <Space direction="vertical" size={0}>
            <Space>
              <Typography.Text code>{candidate.test_run_id}</Typography.Text>
              <Tag color={candidate.eligible ? 'green' : 'orange'}>
                {candidate.eligible ? 'eligible' : 'blocked'}
              </Tag>
            </Space>
            <Typography.Text type="secondary">
              policy {candidate.policy_version} / catalog {candidate.intent_catalog_version}
            </Typography.Text>
          </Space>
        ),
      }))}
      onChange={(next, option) => {
        const selected = Array.isArray(option) ? undefined : option.candidate;
        if (selected) onChange?.(next, selected);
      }}
    />
  );
}
```

- [ ] **Step 2: Load release candidates and rollback targets**

Modify `frontend/intent-routing-console/src/pages/Releases/index.tsx`:

- Add state:

```ts
const [candidates, setCandidates] = useState<API.ReleaseCandidate[]>([]);
const [releaseRows, setReleaseRows] = useState<API.Release[]>([]);
const [loadingCandidates, setLoadingCandidates] = useState(false);
```

- Add loader:

```ts
const loadReleaseOptions = async () => {
  if (!ready) return;
  setLoadingCandidates(true);
  try {
    const [nextCandidates, nextReleases] = await Promise.all([
      listReleaseCandidates(session.serviceId, { environment: selectedEnvironment }),
      listReleases(session.serviceId, selectedEnvironment),
    ]);
    setCandidates(nextCandidates);
    setReleaseRows(nextReleases);
  } finally {
    setLoadingCandidates(false);
  }
};
```

Call `loadReleaseOptions()` in the service-change `useEffect`.

- [ ] **Step 3: Replace manual release fields**

In the Create release card:

- Replace policy/catalog/test run inputs with `ReleaseCandidateSelect`.
- When candidate changes:

```ts
form.setFieldsValue({
  environment: selectedEnvironment,
  policy_version: candidate.policy_version,
  intent_catalog_version: candidate.intent_catalog_version,
  test_run_id: candidate.test_run_id,
});
```

- Replace rollback target text input with:

```tsx
<Select
  allowClear
  showSearch
  placeholder="Rollback target 선택"
  style={{ width: 320 }}
  options={releaseRows.map((release) => ({
    value: release.release_version,
    label: release.release_version,
  }))}
/>
```

- [ ] **Step 4: Refresh candidates after create/activate/rollback**

After successful `createRelease`, `activateRelease`, and `rollbackRelease`, run:

```ts
await loadReleaseOptions();
reload();
```

- [ ] **Step 5: Verify release workflow**

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm typecheck
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm test:unit
```

Expected:

```text
typecheck exits 0
all unit tests pass
```

- [ ] **Step 6: Commit Release workflow**

```bash
cd /home/haua/workspace/AiIntentRouting
git add frontend/intent-routing-console/src/pages/Releases
git commit -m "feat: create releases from candidates"
```

---

### Task 8: Refactor API Keys To Use Inventory And Scope Selectors

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`

- [ ] **Step 1: Load API key inventory and scope candidates**

Modify `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`:

```ts
const [keys, setKeys] = useState<API.ApiKey[]>([]);
const [scopeCandidates, setScopeCandidates] = useState<API.IntentRouteCandidate[]>([]);
const [loadingKeys, setLoadingKeys] = useState(false);

const loadApiKeyPageData = async () => {
  if (!ready || !canManage) return;
  setLoadingKeys(true);
  try {
    const [nextKeys, nextScopeCandidates] = await Promise.all([
      listApiKeys({ service_id: session.serviceId, environment: selectedEnvironment }),
      listIntentRouteCandidates(session.serviceId, {
        source: 'active_release',
        environment: selectedEnvironment,
      }),
    ]);
    setKeys(nextKeys);
    setScopeCandidates(nextScopeCandidates);
  } finally {
    setLoadingKeys(false);
  }
};
```

Call `loadApiKeyPageData()` when `session.serviceId`, `selectedEnvironment`, or role readiness changes.

- [ ] **Step 2: Replace allowed textareas**

Replace `allowed_intents` and `allowed_route_keys` text areas with `IntentRouteMultiSelect`:

```tsx
<Form.Item name="allowed_intents" label={helpLabel('Allowed intents', apiKeyHelp.allowedIntents)}>
  <IntentRouteMultiSelect
    mode="intent"
    candidates={scopeCandidates}
    placeholder="허용할 intent 선택"
  />
</Form.Item>
<Form.Item name="allowed_route_keys" label={helpLabel('Allowed route keys', apiKeyHelp.allowedRouteKeys)}>
  <IntentRouteMultiSelect
    mode="route"
    candidates={scopeCandidates}
    placeholder="허용할 route key 선택"
  />
</Form.Item>
```

Update `ApiKeyFormValues` so `allowed_intents?: string[]` and `allowed_route_keys?: string[]`. Remove `parseList`.

- [ ] **Step 3: Add explicit unrestricted choice text**

Above the selectors render:

```tsx
<Alert
  type="info"
  showIcon
  message="선택하지 않으면 selected Service 안에서 intent/route 제한 목록을 만들지 않습니다."
/>
```

- [ ] **Step 4: Add API key inventory table**

Add `ProTable<API.ApiKey>` below create result:

```tsx
<ProTable<API.ApiKey>
  rowKey="key_id"
  loading={loadingKeys}
  dataSource={keys}
  search={false}
  pagination={false}
  columns={[
    { title: 'Key ID', dataIndex: 'key_id', copyable: true },
    { title: 'App', dataIndex: 'app_id' },
    { title: 'Fingerprint', dataIndex: 'key_fingerprint', copyable: true },
    { title: 'Status', dataIndex: 'status' },
    { title: 'Expires', dataIndex: 'expires_at', valueType: 'dateTime' },
  ]}
/>
```

- [ ] **Step 5: Revoke from selected inventory row**

Add a column action:

```tsx
<ConfirmActionButton
  danger
  title="Revoke API key?"
  okText="Revoke"
  content={`Revoke ${row.key_id}.`}
  onConfirm={async () => {
    await revokeApiKey(row.key_id);
    message.success('API key revoked.');
    await loadApiKeyPageData();
  }}
>
  폐기
</ConfirmActionButton>
```

Keep manual key id revoke field only behind a compact fallback section titled `Manual revoke`.

- [ ] **Step 6: Verify API Keys workflow**

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm typecheck
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm test:unit
```

Expected:

```text
typecheck exits 0
all unit tests pass
```

- [ ] **Step 7: Commit API Keys workflow**

```bash
cd /home/haua/workspace/AiIntentRouting
git add frontend/intent-routing-console/src/pages/ApiKeys/index.tsx
git commit -m "feat: manage api keys from inventory"
```

---

### Task 9: End-To-End Verification And Manual QA

**Files:**
- Modify only if verification reveals a defect in files touched by Tasks 1-8.

- [ ] **Step 1: Run backend contract tests**

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_workflow_candidate_contract_docs.py tests/integration/test_admin_workflow_candidates_api.py tests/integration/test_admin_api_key_inventory_flow.py -q
```

Expected:

```text
all selected backend tests pass
```

- [ ] **Step 2: Run frontend checks**

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm typecheck
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm test:unit
PATH="/tmp/codex-pnpm-11-bin:$PATH" corepack pnpm build
```

Expected:

```text
typecheck exits 0
unit tests pass
build compiles successfully
```

- [ ] **Step 3: Run prohibited-pattern scan**

```bash
cd /home/haua/workspace/AiIntentRouting
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src src/intent_routing docs/AdminUI_Handbook/v04/PATTERN_KIT.md
```

Expected:

```text
No implementation matches. Documentation matches only where they describe prohibited or future behavior.
```

- [ ] **Step 4: Manual browser QA at local ports**

Start backend:

```bash
cd /home/haua/workspace/AiIntentRouting
DATABASE_URL='postgresql+psycopg://intent:intent@127.0.0.1:55432/intent_routing' APP_ENV=local INTENT_ROUTING_ENVIRONMENT=dev EMBEDDING_PROVIDER=fake RAW_TEXT_KEK_ID=local-kek-001 RAW_TEXT_KEK_BASE64=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= RAW_TEXT_LEGACY_KEKS_JSON='{}' uv run uvicorn intent_routing.main:create_app --factory --host 127.0.0.1 --port 30141
```

Start frontend:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
PATH="/tmp/codex-pnpm-11-bin:$PATH" HOST=127.0.0.1 PORT=30140 ADMIN_API_PROXY=http://127.0.0.1:30141 corepack pnpm dev
```

Open:

```text
http://127.0.0.1:30140
```

Manual QA happy path:

1. Log in as `local-admin@example.com`.
2. Select `IT Helpdesk Pilot`.
3. Create or inspect an active Intent.
4. Add and approve one positive Example.
5. Open Test Runs.
6. Load or create validation bundle without typing policy/catalog IDs.
7. Build or paste CSV.
8. Create Test Run.
9. Open Releases.
10. Select a Release candidate without typing policy/catalog/test run IDs.
11. Create Release.
12. Open API Keys.
13. Select allowed intents/routes from candidates.
14. Create API Key.
15. Confirm API Key inventory lists the key without displaying the raw secret.

- [ ] **Step 5: Commit final fixes if needed**

If Step 4 finds defects, commit focused fixes:

```bash
cd /home/haua/workspace/AiIntentRouting
git add docs src tests frontend/intent-routing-console/src
git commit -m "fix: polish admin workflow candidate flow"
```

If Step 4 finds no defects, do not create an empty commit.

## Acceptance Criteria

- A user can complete Intent/Example to Test Run to Release to API Key without manually copying internal IDs in the happy path.
- Every selector is scoped to the selected Service and server-derived roles.
- Release creation is available only from a passing, risk-clean candidate.
- API key allowed intents and route keys are selected from known Service values.
- API key inventory excludes raw key secrets.
- Unsupported governed workflows stay disabled or informational with `FutureFeatureNotice`.
- Manual ID entry remains only for source creation or an explicitly labelled fallback.

## Execution Recommendation

Use **Subagent-Driven** execution:

- Agent 1: docs and ADR contract.
- Agent 2: backend repository and endpoint contracts.
- Agent 3: frontend service/types and reusable workflow components.
- Agent 4: page-level workflow refactor.
- Main agent: integration review, verification, and manual QA.
