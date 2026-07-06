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

## Layout Contract

- Use `AdminShell` as the default page shell.
- Keep a dark fixed sidebar and compact fixed header.
- Put `ServiceScopeBar` directly below the page title area, not inside another card.
- Use restrained enterprise density: compact tables, small status tags, no marketing hero layout.
- Cards are for contained repeated items or true panels only. Do not nest cards.

## Phase Model

### Workflow candidate selectors

Admin UI write screens must prefer service-scoped selectors over manual internal
ID entry.

- Intent IDs are manually entered only when creating an Intent.
- Policy versions, catalog versions, test runs, release candidates, rollback
  targets, allowed intents, and allowed route keys must be loaded from Admin API
  candidate/list endpoints.
- Manual internal ID entry is transitional and should be removed once candidate
  endpoints exist.
- Phase 2 governed workflows remain disabled until their backend approval
  contracts pass.

### Phase 0 — Read-first

Implement first:

- Dashboard metrics.
- Intent Catalog list and row detail from list data.
- Runtime Logs with masked query.
- Audit Logs read-only.

No dangerous writes in Phase 0.

### Phase 1 — Current API writes

Only connect currently supported API writes:

- Intent create/update.
- Example create/approve.
- Policy/catalog version create.
- Test run create/results.
- Release create/activate/rollback.
- API key create/revoke.

Read the current user's global roles and selected Service roles from `/auth/me` and
`/me/services`. Gate buttons and pages from those server-derived roles, never from
client-supplied actor headers.

Every destructive or operationally dangerous action must go through `ConfirmActionButton` or the same `Modal.confirm` pattern.

### Phase 2 — Future backend

Render as disabled or informational only:

- Publish pending/approve/reject.
- Raw query two-person approval.
- Time-limited raw query token.
- Release diff approval workflow.
- CSV export.
- Server pagination/compound filters/live polling.
- Example reject with reason.

Use `FutureFeatureNotice` instead of mock state or fake endpoints.

## API Rules

- Base URL: `/admin/v1`.
- Normal Admin UI authentication uses `/auth/login`, `/auth/logout`, `/auth/me`,
  `/me/services`, `withCredentials: true`, and the server-issued
  `irt_admin_session` HttpOnly cookie.
- Service paths: `/services/{service_id}/...`.
- Do not send `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or
  `X-Service-Scope` from normal Admin UI requests. Those trusted headers are
  reserved for controlled bootstrap, break-glass, or explicitly configured
  internal automation paths.
- Service picker options must come from `GET /me/services`.
- Runtime metrics: `window_hours`.
- Runtime logs: `limit`.
- Runtime log masked field: `query_masked`.
- Example approve: `PATCH /services/{sid}/examples/{example_id}:approve`.
- Release activate/rollback: `POST ...:activate`, `POST ...:rollback`.
- Intent detail: no current `GET /intents/{intent_id}`. Use selected row data from list.

## Current Role Gates

- `system_admin`: all Services, service creation, API key lifecycle, release
  create/activate/rollback, emergency operations.
- `service_owner`: scoped Service catalog work and future owner approval flows.
- `service_developer`: scoped Intent Catalog, examples, policy/catalog versions,
  and test runs.
- `service_operator`: scoped runtime metrics and runtime log inspection.
- `auditor`: scoped runtime log inspection, audit log inspection, security
  lifecycle read, and raw-query audited decrypt.

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
