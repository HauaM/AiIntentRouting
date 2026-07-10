# Admin UI C-2 Role Assignment UI/API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build C-2 so a `system_admin` can grant and revoke user Service roles after C-1 Service creation, and so `/me/services` reflects those persisted role assignments.

**Architecture:** Add a Service-scoped membership API under `/admin/v1/services/{service_id}/members` using the existing `user_service_roles` table and session-derived `AdminContext`. Keep the first UI as a membership panel on `/services`, replace the current C-2 `FutureFeatureNotice`, and keep normal browser requests on the `irt_admin_session` cookie without trusted actor headers. Record append-only audit events for every grant and revoke.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy ORM, existing repository layer, pytest, React 18, TypeScript, Umi Max 4, Ant Design 5, Ant Design Pro patterns, Vitest, Umi `request`.

---

## Required Context

Read these before implementing:

- Session-provided project instructions for `/home/haua/workspace/AiIntentRouting`; no local `AGENTS.md` was present during planning.
- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md`
- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- `docs/AdminUI_Handbook/v04/SETUP_GUIDE.md`
- `docs/superpowers/plans/2026-07-08-admin-ui-c2-service-membership-roles.md`

## Current State

- C-1 Service creation UI/API is implemented.
- C-3 API key/runtime setup has implementation evidence and should not be changed by C-2 except for regression verification.
- `frontend/intent-routing-console/src/pages/Services/index.tsx` still renders C-2 role assignment as `FutureFeatureNotice`.
- `src/intent_routing/api/admin.py` has no `/admin/v1/services/{service_id}/members...` membership endpoints.
- `src/intent_routing/db/models.py` already has `UserServiceRole` with primary key `(user_id, service_id, role)`, `assigned_by`, and `assigned_at`.
- `src/intent_routing/db/repositories.py` already has `SERVICE_ADMIN_ROLES`, `assign_user_service_role`, `list_user_service_roles`, `list_service_roles_for_user`, and `list_services_for_user`.
- Existing RBAC tests prove seeded repository roles work, but not product APIs/UI for grant and revoke.
- Current git status observed during planning included untracked `.env`; do not read, stage, print, or modify it.

## C-2 Scope

Backend endpoints:

- `GET /admin/v1/users?query={email_or_name}&limit=25`
- `GET /admin/v1/services/{service_id}/members`
- `POST /admin/v1/services/{service_id}/members/{user_id}/roles`
- `DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}`

Authorization:

- C-2 baseline: only `system_admin` can list members, grant roles, and revoke roles.
- `service_owner` delegation remains outside the baseline. Do not enable it without a new approved ADR update and guardrail tests.
- Normal browser Admin UI requests must use `irt_admin_session` cookie. They must not send `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope`.

Storage:

- Use existing `user_service_roles` first.
- No migration is needed for baseline direct role grant/revoke.
- Propose a migration only if scope expands to invitations, membership status, role expiry, revocation history outside audit logs, team inheritance, or environment-specific membership.

Audit events:

- `service_membership.role_granted`
- `service_membership.role_revoked`

Frontend:

- Add a selected-Service membership panel below the selected Service area on `/services`.
- Include user search, current member/role list, role grant, and role revoke.
- Use Ant Design Pro/Umi patterns, Umi `request`, and local state or ProTable reload.
- Do not add React Query or axios.

## API Contract

### `GET /admin/v1/users`

Request:

- Query params: `query: str | None`, `limit: int = 25`, bounds `1..25`.
- Match active and disabled Admin users by case-insensitive email, display name, or user ID.
- Empty query may return the first `limit` users ordered by normalized email, but the UI should send a typed query before grant.

Response:

```json
[
  {
    "user_id": "developer-1",
    "email": "developer@example.com",
    "display_name": "Developer One",
    "status": "active"
  }
]
```

Must not expose `password_hash`, `token_hash`, `session_token`, raw session values, or password material.

### `GET /admin/v1/services/{service_id}/members`

Response:

```json
[
  {
    "service_id": "it-helpdesk",
    "user": {
      "user_id": "developer-1",
      "email": "developer@example.com",
      "display_name": "Developer One",
      "status": "active"
    },
    "roles": [
      {
        "role": "service_developer",
        "assigned_by": "system-admin-1",
        "assigned_at": "2026-07-10T00:00:00Z"
      }
    ]
  }
]
```

### `POST /admin/v1/services/{service_id}/members/{user_id}/roles`

Request:

```json
{
  "role": "service_developer"
}
```

Response:

```json
{
  "service_id": "it-helpdesk",
  "user_id": "developer-1",
  "role": "service_developer",
  "assigned_by": "system-admin-1",
  "assigned_at": "2026-07-10T00:00:00Z"
}
```

Duplicate grant should be idempotent: return `200 OK` or `201 Created` with the existing assignment and do not write a second grant audit event. Prefer `200 OK` for an existing role and `201 Created` for a new role only if the implementation can distinguish cleanly; otherwise use `200 OK` for both and document it in tests.

### `DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}`

Response:

```json
{
  "service_id": "it-helpdesk",
  "user_id": "developer-1",
  "role": "service_developer",
  "revoked_by": "system-admin-1",
  "revoked_at": "2026-07-10T00:00:00Z"
}
```

Revoking a missing role should return `404` with the existing not-found envelope and should not write a revoke audit event.

## File Structure

Backend:

- Modify `src/intent_routing/api/admin.py`
  - Add Pydantic models for user search, member listing, role grant request, grant response, and revoke response.
  - Add `_require_service_membership_admin_access(context)`.
  - Add four endpoints in the C-1 Service area near `/me/services` and `POST /services`.
  - Write grant/revoke audit events.
- Modify `src/intent_routing/db/repositories.py`
  - Add `list_admin_users(query: str | None, limit: int)`.
  - Add `list_service_member_roles(service_id: str)`.
  - Add `get_user_service_role(user_id: str, service_id: str, role: str)`.
  - Add `ensure_user_service_role(...)`.
  - Add `delete_user_service_role(role_record)`.
- Do not modify `src/intent_routing/db/models.py` or add Alembic migrations for baseline C-2.

Backend tests:

- Modify `tests/unit/test_admin_auth_api_contract.py`.
- Modify `tests/unit/test_account_auth_schema_contract.py`.
- Modify `tests/unit/test_admin_auth_context.py`.
- Modify `tests/integration/test_admin_service_rbac_flow.py`.

Frontend:

- Modify `frontend/intent-routing-console/src/types/api.d.ts`.
- Modify `frontend/intent-routing-console/src/services/adminServices.ts`.
- Modify `frontend/intent-routing-console/src/models/adminSession.ts`.
- Create `frontend/intent-routing-console/src/pages/Services/serviceMembers.ts`.
- Create `frontend/intent-routing-console/src/pages/Services/ServiceMembershipPanel.tsx`.
- Modify `frontend/intent-routing-console/src/pages/Services/index.tsx`.

Frontend tests:

- Modify `frontend/intent-routing-console/src/services/adminServices.test.ts`.
- Modify `frontend/intent-routing-console/src/models/adminSession.test.ts`.
- Create `frontend/intent-routing-console/src/pages/Services/serviceMembers.test.ts`.

Docs contract:

- Modify `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`.
- Modify `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`.
- Modify `tests/unit/test_admin_ui_handbook_docs_contract.py`.

## Tasks

### Task 1: Backend OpenAPI Contract Tests

**Files:**

- Modify: `tests/unit/test_admin_auth_api_contract.py`
- Later implementation target: `src/intent_routing/api/admin.py`

**Tests to add first:**

- `test_c2_membership_openapi_contract_is_registered`
- `test_c2_membership_openapi_contract_omits_secret_fields`

Use this test shape:

```python
def test_c2_membership_openapi_contract_is_registered() -> None:
    openapi = create_app().openapi()
    paths = openapi["paths"]

    assert "get" in paths["/admin/v1/users"]
    assert "get" in paths["/admin/v1/services/{service_id}/members"]
    assert "post" in paths["/admin/v1/services/{service_id}/members/{user_id}/roles"]
    assert "delete" in paths[
        "/admin/v1/services/{service_id}/members/{user_id}/roles/{role}"
    ]


