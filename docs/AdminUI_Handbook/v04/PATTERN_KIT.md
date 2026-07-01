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

Do not add React Query or axios unless a future architecture decision explicitly reverses this rule.

## Layout Contract

- Use `AdminShell` as the default page shell.
- Keep a dark fixed sidebar and compact fixed header.
- Put `ServiceScopeBar` directly below the page title area, not inside another card.
- Use restrained enterprise density: compact tables, small status tags, no marketing hero layout.
- Cards are for contained repeated items or true panels only. Do not nest cards.

## Phase Model

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
- Service paths: `/services/{service_id}/...`.
- Headers:
  - `X-Admin-Token`
  - `X-Actor-Id`
  - `X-Actor-Roles`
  - `X-Service-Scope`
- Runtime metrics: `window_hours`.
- Runtime logs: `limit`.
- Runtime log masked field: `query_masked`.
- Example approve: `PATCH /services/{sid}/examples/{example_id}:approve`.
- Release activate/rollback: `POST ...:activate`, `POST ...:rollback`.
- Intent detail: no current `GET /intents/{intent_id}`. Use selected row data from list.

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
