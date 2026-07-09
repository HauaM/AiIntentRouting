# Admin UI C-2 Service Membership, Roles, And Developer Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define and then implement the C-2 contract that lets authorized admins assign Service-scoped roles, keeps `/me/services` server-derived, and proves developers/operators/auditors can access only their assigned Services.

**Architecture:** Build on the existing account-session and service-scoped RBAC milestone instead of reintroducing browser-trusted headers. The existing `user_service_roles` table is sufficient for the first C-2 membership model; C-2 adds API endpoints, repository helpers, audit events, Admin UI role-management flows, and authorization matrix tests. C-3 runtime setup and API-key scope stays informational/future only.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy ORM, Alembic, pytest, React 18, TypeScript, Umi Max 4, Ant Design 5, Ant Design ProComponents, Vitest, Umi `request`, `irt_admin_session` HttpOnly cookie.

---

## Scope Of This Session

This document is the deliverable for the current session. No backend, DB,
frontend, test, or ADR implementation code is part of this session.

Default plan path accepted:

- `docs/superpowers/plans/2026-07-08-admin-ui-c2-service-membership-roles.md`

## Approved Direction

User approval recorded on 2026-07-08 with `추천안 승인`:

- ADR path: update
  `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
  instead of creating a new C-2 ADR.
- UI placement: add the first C-2 membership controls as a selected-Service
  panel inside `/services`.
- Owner delegation: C-2 baseline allows only `system_admin` to grant/revoke
  Service roles; `service_owner` delegation remains a future increment.
- Implementation remains paused until the user explicitly asks to implement C-2.

## Required Context Read

- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
- `docs/AdminUI_Handbook/v04/SETUP_GUIDE.md`
- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md`
- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
- `docs/IntentRouting_PRD_v0.2_20260624.md`
- `docs/superpowers/plans/2026-07-08-admin-ui-c1-service-onboarding.md`
- `src/intent_routing/api/admin.py`
- `src/intent_routing/api/admin_dependencies.py`
- `src/intent_routing/security/admin_auth.py`
- `src/intent_routing/db/models.py`
- `src/intent_routing/db/repositories.py`
- `frontend/intent-routing-console/src/models/adminSession.ts`
- `frontend/intent-routing-console/src/pages/Services/index.tsx`
- `frontend/intent-routing-console/src/services/adminServices.ts`
- Supporting existing tests:
  - `tests/integration/test_admin_service_rbac_flow.py`
  - `tests/integration/test_admin_account_auth_api.py`
  - `tests/unit/test_account_auth_schema_contract.py`
  - `tests/unit/test_admin_auth_api_contract.py`
  - `tests/unit/test_admin_auth_context.py`
  - `tests/unit/test_admin_ui_handbook_docs_contract.py`

## Current State

- Current branch: `codex/admin-ui-c1-service-onboarding`.
- Current HEAD observed during planning: `b6f4e64 docs: include service onboarding decision records`.
- C-1 already adds the `/services` Admin UI entry point for `system_admin` Service creation.
- C-1 intentionally keeps Service membership and role assignment as `FutureFeatureNotice`; there is no fake role-assignment state.
- Normal Admin UI requests are documented to use `/auth/login`, `/auth/logout`, `/auth/me`, `/me/services`, Umi `request`, and the `irt_admin_session` HttpOnly cookie.
- Browser UI must not send `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope`.
- Existing DB model already includes:
  - `admin_users`
  - `admin_sessions`
  - `admin_user_roles`
  - `user_service_roles`
- Existing repository already includes:
  - `assign_user_service_role`
  - `list_user_service_roles`
  - `list_service_roles_for_user`
  - `list_services_for_user`
- Existing API already includes:
  - `GET /admin/v1/me/services`
  - `POST /admin/v1/services`
  - service-scoped Intent, example, policy, catalog, test-run, release, runtime log, runtime metric, audit-log paths.
- Existing authorization helpers already prove:
  - `service_developer` can manage assigned Service catalog paths.
  - a service-scoped role on one Service does not grant another Service.
  - session cookies take precedence over trusted headers when both are present.
  - default Admin context rejects trusted headers unless `ADMIN_AUTH_MODE=trusted_headers`.

## C-2 Backend Contract Draft

### Endpoint Candidate Decision

Recommended C-2 endpoint shape:

- `GET /admin/v1/services/{service_id}/members`
- `GET /admin/v1/users?query={email_or_name}&limit=25`
- `POST /admin/v1/services/{service_id}/members/{user_id}/roles`
- `DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}`

Why this shape:

- It keeps membership under the selected Service, matching the C-1 `/services`
  page and the existing `/services/{service_id}/...` API pattern.