def test_c2_membership_openapi_contract_omits_secret_fields() -> None:
    openapi = create_app().openapi()
    schema_text = "\n".join(
        str(schema)
        for name, schema in openapi["components"]["schemas"].items()
        if "AdminUser" in name or "ServiceMember" in name or "ServiceRole" in name
    )

    assert "password_hash" not in schema_text
    assert "token_hash" not in schema_text
    assert "session_token" not in schema_text
```

- [ ] Run failing test:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_auth_api_contract.py -q
```

Expected: fails because C-2 paths and schemas are not registered.

- [ ] Implement only enough Pydantic model and route skeleton code in `src/intent_routing/api/admin.py` for paths to appear, without grant/revoke logic yet.
- [ ] Run the same command again.

Expected: contract tests pass, deeper behavior tests still fail until later tasks.

### Task 2: Repository User And Membership Tests

**Files:**

- Modify: `tests/unit/test_account_auth_schema_contract.py`
- Later implementation target: `src/intent_routing/db/repositories.py`

**Tests to add first:**

- Extend `test_repository_exposes_account_auth_helpers` to include:
  - `list_admin_users`
  - `list_service_member_roles`
  - `get_user_service_role`
  - `ensure_user_service_role`
  - `delete_user_service_role`
- Add `test_repository_searches_admin_users_without_secret_fields`.
- Add `test_repository_ensures_and_deletes_user_service_roles`.

