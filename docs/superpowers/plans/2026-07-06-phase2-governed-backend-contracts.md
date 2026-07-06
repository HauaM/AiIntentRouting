# Phase 2 Governed Backend Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define and implement the backend contracts required before Admin UI Phase 2 governed workflows can become active.

**Architecture:** Build on account login, service-scoped RBAC, and the fine-grained authorization roadmap. Each governed workflow gets an explicit API contract, data model, authorization rule, audit event, and UI-ready response shape before any Admin UI action is enabled.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Pydantic, pytest, existing audit log model, Admin UI `FutureFeatureNotice` until contracts ship.

---

All paths below are relative to `/home/haua/workspace/AiIntentRouting`.

## Preconditions

- Account auth and service-scoped RBAC from PR #22 are present.
- `docs/security/fine-grained-authorization-todo.md` remains the long-term authorization destination.
- Normal Admin UI requests use the `irt_admin_session` HttpOnly cookie.

## Scope

In scope:
- Backend API contract decisions for Phase 2 governed workflows.
- ADR updates where decisions affect API contracts, authorization, database schema, audit workflow, or core business workflow.
- Data models and API endpoints for the first governed workflows.
- Authorization matrix tests.
- Admin UI remains disabled/informational until backend endpoints and tests exist.

Out of scope:
- Enabling Phase 2 Admin UI buttons before backend contracts pass.
- External identity provider integration.
- Full policy engine if a narrower contract satisfies the first governed workflow.

## Required Phase 2 Contracts

1. Publish request/pending/approve/reject for Intent Catalog changes.
2. Example reject with reason.
3. Raw query two-person approval queue.
4. Time-limited raw query view token.
5. Release diff and approval workflow.
6. CSV export with masked-only data contract.
7. Server pagination, compound filters, and live polling contract.

---

### Task 1: Write ADRs For Governed Workflow Boundaries

**Files:**
- Create: `docs/adr/2026-07-06-phase2-governed-workflow-contracts.md`
- Modify: `docs/security/fine-grained-authorization-todo.md`

- [ ] **Step 1: Draft ADR**

Create an ADR with:
- decision to model governed workflows as first-class server-side requests.
- alternatives: direct action APIs, generic workflow engine, narrow governed workflow tables.
- consequences for audit logs, authorization tests, and UI enablement.

- [ ] **Step 2: Link TODO roadmap**

Update `docs/security/fine-grained-authorization-todo.md` so the Phase 2 contract ADR is linked near the existing account auth ADR.

- [ ] **Step 3: Verify ADR shape**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
rg -n "Phase 2|two-person|release diff|CSV export|approval policy|Status|Alternatives Considered|Consequences" docs/adr/2026-07-06-phase2-governed-workflow-contracts.md docs/security/fine-grained-authorization-todo.md
```

Expected:
- All required decision sections and Phase 2 workflow terms appear.

---

### Task 2: Define Approval And Permission Resource Model

**Files:**
- Create: `docs/api/admin-phase2-contracts.md`
- Test: `tests/unit/test_admin_phase2_contract_docs.py`

- [ ] **Step 1: Add failing docs contract test**

Create a test that requires `docs/api/admin-phase2-contracts.md` to define:
- resource types: `intent`, `example`, `release`, `runtime_log`, `raw_query`, `export`.
- action names: `request`, `approve`, `reject`, `activate`, `rollback`, `decrypt`, `export`.
- approval invariants: author cannot approve own request, two-person raw query approval, audit event required for every state transition.

- [ ] **Step 2: Create contract doc**

Add endpoint tables for:
- `POST /admin/v1/services/{service_id}/publish-requests`
- `POST /admin/v1/services/{service_id}/publish-requests/{request_id}:approve`
- `POST /admin/v1/services/{service_id}/publish-requests/{request_id}:reject`
- `POST /admin/v1/services/{service_id}/runtime-logs/{trace_id}/raw-query-view-requests`
- `POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:approve`
- `POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:reject`
- `POST /admin/v1/services/{service_id}/raw-query-view-requests/{request_id}:issue-token`
- `GET /admin/v1/services/{service_id}/releases/{release_version}/diff`
- `POST /admin/v1/services/{service_id}/exports`

- [ ] **Step 3: Verify docs contract**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_phase2_contract_docs.py -q
```

Expected:
- The docs contract test passes.

---

### Task 3: Implement Governed Request Storage

**Files:**
- Create: `alembic/versions/0006_governed_workflow_requests.py`
- Modify: `src/intent_routing/db/models.py`
- Modify: `src/intent_routing/db/repositories.py`
- Test: `tests/unit/test_governed_workflow_models.py`

- [ ] **Step 1: Add failing model tests**