- It avoids a global membership screen becoming the first implementation.
- It maps naturally to the existing composite key
  `(user_id, service_id, role)` in `user_service_roles`.
- It lets C-2 add/remove one role at a time without inventing workflow states.

Alternative endpoint candidates to document but not choose by default:

- `PUT /admin/v1/services/{service_id}/members/{user_id}` with a full role list.
  - Better for replace-all semantics.
  - Riskier because one stale UI save can accidentally remove roles.
- `POST /admin/v1/memberships` as a global membership API.
  - Better for central IAM-style administration.
  - Less aligned with C-1 Service onboarding and Service-scoped UI.

### Allowed Roles

Only these Service-scoped roles are assignable through C-2:

| Role | C-2 meaning | Write access | Read access |
| --- | --- | --- | --- |
| `service_owner` | Service-level ownership and future delegation boundary | Catalog work now; member delegation only after ADR/user approval | Assigned Service |
| `service_developer` | Build and validate the Service catalog | Intents, examples, policy versions, catalog versions, test runs | Assigned Service catalog/test results |
| `service_operator` | Operate and inspect runtime behavior | No C-2 mutation | Runtime metrics, masked runtime logs, test results, release history for assigned Service |
| `auditor` | Audit/security review | No business mutation; raw-query decrypt remains audited read | Audit logs, masked runtime logs, security lifecycle, raw query decrypt where already allowed |

`system_admin` remains a global role in `admin_user_roles`, not a Service
membership role.

### Request And Response Schemas

`GET /admin/v1/users?query={email_or_name}&limit=25`

Purpose: search existing Admin users before assigning a Service role. It must
not create users, invite users, reset passwords, or expose password/session
fields.

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

`GET /admin/v1/services/{service_id}/members`

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
        "assigned_at": "2026-07-08T00:00:00Z"
      }
    ]
  }
]
```

`POST /admin/v1/services/{service_id}/members/{user_id}/roles`

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
  "assigned_at": "2026-07-08T00:00:00Z"
}
```

`DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}`

Response:

```json
{
  "service_id": "it-helpdesk",
  "user_id": "developer-1",
  "role": "service_developer",
  "revoked_by": "system-admin-1",
  "revoked_at": "2026-07-08T00:00:00Z"
}
```

### Authorization Rules

Baseline C-2 rule:

- All C-2 membership endpoints require authenticated session context from
  `irt_admin_session`.
- `system_admin` can list, grant, and revoke Service roles for any Service.
- A user with no membership for a Service cannot inspect or mutate that Service.
- `service_developer` can manage only assigned Service Intents, examples,
  policy/catalog versions, and test runs.
- `service_operator` and `auditor` must remain read-only for their assigned
  read paths.
- Browser requests must never provide or rely on trusted actor headers.

Owner delegation rule:

- Do not silently enable Service owner role assignment in C-2 without the ADR
  decision below.
- Recommended implementation if approved:
  - `service_owner` can list members for their assigned Service.
  - `service_owner` can grant/revoke `service_developer`, `service_operator`,
    and `auditor` on their assigned Service.
  - `service_owner` cannot grant/revoke `service_owner`.
  - `service_owner` cannot grant a role on another Service.
  - `service_owner` cannot change their own `service_owner` role.
  - `system_admin` remains the only role that can grant/revoke `service_owner`.

### Role-To-Endpoint Matrix

| Endpoint family | `system_admin` | `service_owner` | `service_developer` | `service_operator` | `auditor` |
| --- | --- | --- | --- | --- | --- |
| `GET /me/services` | all Services | assigned Services | assigned Services | assigned Services | assigned Services |
| `POST /services` | yes | no | no | no | no |
| `GET /services/{sid}/members` | yes | decision-gated | no | no | no |
| grant/revoke Service roles | yes | decision-gated lower roles only | no | no | no |
| Intent create/update | yes | yes | yes | no | no |
| Intent/example list | yes | yes | yes | optional read-only if product approves | no |
| Example create/approve | yes | yes | yes | no | no |
| Policy/catalog version create | yes | yes | yes | no | no |
| Test run create | yes | yes | yes | no | no |
| Test run list/results | yes | yes | yes | yes | no by default |
| Release create/activate/rollback | yes | no in C-2 | no | no | no |
| Release list/active | yes | yes | yes | yes | auditor optional if audit evidence needs it |
| Runtime metrics | yes | optional | no by default | yes | no by default |
| Masked runtime logs | yes | optional | no by default | yes | yes |
| Audit logs/security lifecycle | yes | no by default | no | no | yes |
| Raw-query decrypt | yes | no | no | no | yes, audited |

Any optional read-only expansion must be captured in tests before implementation.

### Audit Events

