# Admin UI Phase 1 RBAC Write Flows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Admin UI Phase 1 write flows on top of the completed account login and service-scoped RBAC model.

**Architecture:** Use the existing Umi Max Admin UI, Umi `request`, and the `adminSession` model introduced by account auth. Normal browser requests use the `irt_admin_session` HttpOnly cookie with `withCredentials: true`; buttons and pages are gated from `/auth/me` and `/me/services` roles, not client-supplied actor headers.

**Tech Stack:** Umi Max 4, React 18, Ant Design 5, ProComponents, FastAPI Admin API, service-scoped RBAC, Vitest, pytest.

---

All paths below are relative to `/home/haua/workspace/AiIntentRouting`.

## Preconditions

- Base the branch on `origin/main` at or after PR #22, which includes account login and service-scoped RBAC.
- Do not extend the old `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope` Admin UI flow.
- Keep Phase 2 governed workflow features disabled or informational.

## Scope

In scope:
- Intent create/update UI for users with `system_admin`, `service_owner`, or `service_developer`.
- Example list/create/approve UI for users with catalog access.
- Policy version and catalog version create actions.
- CSV test run create/results UI.
- Release list/create/activate/rollback UI, with activation and rollback restricted to `system_admin` until release-operation separation is designed.
- API key create/revoke UI restricted to `system_admin`.
- Role-gated buttons, menus, empty states, and 403 handling using authenticated session state.

Out of scope:
- Publish pending/approve/reject.
- Example reject with reason.
- Release diff approval workflow.
- Raw query two-person approval or time-limited raw query tokens.
- Environment-specific authorization beyond the current Service environment display.
- Server pagination, compound filters, and live polling.

## File Structure

- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
  - Add role helper functions such as `hasAnyDisplayRole` and `canUsePhase1Action`.
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
  - Add Phase 1 response/request types for examples, policy versions, catalog versions, test runs, releases, and API keys.
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
  - Add current Admin API write functions using Umi `request`; rely on global `withCredentials`.
- Create: `frontend/intent-routing-console/src/components/ConfirmActionButton.tsx`
  - Reuse the v04 confirm pattern for dangerous writes.
- Modify: `frontend/intent-routing-console/src/components/IntentCatalogTable.tsx`
  - Add create/edit entry points gated by catalog roles.
- Modify: `frontend/intent-routing-console/src/pages/Intents/index.tsx`
  - Add drawers/forms for Intent and Example workflows.
- Create: `frontend/intent-routing-console/src/pages/Releases/index.tsx`
  - Add release list/create/activate/rollback workflows.
- Create: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
  - Add test run create/results workflows.
- Create: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
  - Add API key create/revoke workflows.
- Modify: `frontend/intent-routing-console/config/config.ts`
  - Add routes for Phase 1 pages.
- Test: focused Vitest tests under existing component/model/service test patterns.

---

### Task 1: Add Role Helpers And Phase 1 Access Tests

**Files:**
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`

- [ ] **Step 1: Add failing tests for role gates**

Add tests that prove:
- `service_developer` can edit catalog for the selected Service.
- `service_operator` cannot edit catalog.
- `system_admin` can manage releases and API keys.
- no helper reads legacy Admin header values.

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/models/adminSession.test.ts
```

Expected:
- Fails because the new role helper functions do not exist yet.

- [ ] **Step 2: Implement role helpers**

Add helpers to `adminSession.ts`:

```ts
export const hasAnyDisplayRole = (session: AdminSession, roles: string[]) => {
  const displayRoles = getDisplayRoles(session);
  return roles.some((role) => displayRoles.includes(role));
};

export const canEditCatalog = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin', 'service_owner', 'service_developer']);

export const canManageReleases = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin']);

export const canManageApiKeys = (session: AdminSession) =>
  hasAnyDisplayRole(session, ['system_admin']);
```

- [ ] **Step 3: Verify role helper tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/models/adminSession.test.ts
```

Expected:
- Role helper tests pass.

---

### Task 2: Add Phase 1 Admin Service Functions

**Files:**
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Test: `frontend/intent-routing-console/src/services/adminServices.test.ts`

- [ ] **Step 1: Add tests for write service paths**

Create service tests that mock Umi `request` and assert these paths/methods:
- `POST /services/{sid}/intents`
- `PATCH /services/{sid}/intents/{intent_id}`
- `GET/POST /services/{sid}/intents/{intent_id}/examples`
- `PATCH /services/{sid}/examples/{example_id}:approve`
- `POST /services/{sid}/policy-versions`
- `POST /services/{sid}/catalog-versions`
- `POST /services/{sid}/test-runs`
- `GET /services/{sid}/test-runs/{test_run_id}`
- `GET /services/{sid}/test-runs/{test_run_id}/results`
- `GET/POST /services/{sid}/releases`
- `POST /services/{sid}/releases/{release_version}:activate`
- `POST /services/{sid}/releases/{release_version}:rollback`
- `POST /api-keys`
- `POST /api-keys/{key_id}:revoke`

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts
```