Use this helper-level assertion shape for method existence:

```python
assert {
    "list_admin_users",
    "list_service_member_roles",
    "get_user_service_role",
    "ensure_user_service_role",
    "delete_user_service_role",
}.issubset(dir(IntentRoutingRepository))
```

Use this DB-backed behavior shape:

```python
def test_repository_ensures_and_deletes_user_service_roles(db_session: Session) -> None:
    now = datetime.now(UTC)
    repository = IntentRoutingRepository(db_session)
    service_id = "svc-c2-repository"
    user_id = "user-c2-repository"
    # Create service and user, then call ensure twice.
    # Assert duplicate returns the same persisted primary key.
    # Assert list_service_member_roles(service_id) contains one role.
    # Delete it with delete_user_service_role and assert get_user_service_role returns None.
```

- [ ] Run failing test:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_account_auth_schema_contract.py -q
```

Expected: fails because repository helpers are missing.

- [ ] Implement repository helpers in `src/intent_routing/db/repositories.py`:
  - `list_admin_users` should search `AdminUser.email_normalized`, `AdminUser.email`, `AdminUser.display_name`, and `AdminUser.user_id` with case-insensitive `LIKE`.
  - `list_service_member_roles` should join `UserServiceRole.user` and order by `AdminUser.email_normalized`, `UserServiceRole.role`.
  - `get_user_service_role` should validate role through `SERVICE_ADMIN_ROLES`.
  - `ensure_user_service_role` should return existing role or create a new one with `assigned_by` and `assigned_at`.
  - `delete_user_service_role` should delete a loaded role record and flush.
- [ ] Run the same command again.

Expected: repository contract and behavior tests pass.

### Task 3: Backend Membership API Success Flow

**Files:**

- Modify: `tests/integration/test_admin_service_rbac_flow.py`
- Modify: `src/intent_routing/api/admin.py`
- Uses repository helpers from Task 2.

**Tests to add first:**

- `test_system_admin_can_search_users_and_grant_revoke_service_roles`

Test shape:

```python
def test_system_admin_can_search_users_and_grant_revoke_service_roles(
    db_session: Session,
) -> None:
    service_id = f"svc-c2-membership-{uuid4().hex}"
    admin_user = f"system-admin-c2-{uuid4().hex}"
    developer_user = f"developer-c2-{uuid4().hex}"
    now = datetime.now(UTC)
    # Create service, system_admin session, and developer user with no service roles.
    # GET /admin/v1/users?query=developer-c2&limit=25 returns developer without secrets.
    # GET /admin/v1/services/{service_id}/members returns [].
    # POST role service_developer returns assignment with assigned_by system admin.
    # GET members returns developer grouped with service_developer.
    # DELETE role returns revoked_by system admin.
    # GET members returns [].
```

- [ ] Run failing test:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_service_rbac_flow.py -q
```

Expected: fails because API behavior is not implemented. If `TEST_DATABASE_URL` is unset, pytest skips this file under its existing skip marker; record that integration verification is not executed locally.

