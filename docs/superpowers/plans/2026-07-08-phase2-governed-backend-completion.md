# Phase 2 Governed Backend Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining Phase 2 governed backend contracts after raw query approval: release diff/approval, masked export, server query contracts, and UI handoff verification.

**Architecture:** Continue using first-class `governed_action_requests` for server-side approvals and the existing release/runtime/audit models for state. Keep Admin UI Phase 2 actions disabled until backend contracts and integration tests pass. Avoid a generic workflow engine; add narrow helpers that match `docs/api/admin-phase2-contracts.md`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic-managed PostgreSQL, Pydantic, pytest, ruff, existing `IntentRoutingRepository`, existing `intent_routing.versions.releases` service module.

---

All paths below are relative to `/home/haua/workspace/AiIntentRouting/.worktrees/phase2-governed-backend`.

## Current Status

- Done: Task 1 ADR, Task 2 contract docs, Task 3 governed storage, Task 4 raw query approval API.
- Local dev DB has been upgraded to `0006_governed_workflow_requests`.
- Verified on local dev DB:

```bash
DATABASE_URL='postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing' \
  uv run pytest tests/integration/test_raw_query_approval_flow.py tests/integration/test_trace_audit_logs.py -q
```

Expected current result:

```text
17 passed
```

## File Structure

- `src/intent_routing/versions/releases.py`
  - Add release diff builder and governed release activation/rollback helpers.
- `src/intent_routing/db/repositories.py`
  - Add narrow query helpers only if release diff/export cannot be cleanly built from existing repository methods.
- `src/intent_routing/api/admin.py`
  - Add `ReleaseDiffResponse`, publish request response models, release request/approve/reject/activate endpoints, export request/response models, and export endpoint.
- `tests/integration/test_release_approval_flow.py`
  - New integration coverage for release diff and governed release activation.
- `tests/integration/test_admin_export_and_query_contracts.py`
  - New integration coverage for masked-only export and server-side query contract.
- `docs/api/admin-phase2-contracts.md`
  - Update only if implementation reveals a contract ambiguity; otherwise treat as fixed contract.
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
  - Final handoff update after backend tests pass.
- `docs/AdminUI_Handbook/v04/README.md`
  - Final handoff update after backend tests pass.
- `docs/AdminUI_Handbook/v04/SETUP_GUIDE.md`
  - Final handoff update after backend tests pass.

## Task 5: Implement Release Diff And Governed Approval Contract

**Files:**
- Modify: `src/intent_routing/versions/releases.py`
- Modify: `src/intent_routing/api/admin.py`
- Modify if needed: `src/intent_routing/db/repositories.py`
- Create: `tests/integration/test_release_approval_flow.py`

- [ ] **Step 1: Add failing release diff tests**

Create `tests/integration/test_release_approval_flow.py` and reuse helpers from `tests/integration/test_release_flow.py` where possible.

Add tests with these names:

```python
def test_release_diff_compares_candidate_to_active_release(db_session, monkeypatch):
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    active = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )
    assert client.post(
        f"/admin/v1/services/{service_id}/releases/{active}:activate",
        headers=_admin_headers(),
    ).status_code == 200
    candidate = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
        rollback_target=active,
    )

    response = client.get(
        f"/admin/v1/services/{service_id}/releases/{candidate}/diff",
        headers=_developer_headers(service_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["service_id"] == service_id
    assert body["release_version"] == candidate
    assert body["compare_to"] == active
    assert body["rollback_target"] == active
    assert "policy_version_diff" in body
    assert "catalog_version_diff" in body
    assert "model_version_diff" in body
    assert "test_run_diff" in body
```