Use append-only audit logs. Do not store secrets or session tokens in audit
state.

Grant event:

- `event_type`: `service_membership.role_granted`
- `actor_id`: authenticated grantor
- `service_id`: target Service
- `target_type`: `user_service_role`
- `target_id`: `{user_id}:{role}`
- `before_state`: `null` or previous membership snapshot if duplicate handling changes
- `after_state`: `{ "user_id": "...", "service_id": "...", "role": "...", "assigned_by": "...", "assigned_at": "..." }`

Revoke event:

- `event_type`: `service_membership.role_revoked`
- `actor_id`: authenticated revoker
- `service_id`: target Service
- `target_type`: `user_service_role`
- `target_id`: `{user_id}:{role}`
- `before_state`: previous role assignment snapshot
- `after_state`: `{ "user_id": "...", "service_id": "...", "role": "...", "revoked_by": "...", "revoked_at": "..." }`

### Error Cases

| Case | Expected status | Error code | Notes |
| --- | --- | --- | --- |
| Missing/invalid `irt_admin_session` cookie | 401 | `AUTHENTICATION_FAILED` | Normal browser path cannot fall back to actor headers |
| Trusted headers without session on `/me/services` | 401 | `AUTHENTICATION_FAILED` | Existing contract must stay true |
| Non-admin grants/revokes role before owner delegation is approved | 403 | `SERVICE_SCOPE_DENIED` | Do not infer from client headers |
| User has role on Service A but accesses Service B | 403 | `SERVICE_SCOPE_DENIED` | Must be covered for inspect and mutate paths |
| Target Service missing | 404 | existing not-found envelope | Do not leak membership state for missing Service |
| Target user missing or disabled | 404 or 400 | `INVALID_REQUEST` | Choose one response during implementation and document it in tests |
| Role not allowed | 422 | validation error | Pydantic enum/check constraint should reject |
| Duplicate role grant | 200 idempotent or 409 conflict | `INVALID_REQUEST` if conflict | Recommended: idempotent 200 with existing assignment to reduce UI retry friction |
| Revoke missing role | 404 | existing not-found envelope | Avoid pretending a revoke happened |
| Owner tries to grant `service_owner` | 403 | `SERVICE_SCOPE_DENIED` | If owner delegation is approved |
| Owner tries to alter own owner role | 403 | `SERVICE_SCOPE_DENIED` | If owner delegation is approved |

## DB And Schema Impact

### Existing Schema Sufficiency

Existing schema is sufficient for first C-2 implementation:

- `user_service_roles.user_id`
- `user_service_roles.service_id`
- `user_service_roles.role`
- `user_service_roles.assigned_by`
- `user_service_roles.assigned_at`
- primary key: `(user_id, service_id, role)`
- foreign keys to `admin_users` and `services`
- role check constraint:
  - `service_owner`
  - `service_developer`
  - `service_operator`
  - `auditor`
- indexes:
  - `ix_user_service_roles_user_id`
  - `ix_user_service_roles_service_id`

No C-2 migration is required if C-2 only supports grant/revoke of direct
Service-scoped roles.

### Migration Not Needed For C-2 Baseline

Do not add tables for:

- invitations
- teams
- organizations
- temporary delegation
- environment-scoped permissions
- intent-level permissions
- route-key-level permissions
- approval workflow states

Those belong to the fine-grained authorization roadmap in
`docs/security/fine-grained-authorization-todo.md`.

### Migration Needed Only If Product Expands Scope

A migration would be needed only if C-2 is expanded to include any of these:

- membership status such as `pending`, `active`, `revoked`
- revocation history outside append-only audit logs
- role expiration
- invitation flow for users that do not yet exist
- team-derived role inheritance
- environment-specific roles

If that expansion is selected, create a new ADR or update the existing RBAC ADR
before implementation.

### Local Verification Risk From C-1

Carry this risk into C-2:

- C-1 backend integration verification skipped locally when `TEST_DATABASE_URL`
  was not configured.
- C-1 local stack script failed because of an Alembic revision mismatch.
- `scripts/run_local_dev_stack.sh` runs `uv run alembic upgrade head`, so C-2
  manual QA can be blocked until the local DB/migration mismatch is repaired.
- C-2 implementation should include an explicit preflight task:
  - either fix/reset the local dev DB revision state,
  - or record the backend integration and manual stack QA as unverified with
    exact commands and failure output.

## Admin UI Screen And Flow

### Recommended UI Direction

Recommended C-2 UI: add a Service Membership panel inside the existing
`/services` page for the selected Service.

Why:

- C-1 already made `/services` the start of authorization-first onboarding.
- The user has just created or selected a Service there.
- Role assignment is the next C-flow step before Intent Catalog work.
- It avoids introducing a global IAM page before the Service-scoped workflow is
  proven.