- [ ] Implement models in `src/intent_routing/api/admin.py`:
  - `AdminUserLookupResponse`
  - `ServiceMemberRoleResponse`
  - `ServiceMemberResponse`
  - `ServiceRoleGrantRequest`
  - `ServiceRoleGrantResponse`
  - `ServiceRoleRevokeResponse`
- [ ] Implement response helpers:
  - `_admin_user_lookup_response(user)`
  - `_service_member_responses(role_rows)`
  - `_service_role_grant_response(role)`
  - `_service_role_revoke_response(role, revoked_by, revoked_at)`
- [ ] Implement endpoints:
  - `GET /users`
  - `GET /services/{service_id}/members`
  - `POST /services/{service_id}/members/{user_id}/roles`
  - `DELETE /services/{service_id}/members/{user_id}/roles/{role}`
- [ ] Require `_require_system_admin(context)` for all four C-2 endpoints.
- [ ] Check target Service exists before listing/granting/revoking; return existing 404 envelope for missing Service.
- [ ] Check target user exists and is active before grant; return existing invalid/not-found behavior chosen by tests.
- [ ] Run the same integration command again.

Expected: success-flow grant/revoke test passes when `TEST_DATABASE_URL` is configured.

### Task 4: Backend Negative Authorization Tests

**Files:**

- Modify: `tests/integration/test_admin_service_rbac_flow.py`
- Modify: `tests/unit/test_admin_auth_context.py`
- Modify: `src/intent_routing/api/admin.py` only if Task 3 did not centralize access checks.

**Tests to add first:**

- `test_non_system_admin_cannot_grant_or_revoke_service_roles`
- `test_c2_membership_endpoints_reject_trusted_headers_without_session_cookie`

Test behavior:

- A `service_owner`, `service_developer`, `service_operator`, and `auditor` with membership on the target Service all receive `403 SERVICE_SCOPE_DENIED` for POST and DELETE.
- Trusted headers without a valid `irt_admin_session` cookie receive `401 AUTHENTICATION_FAILED`.
- With a valid session cookie and conflicting trusted headers, the session actor is used.

Use existing helper patterns from `test_me_services_returns_session_accessible_services` and `test_session_cookie_takes_precedence_over_trusted_headers`.

- [ ] Run failing tests:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_auth_context.py -q
uv run pytest tests/integration/test_admin_service_rbac_flow.py -q
```

Expected: new negative tests fail until endpoints use session-derived context and `_require_system_admin`.

- [ ] Ensure every C-2 endpoint depends on `require_admin_context` or `require_admin_session_context` according to the endpoint need, and does not read trusted headers directly.
- [ ] Run the same commands again.

Expected: unit tests pass; integration tests pass when `TEST_DATABASE_URL` is configured.

### Task 5: `/me/services` Scope Reflection Tests

**Files:**

- Modify: `tests/integration/test_admin_service_rbac_flow.py`
- Modify: `src/intent_routing/api/admin.py` only if grant/revoke does not update persisted roles correctly.
- Modify: `src/intent_routing/db/repositories.py` only if repository deletion leaves stale rows.

**Tests to add first:**

- `test_me_services_reflects_role_grant_and_revoke_from_membership_api`

Behavior:

- Create `system_admin` session and target developer session.
- Developer initially sees `[]` from `/admin/v1/me/services`.
- `system_admin` grants `service_developer` through POST.
- Developer sees exactly the granted Service and role from `/admin/v1/me/services`.
- `system_admin` revokes the role through DELETE.
- Developer sees `[]` again.
- Developer still receives `403 SERVICE_SCOPE_DENIED` when directly calling the revoked Service catalog path.

- [ ] Run failing test:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_service_rbac_flow.py -q
```

Expected: fails until grant/revoke writes and deletes `user_service_roles` correctly.

- [ ] Fix only the minimal repository/API behavior needed for persisted scope to refresh through session context.
- [ ] Run the same command again.

Expected: `/me/services` reflects grant and revoke.

### Task 6: Backend Audit Tests

**Files:**

- Modify: `tests/integration/test_admin_service_rbac_flow.py`
- Modify: `src/intent_routing/api/admin.py`

**Tests to add first:**

- `test_service_membership_grant_and_revoke_write_audit_events`

Expected audit fields:

- Grant event:
  - `event_type == "service_membership.role_granted"`
  - `actor_id == system_admin_user`
  - `service_id == target service`
  - `target_type == "user_service_role"`
  - `target_id == f"{developer_user}:service_developer"`
  - `after_state` includes `user_id`, `service_id`, `role`, `assigned_by`, `assigned_at`
- Revoke event:
  - `event_type == "service_membership.role_revoked"`
  - `actor_id == system_admin_user`
  - `before_state` includes previous assignment
  - `after_state` includes `user_id`, `service_id`, `role`, `revoked_by`, `revoked_at`

- [ ] Run failing test:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_service_rbac_flow.py -q
```

Expected: fails until audit rows are inserted.

- [ ] Insert audit logs in grant/revoke endpoints with `repository.insert_audit_log(...)`.
- [ ] Do not include secrets or password/session fields in audit state.
- [ ] Use `datetime.now(UTC)` once per request for assignment/revoke and audit `created_at`.
- [ ] Run the same command again.

Expected: audit event assertions pass.

### Task 7: Frontend API Types And Service Wrapper Tests

**Files:**

- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`

**Tests to add first:**

- Add imports for:
  - `listAdminUsers`
  - `listServiceMembers`
  - `grantServiceRole`
  - `revokeServiceRole`
- Add `it('uses C-2 membership endpoints without trusted headers', async () => { ... })`.

Test shape:

```ts
await listAdminUsers({ query: 'developer@example.com' });
await listServiceMembers('svc/admin');
await grantServiceRole('svc/admin', 'user/a', { role: 'service_developer' });
await revokeServiceRole('svc/admin', 'user/a', 'service_developer');

expect(requestMock).toHaveBeenNthCalledWith(1, '/users', {
  method: 'GET',
  params: { query: 'developer@example.com', limit: 25 },
});
expect(requestMock).toHaveBeenNthCalledWith(2, '/services/svc%2Fadmin/members', {
  method: 'GET',
});
expect(requestMock).toHaveBeenNthCalledWith(
  3,
  '/services/svc%2Fadmin/members/user%2Fa/roles',
  { method: 'POST', data: { role: 'service_developer' } },
);
expect(requestMock).toHaveBeenNthCalledWith(
  4,
  '/services/svc%2Fadmin/members/user%2Fa/roles/service_developer',
  { method: 'DELETE' },
);
for (const [, options] of requestMock.mock.calls as Array<[string, Record<string, unknown>]>) {
  expect(options).not.toHaveProperty('headers');
}
```

- [ ] Run failing test:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts
```

Expected: fails because service wrappers and types do not exist.

- [ ] Add API types:
  - `ServiceRole = 'service_owner' | 'service_developer' | 'service_operator' | 'auditor'`
  - `AdminUserLookup`
  - `ServiceMemberRole`
  - `ServiceMember`
  - `ServiceRoleGrantRequest`
  - `ServiceRoleGrantResponse`
  - `ServiceRoleRevokeResponse`
- [ ] Add wrappers in `adminServices.ts` using existing `servicePath` and `encodeURIComponent`.
- [ ] Run the same command again.

Expected: frontend service wrapper tests pass and no request call contains `headers`.

### Task 8: Frontend Session Role Helper Tests

**Files:**

- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`

**Tests to add first:**

- `it('allows only system admins to manage service memberships in C-2 baseline', () => { ... })`
- Extend the existing legacy header test to assert `canManageServiceMembers(session) === false`.

Expected helper:

```ts
export const canManageServiceMembers = (session: AdminSession) =>
  session.globalRoles.includes('system_admin');
```