```python
def test_release_activation_requires_governed_approval_for_service_developer(
    db_session,
    monkeypatch,
):
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    release_version = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )

    direct = client.post(
        f"/admin/v1/services/{service_id}/releases/{release_version}:activate",
        headers=_developer_headers(service_id),
    )
    assert direct.status_code == 403

    requested = client.post(
        f"/admin/v1/services/{service_id}/publish-requests",
        headers=_developer_headers(service_id),
        json={
            "resource_type": "release",
            "resource_id": release_version,
            "action": "activate",
            "target_version": release_version,
            "reason": "Promote tested release after green gate",
        },
    )
    assert requested.status_code == 201
    request_id = requested.json()["request_id"]

    self_approve = client.post(
        f"/admin/v1/services/{service_id}/publish-requests/{request_id}:approve",
        headers=_developer_headers(service_id),
        json={"reason": "Trying to approve my own request"},
    )
    assert self_approve.status_code == 403

    approved = client.post(
        f"/admin/v1/services/{service_id}/publish-requests/{request_id}:approve",
        headers=_owner_headers(service_id),
        json={"reason": "Release gate and diff reviewed"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    activated = client.post(
        f"/admin/v1/services/{service_id}/publish-requests/{request_id}:activate",
        headers=_developer_headers(service_id),
    )
    assert activated.status_code == 200
    assert activated.json()["active"] is True
```

Run:

```bash
DATABASE_URL='postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing' \
  uv run pytest tests/integration/test_release_approval_flow.py -q
```

Expected:

```text
FAIL
```

Failure should mention missing route or missing response fields.

- [ ] **Step 2: Add release diff service helper**

In `src/intent_routing/versions/releases.py`, add a dataclass and helper:

```python
@dataclass(frozen=True, slots=True)
class ReleaseDiff:
    service_id: str
    release_version: str
    compare_to: str | None
    policy_version_diff: dict[str, object]
    catalog_version_diff: dict[str, object]
    model_version_diff: dict[str, object]
    test_run_diff: dict[str, object]
    rollback_target: str | None
```

```python
def build_release_diff(
    repository: IntentRoutingRepository,
    *,
    service_id: str,
    release_version: str,
    compare_to: str | None = None,
) -> ReleaseDiff:
    candidate = repository.get_release(service_id, release_version)
    if candidate is None:
        raise ReleaseDependencyNotFoundError("Release does not exist.")

    baseline = (
        repository.get_release(service_id, compare_to)
        if compare_to is not None
        else repository.get_active_release(service_id, candidate.environment)
    )
    if baseline is not None and baseline.service_id != service_id:
        raise ReleaseDependencyNotFoundError("Compare release does not exist.")

    return ReleaseDiff(
        service_id=service_id,
        release_version=candidate.release_version,
        compare_to=baseline.release_version if baseline is not None else None,
        policy_version_diff={
            "from": baseline.policy_version if baseline is not None else None,
            "to": candidate.policy_version,
            "changed": baseline is None
            or baseline.policy_version != candidate.policy_version,
        },
        catalog_version_diff={
            "from": baseline.intent_catalog_version if baseline is not None else None,
            "to": candidate.intent_catalog_version,
            "changed": baseline is None
            or baseline.intent_catalog_version != candidate.intent_catalog_version,
        },
        model_version_diff={
            "from": baseline.model_version if baseline is not None else None,
            "to": candidate.model_version,
            "changed": baseline is None
            or baseline.model_version != candidate.model_version,
        },
        test_run_diff={
            "from": baseline.test_run_id if baseline is not None else None,
            "to": candidate.test_run_id,
            "pass_rate": float(candidate.pass_rate),
            "risk_pass_rate": float(candidate.risk_pass_rate),
            "gate_passed": True,
        },
        rollback_target=candidate.rollback_target,
    )
```

- [ ] **Step 3: Add release diff API model and endpoint**

In `src/intent_routing/api/admin.py`, add:

```python
class ReleaseDiffResponse(BaseModel):
    service_id: str
    release_version: str
    compare_to: str | None
    policy_version_diff: dict[str, object]
    catalog_version_diff: dict[str, object]
    model_version_diff: dict[str, object]
    test_run_diff: dict[str, object]
    rollback_target: str | None
```

Add endpoint before `GET /services/{service_id}/releases`:

```python
@router.get(
    "/services/{service_id}/releases/{release_version}/diff",
    response_model=ReleaseDiffResponse,
)
def get_release_diff(
    service_id: str,
    release_version: str,
    context: Annotated[AdminContext, Depends(require_admin_context)],
    session: Annotated[Session, Depends(get_admin_session)],
    compare_to: str | None = None,
) -> ReleaseDiffResponse:
    _require_release_review_access(context, service_id)
    repository = IntentRoutingRepository(session)
    _ensure_service_exists(repository, service_id)
    try:
        diff = release_service.build_release_diff(
            repository,
            service_id=service_id,
            release_version=release_version,
            compare_to=compare_to,
        )
    except release_service.ReleaseDependencyNotFoundError as exc:
        _raise_not_found(str(exc))
    return ReleaseDiffResponse(**diff.__dict__)
```