UI controls:

- Keep `AdminShell` and `ServiceScopeBar`.
- Keep the existing C-1 Service creation flow.
- Replace the C-2 `FutureFeatureNotice` with a real membership panel only after
  backend contracts exist.
- Use Umi `request`; do not use React Query or axios.
- Use a compact `ProTable` or Ant Design table matching the current `/services`
  density.
- Use `actionRef.current?.reload()` or local reload after grant/revoke.
- Use a user lookup `Select` backed by `GET /admin/v1/users`.
- Use role `Select` or segmented choices from the allowed role enum.
- Use confirmation for revoke.
- Keep C-3 runtime setup/API-key scope as `FutureFeatureNotice`.

### UI Alternatives

Option A: panel in `/services` for selected Service.

- Pros: fastest continuation from C-1, simplest manual QA, less navigation.
- Cons: `/services` can become dense if user search, member table, and create
  Service all live together.
- Recommended for C-2 baseline.

Option B: route `/services/:serviceId/members`.

- Pros: cleaner long-term page ownership and easier deep links.
- Cons: more routing/navigation work; Service ID in route must still be
  validated against `/me/services`.
- Good second step if the panel becomes too large.

Option C: global `/memberships` page.

- Pros: central IAM-style administration.
- Cons: weakest fit with Service-scoped C-flow and easiest to overbuild.
- Do not choose for C-2 baseline unless product explicitly pivots to central IAM.

### C-1 To C-2 Flow

1. `system_admin` logs in with `irt_admin_session`.
2. `system_admin` opens `/services`.
3. `system_admin` creates or selects a Service.
4. Admin UI refreshes `/me/services`.
5. Membership panel loads members for the selected Service.
6. `system_admin` searches an existing active user.
7. `system_admin` grants `service_developer`, `service_operator`, or `auditor`.
8. Audit log records `service_membership.role_granted`.
9. The assigned user logs in.
10. `/me/services` returns only assigned Services.
11. `service_developer` continues to Intent Catalog and validation only inside
    assigned Service.
12. `service_operator` and `auditor` see only their read paths.

## Future Implementation File Structure

Backend:

- Modify: `src/intent_routing/api/admin.py`
  - Add request/response models.
  - Add users lookup endpoint.
  - Add Service members list endpoint.
  - Add role grant endpoint.
  - Add role revoke endpoint.
  - Split authorization helpers where read/write access differs.
- Modify: `src/intent_routing/db/repositories.py`
  - Add `list_admin_users`.
  - Add `list_service_members`.
  - Add `get_user_service_role`.
  - Add `ensure_user_service_role`.
  - Add `delete_user_service_role`.
- Modify only if needed: `src/intent_routing/db/models.py`
  - No schema change expected for baseline C-2.
- No baseline migration expected.

Frontend:

- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
  - Add Admin user lookup and membership response/request types.
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
  - Add `listAdminUsers`.
  - Add `listServiceMembers`.
  - Add `grantServiceRole`.
  - Add `revokeServiceRole`.
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`
  - Verify paths, methods, payloads, and no custom auth headers.
- Modify: `frontend/intent-routing-console/src/models/adminSession.ts`
  - Add `canManageServiceMembers`.
  - Add read-path helpers if pages need role-specific gating.
- Modify: `frontend/intent-routing-console/src/models/adminSession.test.ts`
  - Prove role helpers use server-derived roles only.
- Create: `frontend/intent-routing-console/src/pages/Services/serviceMembers.ts`
  - Keep role/member form normalization outside React.
- Create: `frontend/intent-routing-console/src/pages/Services/serviceMembers.test.ts`
  - Test normalization and allowed role selection.
- Modify: `frontend/intent-routing-console/src/pages/Services/index.tsx`
  - Add membership panel after backend service wrapper tests pass.

Docs/tests:

- Modify: `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`
  - Mark C-2 contract/implementation status accurately.
- Modify: `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`
  - Add C-2 membership UI/API pattern notes after contract approval.
- Modify or add ADR only after user decision.
- Modify: `tests/unit/test_admin_ui_handbook_docs_contract.py`
  - Add C-2 role-assignment contract wording checks.
- Add or modify backend contract tests in:
  - `tests/unit/test_admin_auth_api_contract.py`
  - `tests/integration/test_admin_service_rbac_flow.py`
  - `tests/integration/test_admin_account_auth_api.py`

## TDD Plan

### Task 0: Approval Checkpoint Before Implementation

- [ ] Confirm the ADR update still reflects the approved 2026-07-08 direction:
      existing RBAC ADR updated, `/services` membership panel, and
      `system_admin`-only grant/revoke for C-2 baseline.
- [ ] Confirm local DB/Alembic preflight policy before manual QA.

### Task 1: Backend Contract Tests

- [ ] Add OpenAPI/API contract assertions for:
  - `GET /admin/v1/services/{service_id}/members`
  - `GET /admin/v1/users`
  - `POST /admin/v1/services/{service_id}/members/{user_id}/roles`
  - `DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}`
- [ ] Add tests that response schemas omit:
  - `password_hash`
  - `token_hash`
  - raw session tokens
  - secrets
- [ ] Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_auth_api_contract.py -q
```