Expected:
- Fails until the functions exist.

- [ ] **Step 2: Add typed service functions**

Implement the functions in `adminServices.ts` using the existing `servicePath` helper and Umi `request`. Do not add custom auth headers; global request config already sends cookies.

- [ ] **Step 3: Verify service tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts
```

Expected:
- Service path tests pass.

---

### Task 3: Add Intent And Example Write UI

**Files:**
- Create or modify focused components under `frontend/intent-routing-console/src/pages/Intents/`
- Modify: `frontend/intent-routing-console/src/components/IntentCatalogTable.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Intents/index.tsx`

- [ ] **Step 1: Add UI tests for gated buttons**

Test that:
- users without catalog roles see no create/edit/approve controls.
- users with catalog roles see Intent create/edit and Example create/approve controls.
- approve uses confirm before calling the API.

- [ ] **Step 2: Implement Intent create/edit drawers**

Use Ant Design `Drawer` + `ProForm`. Fields:
- `intent_id` disabled on edit.
- `domain`, `display_name`, `description`, `route_key`, `status`.
- `include_keywords`, `exclude_keywords` as tag inputs.

- [ ] **Step 3: Implement Example drawer**

Use current API only:
- list examples for selected intent.
- create positive/negative examples.
- approve an example through `ConfirmActionButton`.
- keep reject hidden or disabled as Phase 2.

- [ ] **Step 4: Verify Intents UI**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit
corepack pnpm typecheck
```

Expected:
- Unit tests and TypeScript pass.

---

### Task 4: Add Releases, Test Runs, And API Key Pages

**Files:**
- Create: `frontend/intent-routing-console/src/pages/Releases/index.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- Create: `frontend/intent-routing-console/src/pages/ApiKeys/index.tsx`
- Modify: `frontend/intent-routing-console/config/config.ts`
- Modify: `frontend/intent-routing-console/src/components/AdminShell.tsx`

- [ ] **Step 1: Add route and access tests**

Assert pages show:
- release actions only for `system_admin`.
- API key actions only for `system_admin`.
- test run actions for catalog roles.
- Phase 2 notices for release diff approval and CSV export.

- [ ] **Step 2: Implement Releases page**

Show list, active release, create form, activate button, rollback button. Use `ConfirmActionButton` for activate and rollback.

- [ ] **Step 3: Implement Test Runs page**

Create test runs and display summary/results. Do not add CSV export; show `FutureFeatureNotice`.

- [ ] **Step 4: Implement API Keys page**

Create and revoke API keys. Display newly created secret only in the create result response area; never persist it in local storage.

- [ ] **Step 5: Verify pages**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit
corepack pnpm typecheck
corepack pnpm build
```

Expected:
- Vitest, TypeScript, and build pass.

---

### Task 5: Backend And UI Regression

**Files:**
- Read-only verification across backend and frontend.

- [ ] **Step 1: Run backend RBAC and current Admin API tests**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_passwords.py tests/unit/test_admin_sessions.py tests/unit/test_admin_auth_context.py tests/unit/test_admin_auth_api_contract.py tests/unit/test_account_auth_schema_contract.py tests/integration/test_admin_account_auth_api.py tests/integration/test_admin_service_rbac_flow.py -q
uv run pytest tests/integration/test_admin_catalog_api.py tests/integration/test_release_flow.py tests/integration/test_ops_metrics_api.py tests/integration/test_trace_audit_logs.py -q
```

Expected:
- All selected tests pass or documented skips remain unchanged.

- [ ] **Step 2: Run forbidden pattern scan**

Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" src config package.json
```

Expected:
- No matches in normal Admin UI source/config.

- [ ] **Step 3: Manual smoke**

Run backend and frontend locally. Verify:
- unauthenticated pages redirect to `/login`.
- login restores user and accessible Services.
- service picker only lists Services from `/me/services`.
- Phase 1 write controls follow the selected Service roles.
- Phase 2 controls remain disabled or informational.

---

## Self-Review

Spec coverage:
- Phase 1 write surfaces are covered by Tasks 2-4.
- Account login and service RBAC assumptions are covered by Preconditions and Task 5.
- Phase 2 exclusion is covered in every dangerous/future area.

Placeholder scan:
- No TBD/TODO placeholders are present.

Type consistency:
- UI role names match the account auth ADR and `docs/security/fine-grained-authorization-todo.md`.
- Admin API paths match the current FastAPI routes.