- [ ] Run failing test:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/models/adminSession.test.ts
```

Expected: fails because `canManageServiceMembers` is not exported.

- [ ] Add `canManageServiceMembers` to `adminSession.ts`.
- [ ] Do not allow `service_owner` in this helper for baseline C-2.
- [ ] Run the same command again.

Expected: session helper tests pass.

### Task 9: Frontend Membership Helper Tests

**Files:**

- Create: `frontend/intent-routing-console/src/pages/Services/serviceMembers.test.ts`
- Create: `frontend/intent-routing-console/src/pages/Services/serviceMembers.ts`

**Tests to add first:**

- `serviceRoleOptions` contains exactly `service_owner`, `service_developer`, `service_operator`, and `auditor`.
- `toServiceRoleGrantRequest` trims and validates selected role.
- `toServiceRoleGrantRequest` rejects blank user ID.
- `toServiceRoleGrantRequest` rejects invalid roles.
- `memberRowsForTable` flattens members into stable rows by `user_id:role`.
- `shouldClearMembershipState` returns true when selected Service changes.

Implementation shape:

```ts
export const serviceRoleOptions = [
  { label: 'service_owner', value: 'service_owner' },
  { label: 'service_developer', value: 'service_developer' },
  { label: 'service_operator', value: 'service_operator' },
  { label: 'auditor', value: 'auditor' },
] satisfies Array<{ label: API.ServiceRole; value: API.ServiceRole }>;
```

- [ ] Run failing test:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/pages/Services/serviceMembers.test.ts
```

Expected: fails because helper file does not exist.

- [ ] Implement helper functions only; do not edit React UI yet.
- [ ] Run the same command again.

Expected: helper tests pass.

### Task 10: Frontend Membership Panel UI

**Files:**

- Create: `frontend/intent-routing-console/src/pages/Services/ServiceMembershipPanel.tsx`
- Modify: `frontend/intent-routing-console/src/pages/Services/index.tsx`
- Uses helpers from `frontend/intent-routing-console/src/pages/Services/serviceMembers.ts`
- Uses wrappers from `frontend/intent-routing-console/src/services/adminServices.ts`
- Uses `canManageServiceMembers` from `frontend/intent-routing-console/src/models/adminSession.ts`

**UI requirements:**

- Render below the selected Service details on `/services`.
- Load members when `selectedService.service_id` changes.
- Clear selected user, selected role, search options, and previous member rows when selected Service changes.
- User search:
  - Ant Design `Select showSearch`
  - Calls `listAdminUsers({ query, limit: 25 })`
  - Shows email, display name, and status
  - Disabled when `canManageServiceMembers(session)` is false
- Grant form:
  - Role `Select` from `serviceRoleOptions`
  - Submit calls `grantServiceRole(selectedService.service_id, selectedUserId, { role })`
  - On success reloads members and calls `restoreSession()` so `/me/services` scope can refresh for current admin where relevant
- Member table:
  - Columns: user, email, status, role, assigned_by, assigned_at, action
  - Uses compact `Table` or ProTable-style density
  - No fake server pagination and no fake live polling
- Revoke:
  - Use `ConfirmActionButton` or `Modal.confirm`
  - Calls `revokeServiceRole(selectedService.service_id, user_id, role)`
  - On success reloads members and calls `restoreSession()`
- Unauthorized state:
  - Display read-only membership list if list endpoint is allowed only for `system_admin`; if endpoint returns 403, show an Ant Design `Alert` saying membership management requires `system_admin`.
  - Disable grant/revoke controls for non-system-admins.
- Remove only the C-2 `FutureFeatureNotice`; keep any C-3 notices unchanged.

- [ ] Run narrow frontend tests before UI edit:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts src/pages/Services/serviceMembers.test.ts
```

Expected: all pass before UI wiring.

- [ ] Implement `ServiceMembershipPanel.tsx`.
- [ ] Modify `Services/index.tsx`:
  - Import `ServiceMembershipPanel`.
  - Import `canManageServiceMembers`.
  - Remove the current C-2 `FutureFeatureNotice`.
  - Render `<ServiceMembershipPanel selectedService={selectedService} canManage={canManageServiceMembers(session)} onMembershipChanged={restoreSession} />` directly after `Selected Service`.
- [ ] Run frontend typecheck:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm typecheck
```

Expected: TypeScript passes.

### Task 11: Docs Contract Tests

**Files:**

- Modify: `tests/unit/test_admin_ui_handbook_docs_contract.py`
- Modify: `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`

**Tests to add first:**

- Extend `test_admin_ui_v04_records_authorization_first_onboarding_flow` or add `test_admin_ui_v04_records_c2_membership_contract`.

Expected strings:

- `GET /admin/v1/users`
- `GET /admin/v1/services/{service_id}/members`
- `POST /admin/v1/services/{service_id}/members/{user_id}/roles`
- `DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}`
- `service_membership.role_granted`
- `service_membership.role_revoked`
- `system_admin`
- `service_owner delegation`
- `irt_admin_session`
- `Do not send \`X-Admin-Token\``