Expected before implementation: fails because C-2 endpoints do not exist.

### Task 2: Repository Membership Tests

- [ ] Extend `tests/unit/test_account_auth_schema_contract.py` or add focused
      repository tests proving:
  - allowed roles are accepted.
  - invalid roles are rejected.
  - duplicate grant behavior is defined.
  - revoke removes only the requested `(user_id, service_id, role)`.
  - list members groups roles by user for one Service.
- [ ] Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_account_auth_schema_contract.py -q
```

Expected before implementation: fails only for newly added repository helpers.

### Task 3: Membership API Implementation

- [ ] Add Pydantic models in `src/intent_routing/api/admin.py`.
- [ ] Add repository helpers in `src/intent_routing/db/repositories.py`.
- [ ] Implement user lookup endpoint.
- [ ] Implement members list endpoint.
- [ ] Implement role grant endpoint.
- [ ] Implement role revoke endpoint.
- [ ] Insert audit logs for grant/revoke.
- [ ] Keep implementation on session-derived `AdminContext`.
- [ ] Run backend contract/repository tests from Tasks 1 and 2.

### Task 4: Authorization Matrix Tests

- [ ] Extend `tests/integration/test_admin_service_rbac_flow.py`:
  - `system_admin` grants `service_developer` on Service A.
  - developer logs in and `/me/services` returns only Service A.
  - developer can create/list Intents for Service A.
  - developer receives 403 for Service B.
  - unrelated active user receives no Services and 403 for Service A.
  - operator can read runtime/test/release paths selected for C-2 and cannot
    mutate catalog paths.
  - auditor can read audit/security paths and cannot mutate catalog paths.
- [ ] Add membership audit assertions:
  - `service_membership.role_granted`
  - `service_membership.role_revoked`
  - authenticated actor ID, target user, role, and Service ID are present.
- [ ] Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/integration/test_admin_service_rbac_flow.py -q
```

Expected: may skip unless `TEST_DATABASE_URL` is configured.

### Task 5: Trusted Header Security Tests

- [ ] Add/extend tests proving:
  - browser-style C-2 endpoints reject trusted headers without a session.
  - when session cookie and trusted headers conflict, session identity wins.
  - frontend C-2 service wrappers do not set trusted headers.
- [ ] Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_auth_context.py tests/unit/test_admin_auth_api_contract.py -q
```

Expected after implementation: pass.

### Task 6: Frontend Service Wrapper Tests

- [ ] Add API types for users and Service members.
- [ ] Add tests in `frontend/intent-routing-console/src/services/adminServices.test.ts`.
- [ ] Verify wrapper calls:
  - `GET /users`
  - `GET /services/{sid}/members`
  - `POST /services/{sid}/members/{userId}/roles`
  - `DELETE /services/{sid}/members/{userId}/roles/{role}`
- [ ] Verify no wrapper passes custom auth headers.
- [ ] Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts
```

Expected before implementation: fails because wrappers do not exist.

### Task 7: Admin Session Helper Tests

- [ ] Add `canManageServiceMembers`.
- [ ] Add read-path helpers only for pages that need them.
- [ ] Prove `system_admin` can manage memberships.
- [ ] Prove `service_owner` behavior matches the approved ADR decision.
- [ ] Prove `service_developer`, `service_operator`, and `auditor` cannot manage
      memberships.
- [ ] Prove no helper reads legacy/trusted header values.
- [ ] Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/models/adminSession.test.ts
```

Expected before implementation: fails because helpers do not exist.

### Task 8: Page/Form Helper Tests

- [ ] Create `serviceMembers.ts` helper tests before React UI changes.
- [ ] Test:
  - blank user selection is rejected.
  - blank role is rejected.
  - only allowed Service roles are emitted.
  - self-owner mutation is blocked in UI only if owner delegation is approved.
  - helper does not create fake user or fake pagination state.
- [ ] Run:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/pages/Services/serviceMembers.test.ts
```

Expected before implementation: fails because helper file does not exist.

### Task 9: Services Page Membership Panel

- [ ] Replace the C-2 `FutureFeatureNotice` with a real membership panel only
      after backend contract wrappers pass.