Also add:

```python
def _require_release_review_access(context: AdminContext, service_id: str) -> None:
    if context.has_role("system_admin"):
        return
    if context.has_any_service_role(
        service_id,
        {"service_developer", "service_owner", "auditor"},
    ):
        return
    raise_admin_forbidden("Release review scope is required for this action.")
```

- [ ] **Step 4: Add publish request API models and endpoints for releases**

In `src/intent_routing/api/admin.py`, add request/response models:

```python
class PublishRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: Literal["intent", "example", "release"]
    resource_id: str = Field(min_length=1)
    action: Literal["request", "activate", "rollback"]
    target_version: str | None = Field(default=None, min_length=1)
    reason: str = Field(min_length=10)
    evidence_refs: list[str] = Field(default_factory=list)
```

```python
class PublishRequestDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, min_length=1)
```

```python
class PublishRequestResponse(BaseModel):
    request_id: str
    service_id: str
    resource_type: str
    resource_id: str
    action: str
    status: str
    requested_by: str
    requested_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    reason: str
    decision_reason: str | None = None
```

Add endpoints:

- `POST /services/{service_id}/publish-requests`
- `POST /services/{service_id}/publish-requests/{request_id}:approve`
- `POST /services/{service_id}/publish-requests/{request_id}:reject`
- `POST /services/{service_id}/publish-requests/{request_id}:activate`

Use existing repository helpers:

```python
repository.create_governed_action_request(
    request_id=f"gar_{uuid4().hex}",
    service_id=service_id,
    resource_type=request.resource_type,
    resource_id=request.resource_id,
    action=request.action,
    requested_by=context.actor_id,
    requested_at=now,
    reason=request.reason,
)
```

On activation, require `status == "approved"` and `resource_type == "release"`, then call:

```python
before_state, release = release_service.activate_release(
    repository,
    service_id=service_id,
    release_version=publish_request.resource_id,
)
publish_request.status = "activated"
```

Write audit events:

- `publish.requested`
- `publish.approved`
- `publish.rejected`
- `release.activated`

- [ ] **Step 5: Preserve system_admin direct activation compatibility**

Keep existing `POST /services/{service_id}/releases/{release_version}:activate` for `system_admin`, because existing `tests/integration/test_release_flow.py` depends on it. Ensure service-scoped non-system-admin users receive 403.

Add this assertion to `tests/integration/test_release_approval_flow.py`:

```python
def test_system_admin_can_still_activate_release_directly(db_session, monkeypatch):
    service_id, policy_version, catalog_version, client = _release_setup(
        db_session,
        monkeypatch,
    )
    release_version = _create_valid_release(
        db_session,
        client,
        service_id,
        policy_version=policy_version,
        catalog_version=catalog_version,
    )

    response = client.post(
        f"/admin/v1/services/{service_id}/releases/{release_version}:activate",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert response.json()["active"] is True
```

- [ ] **Step 6: Verify release approval**

Run:

```bash
DATABASE_URL='postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing' \
  uv run pytest tests/integration/test_release_approval_flow.py tests/integration/test_release_flow.py -q
```

Expected:

```text
PASS
```

- [ ] **Step 7: Commit Task 5**

Run:

```bash
git add src/intent_routing/versions/releases.py src/intent_routing/api/admin.py src/intent_routing/db/repositories.py tests/integration/test_release_approval_flow.py
git commit -m "feat: add release approval workflow"
```

## Task 6: Implement Masked Export And Query Contract

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Modify: `src/intent_routing/db/repositories.py`
- Create: `tests/integration/test_admin_export_and_query_contracts.py`

- [ ] **Step 1: Add failing export tests**

Create `tests/integration/test_admin_export_and_query_contracts.py` with:

```python
def test_masked_runtime_log_export_excludes_raw_query_and_secret_material(
    db_session,
    monkeypatch,
):
    trace_id = _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_auditor_headers(SERVICE_ID),
        json={
            "resource_type": "runtime_log",
            "format": "jsonl",
            "filters": {"trace_id": trace_id},
            "reason": "Evidence export for audit ticket INC-20260708-export",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["format"] == "jsonl"
    assert body["content"]
    assert "query_masked" in body["content"]
    forbidden = (
        "query_raw",
        "ciphertext",
        "encrypted_dek",
        "auth_tag",
        "kek",
        RAW_QUERY,
    )
    assert not any(token in body["content"] for token in forbidden)
```

```python
def test_export_rejects_unsupported_filters_and_writes_audit(db_session, monkeypatch):
    _create_runtime_trace(db_session, monkeypatch)
    client = _client(db_session, monkeypatch)

    response = client.post(
        f"/admin/v1/services/{SERVICE_ID}/exports",
        headers=_auditor_headers(SERVICE_ID),
        json={
            "resource_type": "runtime_log",
            "format": "csv",
            "filters": {"raw_query": "should never be filterable"},
            "reason": "Evidence export for audit ticket INC-20260708-export",
        },
    )

    assert response.status_code == 400
    assert RAW_QUERY not in response.text
```

Run:

```bash
DATABASE_URL='postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing' \
  uv run pytest tests/integration/test_admin_export_and_query_contracts.py -q
```

Expected:

```text
FAIL
```

- [ ] **Step 2: Add repository export helpers**

In `src/intent_routing/db/repositories.py`, add narrow helpers:

```python
def list_masked_runtime_logs_for_export(
    self,
    service_id: str,
    *,
    trace_id: str | None = None,
    limit: int = 500,
) -> list[Mapping[str, Any]]:
    statement = select(*_masked_runtime_log_columns()).where(
        models.RuntimeLog.service_id == service_id
    )
    if trace_id is not None:
        statement = statement.where(models.RuntimeLog.trace_id == trace_id)
    rows = self.session.execute(
        statement.order_by(
            models.RuntimeLog.created_at.desc(),
            models.RuntimeLog.trace_id,
        ).limit(limit)
    ).mappings()
    return [cast("Mapping[str, Any]", row) for row in rows]
```

- [ ] **Step 3: Add export API models and endpoint**

In `src/intent_routing/api/admin.py`, add:

```python
class ExportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: Literal["intent", "example", "release", "runtime_log", "export"]
    format: Literal["csv", "jsonl"]
    filters: dict[str, object] = Field(default_factory=dict)
    reason: str = Field(min_length=10)
```

```python
class ExportResponse(BaseModel):
    export_id: str
    service_id: str
    resource_type: str
    status: Literal["completed", "rejected"]
    format: str
    content: str | None = None
    rejection_reason: str | None = None
    requested_by: str
    requested_at: datetime
```

Add endpoint:

```python
@router.post("/services/{service_id}/exports", response_model=ExportResponse)
def create_export(...):
    _require_export_access(context, service_id)
    ...
```

Allow only these runtime log filters:

```python
allowed_filters = {"trace_id"}
unknown_filters = set(request.filters) - allowed_filters
if unknown_filters:
    _raise_bad_request("Unsupported export filter.")
```

Serialize JSONL with `json.dumps(row, default=str, ensure_ascii=False)`.
Serialize CSV with `csv.DictWriter` over `MASKED_RUNTIME_LOG_FIELD_NAMES`.

Write audit events:

- `export.requested`
- `export.completed` on success
- `export.rejected` on validation rejection when a request is otherwise authenticated and scoped

- [ ] **Step 4: Verify export/query tests**

Run:

```bash
DATABASE_URL='postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing' \
  uv run pytest tests/integration/test_admin_export_and_query_contracts.py -q
```

Expected:

```text
PASS
```

- [ ] **Step 5: Commit Task 6**

Run:

```bash
git add src/intent_routing/api/admin.py src/intent_routing/db/repositories.py tests/integration/test_admin_export_and_query_contracts.py
git commit -m "feat: add masked admin export contract"
```

## Task 7: Final Verification And Admin UI Handoff

**Files:**
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- Modify: `docs/AdminUI_Handbook/v04/README.md`
- Modify: `docs/AdminUI_Handbook/v04/SETUP_GUIDE.md`

