# Admin Console v04 Pattern Kit

## Sprint 9 Baseline

- Current state: API-only MVP.
- Sprint 9 decision: Go.
- Sprint 9 scope: Go reassessment and launch evidence closure.
- Admin UI implementation: excluded.
- This kit is a reference implementation for a future Admin UI sprint, not a committed product surface.

## Stack

- React + TypeScript.
- Umi 4 / Ant Design Pro v6 / ProComponents.
- Ant Design token theme.
- Umi `request` for HTTP.
- ProTable `request` prop for list screens.
- `actionRef.current?.reload()` for post-mutation refresh.
- React local state or Umi `useModel`/`initialState` for UI state.
- Account login with the `irt_admin_session` HttpOnly cookie.

Do not add React Query or axios unless a future architecture decision explicitly reverses this rule.

## Viewport Scope

The Admin Console is a desktop web operations console optimized for FHD usage.
Do not design, implement, or verify mobile-specific UX unless explicitly
requested.

Responsive behavior is still required for desktop browser width changes: avoid
clipping, unreadable tables, broken toolbars, and modal/drawer overflow when a
desktop window is narrowed. Treat this as desktop web layout resilience, not as
mobile product support.

Do not add mobile-only navigation, card-list replacements for tables,
touch-first interaction patterns, or phone-viewport acceptance criteria by
default.

## Layout Contract

- Use `AdminShell` as the default page shell.
- Keep a dark fixed sidebar and compact fixed header. The sidebar/nav is the
  only approved dark surface; content panels, dropdowns, alerts, steps, modals,
  drawers, and cards stay on light surfaces.
- Put `ServiceScopeBar` directly below the page title area, not inside another card.
- Use restrained enterprise density: compact tables, small status tags, no marketing hero layout.
- Cards are for contained repeated items or true panels only. Do not nest cards.
- Use wrapping, ellipsis, table overflow, and viewport-bounded floating layers
  for narrowed desktop windows, without converting tables or navigation into
  mobile-specific experiences.

## Phase Model

### Authorization-first onboarding

Admin UI development must use the C flow from
`docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md` as the target product workflow.
This keeps financial closed-network authorization constraints visible before
future C-2 and C-3 work begins.

- C-1 Service onboarding: `system_admin` creates a Service, the Service appears
  through server-derived Service scope, and creation is audited.
- C-2 Service membership and validation: Service roles are assigned before
  developers configure Intents, examples, policy/catalog versions, and test
  runs for assigned Services.
- C-2 Service Membership / Role Assignment UI/API is in implementation scope:
  user search, selected-Service member listing, Service role grant, Service role
  revoke, and post-change scope refresh.
- Baseline C-2 membership administration is accepted for `system_admin` and
  authorized `service_owner`: both can use the selected-Service user lookup,
  list members, grant roles, and revoke roles inside that Service boundary.
- Grant and revoke must write append-only audit events:
  `service_membership.role_granted` and
  `service_membership.role_revoked`.
- C-3 runtime integration and operations: service-scoped API keys, Dify/client
  setup guidance, masked Runtime Logs, and append-only Audit Logs complete the
  onboarding loop.
- Permission and audit requirements are product workflow requirements, not test
  setup. Do not add UI shortcuts that bypass server-derived roles or Service
  scope.

### Central Permission Management

The Permission Management page is the central IAM surface for system administrators.
It may show Admin accounts, global roles, Service roles, sanitized permission audit
events, and derived risk findings. It must not make `users` an authorization source.
Service-scoped role writes continue to use the existing Service membership model.

### Workflow candidate selectors

Admin UI write screens must prefer service-scoped selectors over manual internal
ID entry.

- Intent IDs are manually entered only when creating an Intent.
- Policy versions, catalog versions, test runs, release candidates, rollback
  targets, allowed intents, and allowed route keys must be loaded from Admin API
  candidate/list endpoints.
- Manual internal ID entry is transitional and should be removed once candidate
  endpoints exist.
- Phase 2 governed backend contracts have passed for raw query approval,
  release diff/approval, and masked export.
- Phase 2 action buttons remain disabled until frontend routes, service
  functions, role gates, and UX tests are implemented.

### Phase 0 — Read-first

Implement first:

- Dashboard metrics.
- Intent Catalog list and row detail from list data.
- Runtime Logs with masked query.
- Audit Logs read-only.

No dangerous writes in Phase 0.

### Phase 1 — Current API writes

Only connect currently supported API writes:

- Intent create/update/delete.
- Example create/update/delete/approve.
- Policy/catalog version create.
- Test run create/results.
- Release create/activate/rollback.
- API key create/revoke.

Read the current user's global roles and selected Service roles from `/auth/me` and
`/me/services`. Gate buttons and pages from those server-derived roles, never from
client-supplied actor headers.

Every destructive or operationally dangerous action must go through `ConfirmActionButton` or the same `Modal.confirm` pattern.

### Phase 2 — Backend Implemented, UI Gated

Backend contracts are implemented for:

- Publish pending/approve/reject for release activation.
- Raw query two-person approval.
- Time-limited raw query token.
- Release diff approval workflow.
- Masked runtime log export as CSV or JSONL.