Tests must prove:
- governed requests store `request_id`, `service_id`, `resource_type`, `resource_id`, `action`, `status`, `requested_by`, `requested_at`, `decided_by`, `decided_at`, and `reason`.
- raw query tokens store only token hashes and expiry timestamps.
- status transitions cannot skip from `pending` to token-issued without approval.

- [ ] **Step 2: Add migration and models**

Create tables:
- `governed_action_requests`
- `raw_query_view_tokens`

Use explicit indexes on `service_id`, `status`, `resource_type`, and `expires_at`.

- [ ] **Step 3: Add repository helpers**

Add helpers to create, list, approve, reject, and expire governed requests.

- [ ] **Step 4: Verify model tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_governed_workflow_models.py -q
```

Expected:
- Model tests pass.

---

### Task 4: Implement Raw Query Two-Person Approval Contract

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Modify: `src/intent_routing/db/repositories.py`
- Test: `tests/integration/test_raw_query_approval_flow.py`

- [ ] **Step 1: Add failing integration tests**

Tests must prove:
- `service_operator` can request raw query access with a reason.
- `auditor` or `system_admin` can approve the request.
- requester cannot approve their own request.
- token issuance requires approval.
- raw query decrypt with token writes `raw_query.viewed` audit log and does not print raw query in CLI/evidence outputs.

- [ ] **Step 2: Implement endpoints**

Implement the raw query request/approve/reject/token endpoints from `docs/api/admin-phase2-contracts.md`.

- [ ] **Step 3: Verify integration tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_raw_query_approval_flow.py -q
```

Expected:
- Raw query approval tests pass.

---

### Task 5: Implement Release Diff And Approval Contract

**Files:**
- Modify: `src/intent_routing/versions/releases.py`
- Modify: `src/intent_routing/api/admin.py`
- Test: `tests/integration/test_release_approval_flow.py`

- [ ] **Step 1: Add failing release approval tests**

Tests must prove:
- release diff compares policy version, catalog version, model version, test run, rollback target, and active release.
- service developer can create a release request but cannot activate prod directly unless already `system_admin`.
- service owner or system admin approval is required by the Phase 2 contract.
- every approve/reject/activate transition writes an audit log.

- [ ] **Step 2: Implement diff and approval endpoints**

Add release diff endpoint and approval request transitions. Keep existing direct activate/rollback behavior available only where current contracts require it.

- [ ] **Step 3: Verify release tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_release_approval_flow.py tests/integration/test_release_flow.py -q
```

Expected:
- New approval tests pass and existing release flow regressions remain green.

---

### Task 6: Implement CSV Export And Server Query Contracts

**Files:**
- Modify: `src/intent_routing/api/admin.py`
- Modify: `src/intent_routing/db/repositories.py`
- Test: `tests/integration/test_admin_export_and_query_contracts.py`

- [ ] **Step 1: Add failing export/query tests**

Tests must prove:
- exports contain masked text only.
- exports never include API key secrets, raw query text, encrypted DEKs, ciphertext, or KEK material.
- list endpoints support explicit `limit`/`cursor` or `offset` contract chosen in the ADR.
- compound filters are server-side and documented.

- [ ] **Step 2: Implement export and query APIs**

Add export endpoint and server query parameters according to `docs/api/admin-phase2-contracts.md`.

- [ ] **Step 3: Verify export/query tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_export_and_query_contracts.py -q
```

Expected:
- Export/query tests pass.

---

### Task 7: Final Verification And UI Handoff

**Files:**
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- Modify: `docs/AdminUI_Handbook/v04/README.md`
- Modify: `docs/AdminUI_Handbook/v04/SETUP_GUIDE.md`

- [ ] **Step 1: Update Admin UI phase table**

Move implemented Phase 2 contracts from `Future backend` to `Current API writes` only after backend tests pass.

- [ ] **Step 2: Run full relevant backend verification**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_auth_context.py tests/unit/test_admin_auth_api_contract.py tests/integration/test_admin_account_auth_api.py tests/integration/test_admin_service_rbac_flow.py tests/integration/test_raw_query_approval_flow.py tests/integration/test_release_approval_flow.py tests/integration/test_admin_export_and_query_contracts.py -q
```

Expected:
- All selected tests pass.

- [ ] **Step 3: Keep UI disabled until contract completion**

Confirm Admin UI still renders `FutureFeatureNotice` for any Phase 2 workflow whose backend tests are missing:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
rg -n "FutureFeatureNotice|raw query|release diff|CSV export|live polling|server pagination" src
```

Expected:
- Unsupported features are disabled or informational.

---

## Self-Review

Spec coverage:
- Every Phase 2 item in the v04 pattern kit has a backend contract task.
- Fine-grained authorization TODO items are represented through resource/action/approval/audit tasks.

Placeholder scan:
- No TBD/TODO placeholders are present.

Type consistency:
- Resource and action names are lower-case server concepts, not UI labels.
- Raw query workflows keep raw text out of normal UI, exports, logs, and evidence.