- [ ] **Step 1: Run backend verification bundle**

Run:

```bash
DATABASE_URL='postgresql+psycopg://intent:intent@127.0.0.1:30142/intent_routing' \
  uv run pytest \
    tests/unit/test_admin_auth_context.py \
    tests/unit/test_admin_auth_api_contract.py \
    tests/unit/test_admin_phase2_contract_docs.py \
    tests/unit/test_governed_workflow_models.py \
    tests/integration/test_admin_account_auth_api.py \
    tests/integration/test_admin_service_rbac_flow.py \
    tests/integration/test_raw_query_approval_flow.py \
    tests/integration/test_release_approval_flow.py \
    tests/integration/test_release_flow.py \
    tests/integration/test_admin_export_and_query_contracts.py \
    -q
```

Expected:

```text
PASS
```

- [ ] **Step 2: Verify lint**

Run:

```bash
uv run ruff check \
  src/intent_routing/api/admin.py \
  src/intent_routing/db/repositories.py \
  src/intent_routing/versions/releases.py \
  tests/integration/test_raw_query_approval_flow.py \
  tests/integration/test_release_approval_flow.py \
  tests/integration/test_admin_export_and_query_contracts.py
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Update Admin UI handoff docs**

Update the v04 handbook files so:

- raw query approval backend is marked implemented.
- release diff/approval backend is marked implemented.
- masked export backend is marked implemented.
- Admin UI buttons remain gated until frontend routes call these endpoints and have UX tests.
- unsupported pagination/live polling UI still uses `FutureFeatureNotice`.

- [ ] **Step 4: Verify UI handoff text**

Run:

```bash
rg -n "raw query approval|release diff|masked export|FutureFeatureNotice|Phase 2" \
  docs/AdminUI_Handbook/v04/PATTERN_KIT.md \
  docs/AdminUI_Handbook/v04/README.md \
  docs/AdminUI_Handbook/v04/SETUP_GUIDE.md
```

Expected:

```text
matching lines for implemented backend contracts and remaining UI gates
```

- [ ] **Step 5: Commit Task 7**

Run:

```bash
git add docs/AdminUI_Handbook/v04/PATTERN_KIT.md docs/AdminUI_Handbook/v04/README.md docs/AdminUI_Handbook/v04/SETUP_GUIDE.md
git commit -m "docs: update phase2 admin ui handoff"
```

## Task 8: Publish Review Branch

**Files:**
- No code files unless verification exposes defects.

- [ ] **Step 1: Confirm branch state**

Run:

```bash
git status --short --branch
git log --oneline --decorate --max-count=10
```

Expected:

```text
clean working tree
branch codex/phase2-governed-backend ahead of origin/main
```

- [ ] **Step 2: Push branch**

Run:

```bash
git push -u origin codex/phase2-governed-backend
```

Expected:

```text
branch pushed successfully
```

- [ ] **Step 3: Open draft PR**

Open a draft PR with:

```text
Title: [codex] Complete Phase 2 governed backend contracts

Summary:
- Adds governed workflow storage and raw query approval API
- Adds release diff/approval workflow
- Adds masked export contract
- Updates Admin UI handoff docs

Verification:
- ruff check ...
- pytest ... (include exact command output)
```

## Self-Review

Spec coverage:

- `docs/api/admin-phase2-contracts.md` release diff endpoint is implemented by Task 5.
- `docs/api/admin-phase2-contracts.md` publish request approve/reject/activate workflow is implemented by Task 5.
- `docs/api/admin-phase2-contracts.md` masked export endpoint is implemented by Task 6.
- Existing raw query approval workflow remains covered by Task 7 verification.
- UI handoff remains covered by Task 7 and does not prematurely enable frontend actions.

Placeholder scan:

- No unfinished markers or unspecified test steps remain.
- Each code task includes exact files, endpoint names, test names, commands, and expected results.

Type consistency:

- `resource_type`, `action`, and `status` values match `docs/api/admin-phase2-contracts.md`.
- Release request activation reuses existing `GovernedActionRequest` storage instead of adding a second workflow table.
- Export content uses existing masked runtime log projection and never selects raw query/encryption fields.