- [ ] Keep C-3 runtime setup/API-key scope as informational/future.
- [ ] Use server-derived selected Service from `session.services`.
- [ ] Disable membership controls if `canManageServiceMembers` is false.
- [ ] Use confirmation on revoke.
- [ ] Refresh members after grant/revoke.
- [ ] Do not add React Query, axios, fake server pagination, fake live polling,
      or invented workflow states.

### Task 10: Docs And ADR

- [ ] Apply the user-approved ADR decision.
- [ ] Update `ONBOARDING_FLOW.md` with accurate C-2 contract/implementation
      status.
- [ ] Update `PATTERN_KIT.md` with membership API/UI constraints.
- [ ] Add docs contract tests for C-2 wording.
- [ ] Run:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py -q
```

Expected after docs update: pass.

### Task 11: Final Verification

Backend:

```bash
cd /home/haua/workspace/AiIntentRouting
uv run pytest tests/unit/test_admin_auth_context.py tests/unit/test_admin_auth_api_contract.py tests/unit/test_account_auth_schema_contract.py -q
uv run pytest tests/integration/test_admin_account_auth_api.py tests/integration/test_admin_service_rbac_flow.py -q
```

Frontend:

```bash
cd /home/haua/workspace/AiIntentRouting/frontend/intent-routing-console
corepack pnpm test:unit -- src/services/adminServices.test.ts src/models/adminSession.test.ts src/pages/Services/serviceMembers.test.ts
corepack pnpm typecheck
```

Forbidden-pattern scan:

```bash
cd /home/haua/workspace/AiIntentRouting
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/pages/Services frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/models/adminSession.ts frontend/intent-routing-console/config/config.ts
```

Expected: no frontend implementation matches. Documentation references to
forbidden headers are allowed only when they explicitly say not to use them from
normal browser UI requests.

Local stack:

```bash
cd /home/haua/workspace/AiIntentRouting
./scripts/run_local_dev_stack.sh
```

Expected: pass only after the C-1 Alembic/local DB mismatch is resolved.

## Security And Authorization Validation

C-2 cannot be accepted unless tests prove all of these:

- `/me/services` returns only server-derived Service scope for non-system-admins.
- `system_admin` sees all Services.
- `service_developer` can manage assigned Service Intents/examples/policy
  versions/catalog versions/test runs.
- `service_developer` cannot inspect or mutate another Service.
- `service_operator` and `auditor` have read-only paths matching the role matrix.
- a user with no Service membership cannot inspect or mutate a Service.
- normal Admin UI C-2 requests use `irt_admin_session` cookie and Umi `request`.
- normal Admin UI C-2 requests do not send trusted actor headers.
- trusted headers without a session do not unlock `/me/services`.
- conflicting trusted headers do not override a valid session cookie.
- audit events use authenticated session actor identity.

## Manual QA Scenarios

Prerequisite:

- Local stack starts successfully, or backend/API verification is run against a
  configured local test DB with `TEST_DATABASE_URL`.
- Known test accounts exist:
  - one `system_admin`
  - one developer user without initial roles
  - one operator user without initial roles
  - one auditor user without initial roles
  - one unrelated user without membership

Scenario 1: `system_admin` adds roles.

1. Log in as `system_admin`.
2. Open `/services`.
3. Create or select Service `c2-helpdesk`.
4. Add developer as `service_developer`.
5. Add operator as `service_operator`.
6. Add auditor as `auditor`.
7. Confirm member table shows all three users and roles.
8. Open Audit Logs as an allowed auditor/system admin and confirm
   `service_membership.role_granted` events.

Scenario 2: developer sees only assigned Service.

1. Log out.
2. Log in as developer.
3. Confirm Service picker contains `c2-helpdesk` only.
4. Open Intent Catalog for `c2-helpdesk`.
5. Create/update an Intent.
6. Run or inspect validation/test-run flow.
7. Attempt direct URL/API access for another Service.
8. Confirm 403 and no leaked data.

Scenario 3: unrelated user is blocked.

1. Log in as unrelated user.
2. Confirm `/me/services` returns an empty list.
3. Attempt direct URL/API access to `c2-helpdesk`.
4. Confirm 403 for inspect/mutate paths.

Scenario 4: operator read path.

1. Log in as operator.
2. Confirm Service picker contains `c2-helpdesk`.
3. Confirm runtime metrics/logs and selected test/release read paths load.
4. Confirm catalog mutation buttons are hidden or disabled.
5. Attempt direct catalog mutation API.
6. Confirm 403.

Scenario 5: auditor read path.

1. Log in as auditor.
2. Confirm Service picker contains `c2-helpdesk`.
3. Confirm audit/security read paths load.
4. Confirm business mutation buttons are hidden or disabled.
5. If raw query decrypt is exercised, provide a reason and confirm audit event.
6. Attempt direct catalog mutation API.
7. Confirm 403.

Scenario 6: revoke role.

1. Log in as `system_admin`.
2. Revoke developer `service_developer` role.
3. Confirm audit event `service_membership.role_revoked`.
4. Log in as developer.
5. Confirm `c2-helpdesk` is no longer returned by `/me/services`.

## ADR Judgment

### Current Assessment

C-2 touches authorization, API contract, DB schema boundaries, and core
onboarding workflow. It meets the ADR Trigger.

Existing ADR coverage:

- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
  already accepts account auth, sessions, Service membership records, and
  Service-scoped role assignments.
- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md` already
  accepts C-1/C-2/C-3 authorization-first onboarding.