- [ ] Run failing docs contract test:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py -q
```

Expected: fails until handbook documents the C-2 contract.

- [ ] Update docs:
  - `ONBOARDING_FLOW.md`: mark C-2 as implemented once code is complete; before code completion, describe it as the C-2 implementation target.
  - `PATTERN_KIT.md`: add membership API/UI constraints under authorization-first onboarding and API rules.
  - Mention `service_owner` delegation as a future increment, not baseline behavior.
- [ ] Run the same command again.

Expected: docs contract passes.

### Task 12: Forbidden Pattern And Regression Verification

**Files:**

- No new source changes expected unless verification finds a violation.

- [ ] Run backend unit verification:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_auth_context.py tests/unit/test_admin_auth_api_contract.py tests/unit/test_account_auth_schema_contract.py tests/unit/test_admin_ui_handbook_docs_contract.py -q
```

Expected: all pass.

- [ ] Run backend integration verification:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_account_auth_api.py tests/integration/test_admin_service_rbac_flow.py -q
```

Expected: all pass when `TEST_DATABASE_URL` points at a safe test database. If not configured, report as unverified rather than claiming integration success.

- [ ] Run frontend unit verification:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts src/pages/Services/serviceMembers.test.ts
```

Expected: all pass.

- [ ] Run frontend typecheck:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm typecheck
```

Expected: TypeScript passes.

- [ ] Run forbidden-pattern scan:

```bash
cd /home/haua/workspace/AiIntentRouting
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/pages/Services frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/models/adminSession.ts frontend/intent-routing-console/config/config.ts
```

Expected: no implementation matches. Documentation references are allowed only when explicitly stating normal browser UI must not send trusted headers.

- [ ] Optional local stack manual QA preflight:

```bash
cd /home/haua/workspace/AiIntentRouting
./scripts/run_local_dev_stack.sh
```

Expected: stack starts. If Alembic/local DB state blocks startup, record exact failure and keep manual QA unverified.

## Complete Verification Command List

Backend unit:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_auth_context.py tests/unit/test_admin_auth_api_contract.py tests/unit/test_account_auth_schema_contract.py tests/unit/test_admin_ui_handbook_docs_contract.py -q
```

Backend integration:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_account_auth_api.py tests/integration/test_admin_service_rbac_flow.py -q
```

Frontend unit:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts src/pages/Services/serviceMembers.test.ts
```

Frontend typecheck:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm typecheck
```

Forbidden-pattern scan:

```bash
cd /home/haua/workspace/AiIntentRouting
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/pages/Services frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/models/adminSession.ts frontend/intent-routing-console/config/config.ts
```

Optional local stack:

```bash
cd /home/haua/workspace/AiIntentRouting
./scripts/run_local_dev_stack.sh
```

## Acceptance Criteria

- `system_admin` can search users, list selected Service members, grant Service roles, and revoke Service roles.
- Non-`system_admin` users cannot grant or revoke roles in baseline C-2.
- `/me/services` reflects role grant and revoke through persisted `user_service_roles`.
- Grant and revoke write append-only audit events with authenticated actor, target user, role, and Service ID.
- The `/services` page has a real selected-Service membership panel.
- Frontend uses Umi `request` and relies on `irt_admin_session` cookie.
- Frontend C-2 wrappers do not send `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, `X-Service-Scope`, `Authorization: Bearer`, or custom auth headers.
- React Query and axios are not introduced.
- No baseline migration is added for `user_service_roles`.
- `service_owner` delegation remains documented as future.

## Remaining Risks

- Integration verification depends on `TEST_DATABASE_URL`; without it, backend grant/revoke behavior remains unverified locally.
- The existing local stack may still be blocked by Alembic/local DB revision mismatch noted in the 2026-07-08 C-2 plan.
- Listing members as `system_admin`-only may be product-safe but less convenient for future `service_owner` workflows; owner delegation needs a separate approved decision and guardrail tests.
- User search over all Admin users is appropriate for `system_admin`, but should be revisited before owner delegation to avoid exposing unrelated users to Service owners.