Render these as disabled or informational until the Admin UI adds frontend
routes, service functions, server-derived role gates, and UX tests. Do not use
mock state or fake endpoints to simulate approval progress.

Keep using `FutureFeatureNotice` for unsupported capabilities:

- Server pagination/compound filters/live polling.
- Example reject with reason.

## API Rules

- Base URL: `/admin/v1`.
- Normal Admin UI authentication uses `/auth/login`, `/auth/logout`, `/auth/me`,
  `/me/services`, `withCredentials: true`, and the server-issued
  `irt_admin_session` HttpOnly cookie.
- Service paths: `/services/{service_id}/...`.
- C-2 membership API contract:
  - `GET /admin/v1/users?query={email_or_name}&limit=25`
  - `GET /admin/v1/services/{service_id}/members`
  - `POST /admin/v1/services/{service_id}/members/{user_id}/roles`
  - `DELETE /admin/v1/services/{service_id}/members/{user_id}/roles/{role}`
- Do not send `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or
  `X-Service-Scope` from normal Admin UI requests. Those trusted headers are
  reserved for controlled bootstrap, break-glass, or explicitly configured
  internal automation paths.
- C-2 frontend must not send `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`,
  `X-Service-Scope`, or `Authorization: Bearer` from normal browser Admin UI
  requests.
- Service picker options must come from `GET /me/services`.
- Runtime metrics: `window_hours`.
- Runtime logs: `limit`.
- Runtime log masked field: `query_masked`.
- API key secret copy uses `Secret 보기/복사` and the audited reveal endpoint
  `POST /admin/v1/services/{service_id}/api-keys/{key_id}:reveal`.
- Persisted API keys use encrypted secret material; raw secret is copied only through the audited reveal endpoint and never through inventory or guidance.
- Intent delete: `DELETE /services/{sid}/intents/{intent_id}`.
- Example update: `PATCH /services/{sid}/examples/{example_id}`.
- Example approve: `PATCH /services/{sid}/examples/{example_id}:approve`.
- Example delete: `DELETE /services/{sid}/examples/{example_id}`.
- Release activate/rollback: `POST ...:activate`, `POST ...:rollback`.
- Release diff: `GET /services/{sid}/releases/{release_version}/diff`.
- Release approval workflow: `POST /services/{sid}/publish-requests`,
  `POST /services/{sid}/publish-requests/{request_id}:approve`,
  `POST /services/{sid}/publish-requests/{request_id}:reject`, and
  `POST /services/{sid}/publish-requests/{request_id}:activate`.
- API key lifecycle: `GET /services/{sid}/api-keys`,
  `POST /services/{sid}/api-keys`, and
  `POST /services/{sid}/api-keys/{key_id}:revoke`.
- Runtime setup guidance: `GET /services/{sid}/runtime-setup`. This guidance
  may render `selected_key` metadata and Dify/client templates, but must never
  return or replay the raw `api_key` secret.
- Raw query approval workflow:
  `POST /services/{sid}/runtime-logs/{trace_id}/raw-query-view-requests`,
  `POST /services/{sid}/raw-query-view-requests/{request_id}:approve`,
  `POST /services/{sid}/raw-query-view-requests/{request_id}:reject`, and
  `POST /services/{sid}/raw-query-view-requests/{request_id}:issue-token`.
- Masked export: `POST /services/{sid}/exports`.
- Intent detail: no current `GET /intents/{intent_id}`. Use selected row data from list.

## Current Role Gates

- `system_admin`: all permissions, Service creation, initial service_owner grants, system monitoring.
- `service_owner`: assigned-Service membership, Intent Catalog, Test Runs, Releases, API Keys, Runtime Logs.
- `service_developer`: assigned-Service Intent Catalog and Test Runs writes, Releases read, Runtime Logs read.
- `service_operator`: scoped runtime metrics, runtime log inspection, and audit
  log inspection.
- `auditor`: scoped runtime log inspection, audit log inspection, security
  lifecycle read, raw-query approval/review paths, and masked export.

Organization Directory and Permission Management are system-admin-only. Audit
Logs are not shown to `service_owner` or `service_developer`.

## Visual Tokens

```ts
export const adminUiTokens = {
  colorPrimary: '#1D5A96',
  colorSuccess: '#2F8F5B',
  colorWarning: '#D4920B',
  colorError: '#C0392B',
  colorTextBase: '#1C2733',
  colorBgLayout: '#F4F6F8',
  colorSider: '#0D2438',
  borderRadius: 6,
};
```

Use semantic tags consistently:

- active/confident/pass: green.
- draft/clarify/warning: orange.
- deprecated/fallback/off_topic: gray or blue-gray.
- risk/error/revoke: red.
- future/disabled: gray.
- Render semantic state, environment, severity, gate result, and role badges
  through `StatusTag`. Do not use Ant Design preset `Tag color` values such as
  `blue`, `green`, `red`, `warning`, `processing`, `success`, `error`, or
  `default`.
- Do not add Ant Design `darkAlgorithm`, `color-scheme: dark`, or near-black
  content backgrounds such as `#01021E`, `#050625`, `#17011E`, or similar
  low-luminance navy/purple-black values. If a new dark surface is genuinely
  required, update `docs/THEME_AND_UX_GUIDE_v1.md` and the Admin UI color guard
  test in the same change.