Recommendation:

- Update the existing 2026-07-06 RBAC ADR for the C-2 API and owner-delegation
  boundary instead of creating a new ADR, unless the user chooses to make
  owner delegation a separate architectural decision.

### Human Decision Protocol: ADR Path

1. Related requirement/spec ID

- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
- `docs/adr/2026-07-08-authorization-first-admin-ui-onboarding.md`
- `docs/IntentRouting_PRD_v0.2_20260624.md`, sections `4. 주요 사용자`,
  `5.1 서비스 온보딩 흐름`, and `9.3 관리 사용자 권한`
- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`, section
  `C-2: Service Membership, Roles, And Developer Validation`

2. Why this decision is needed now

- C-2 turns Service membership from seeded/test data into a user-facing Admin
  API and UI contract. The team must decide whether this is an update to the
  existing accepted RBAC decision or a new decision record.

3. Plain explanation for beginners

- An ADR is the project's memory for important technical choices. C-2 decides
  who can give users access to a Service and which API shape the UI will call.
  Future developers need to know whether this is just the next step of the
  existing RBAC design or a separate new policy.

4. Options A/B/C

- A: Update the existing RBAC ADR.
- B: Create a new C-2 Service Membership ADR.
- C: Do not change ADRs now; keep only this plan until implementation starts.

5. Pros, cons, and impact scope

- A pros: avoids duplicate ADRs, fits the accepted account/RBAC direction,
  lower documentation overhead.
- A cons: the existing ADR becomes broader and must clearly separate accepted
  baseline from future owner delegation.
- A impact: docs only; no schema/code effect by itself.
- B pros: creates a crisp record for membership API, owner delegation, and
  audit event decisions.
- B cons: can duplicate the existing RBAC ADR and create two places to maintain.
- B impact: docs only; useful if owner delegation is approved now.
- C pros: fastest path to implementation after plan approval.
- C cons: weaker audit trail for an auth/API/schema/core-workflow decision.
- C impact: leaves C-2 implementation dependent on this plan only.

6. Recommended option and why

- Recommended: A. C-2 is the planned next slice of the accepted account auth
  and Service RBAC ADR. Updating that ADR is enough unless owner delegation is
  expanded beyond the current Service-level RBAC milestone.

7. Safe default if the user does not answer

- Keep implementation paused. If implementation is later requested without a
  fresh answer, use A and update the existing RBAC ADR before C-2 code changes.

8. Newly introduced project terms

- Service membership: a persisted relationship that says a user has one or more
  roles on a specific Service.
- Owner delegation: allowing `service_owner` to grant lower roles inside their
  own Service.
- Trusted headers: bootstrap/internal automation headers such as
  `X-Admin-Token`; normal browser UI must not send them.
- Service-scoped RBAC: role-based access control where roles apply to one
  Service, not every Service.

User can answer: `A로 진행`, `B로 진행`, `C로 진행`, `보류`, or `추천안 승인`.

### Human Decision Protocol: UI Placement

1. Related requirement/spec ID

- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md`, C-1 and C-2 sections
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md`, `Authorization-first onboarding`
- `docs/superpowers/plans/2026-07-08-admin-ui-c1-service-onboarding.md`

2. Why this decision is needed now

- C-2 role assignment must attach to the C-1 Service onboarding flow without
  overbuilding a global IAM console.

3. Plain explanation for beginners

- The team must decide where users will click to add developers/operators/
  auditors to a Service.

4. Options A/B/C

- A: Add membership panel inside `/services`.
- B: Add a dedicated `/services/:serviceId/members` page.
- C: Add a global `/memberships` page.

5. Pros, cons, and impact scope

- A pros: fastest, directly follows C-1, easiest QA.
- A cons: Services page can get crowded.
- A impact: modifies existing C-1 page only.
- B pros: cleaner long-term page and deep-link ownership.
- B cons: more routing and scope validation work.
- B impact: new route/page plus navigation.
- C pros: central administration model.
- C cons: least aligned with authorization-first Service onboarding and easiest
  to overbuild.
- C impact: new global workflow and more product decisions.

6. Recommended option and why

- Recommended: A for C-2 baseline. Move to B later if the panel becomes too
  large.

7. Safe default if the user does not answer

- Keep implementation paused. If implementation is later requested without a
  fresh answer, use A because it is the smallest continuation from C-1.

8. Newly introduced project terms

- Membership panel: a contained section in `/services` that lists and edits
  users assigned to the selected Service.
- Deep link: a URL that opens a specific Service members page directly.
- Global IAM: a central identity/access management area not scoped to one
  Service page.

User can answer: `A로 진행`, `B로 진행`, `C로 진행`, `보류`, or `추천안 승인`.

### Human Decision Protocol: Owner Delegation

1. Related requirement/spec ID

- `docs/IntentRouting_PRD_v0.2_20260624.md`, sections `4. 주요 사용자` and
  `9.3 관리 사용자 권한`
- `docs/adr/2026-07-06-account-auth-service-rbac-to-fine-grained-authorization.md`
- `docs/security/fine-grained-authorization-todo.md`, listed fine-grained
  authorization follow-up items

2. Why this decision is needed now

- The user requirement says `system_admin` or a future authorized owner can
  assign Service roles. The team must decide whether owner assignment is in C-2
  now or documented as future.

3. Plain explanation for beginners

- If only system admins can add users, the rule is simple. If Service owners can
  also add users, the product is more convenient but needs extra guardrails so
  owners cannot make themselves global admins or change other Services.

4. Options A/B/C

- A: C-2 allows only `system_admin` to grant/revoke roles; owner delegation is
  future.
- B: C-2 allows `service_owner` to manage lower roles only on their assigned
  Service.
- C: C-2 creates a broader delegation model now.

5. Pros, cons, and impact scope

- A pros: safest and smallest authorization surface.
- A cons: Service teams depend on system admins for every membership change.
- A impact: simplest API, UI, and tests.
- B pros: supports practical owner workflow without full fine-grained auth.
- B cons: needs self-change, cross-Service, and owner-role guardrail tests.
- B impact: moderate backend/UI/test scope.
- C pros: closer to future permission model.
- C cons: risks building a policy engine before workflows prove it.
- C impact: high architecture/schema/product scope, likely new ADR.

6. Recommended option and why

- Recommended: A for first C-2 implementation, with B documented as the next
  owner-delegation increment. This keeps C-2 focused on proving membership,
  roles, and developer validation.

7. Safe default if the user does not answer

- Keep implementation paused. If implementation is later requested without a
  fresh answer, use A.

8. Newly introduced project terms

- Lower roles: roles below `service_owner`, such as `service_developer`,
  `service_operator`, and `auditor`.
- Self-change guardrail: a rule preventing a user from removing or escalating
  their own critical access.
- Cross-Service guardrail: a rule preventing a Service-scoped user from
  changing membership on another Service.

User can answer: `A로 진행`, `B로 진행`, `C로 진행`, `보류`, or `추천안 승인`.

## Acceptance Criteria For Future C-2 Implementation

- `system_admin` can grant and revoke Service roles through the Admin UI.
- `/me/services` returns only Services derived from persisted membership for
  non-system-admin users.
- `service_developer` can manage Intents, examples, policy/catalog versions,
  and test runs only inside assigned Services.
- `service_operator` and `auditor` have only approved read paths.
- users with no Service membership cannot inspect or mutate Service resources.
- membership grant/revoke writes append audit events.
- frontend uses Umi `request` and `irt_admin_session` cookie.
- frontend does not send trusted actor headers.
- C-3 runtime setup/API key scope remains future/informational.
- local DB/Alembic risk is either resolved or explicitly reported as
  unverified with exact commands.

## Self-Review Checklist

- C-2 backend contract includes endpoint candidates, schemas, allowed roles,
  authorization rules, audit events, and error cases.
- DB section explains that existing schema is enough for baseline C-2 and when
  a migration would become necessary.
- Admin UI section compares `/services` panel, `/services/:serviceId/members`,
  and global `/memberships`.
- TDD plan covers backend tests, frontend service wrapper tests,
  `adminSession` helper tests, page/form helper tests, and docs contract tests.
- Security section covers no-service access, cross-Service denial, and trusted
  header non-use.
- Manual QA covers system admin assignment, developer login, unrelated user
  denial, operator read paths, auditor read paths, and revoke flow.
- ADR judgment follows the Human Decision Protocol.
- No C-3 runtime setup/API-key scope implementation is included.
