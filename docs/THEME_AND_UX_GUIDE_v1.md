# AiIntentRouting Admin Console — Theme & UX Guide

Status: **canonical / source of truth**. The companion file `AiIntentRouting Admin Console Design Guide.dc.html` (and its standalone export) is a human-facing visual preview only. If the two ever disagree, this document wins.

Audience: system administrators, service developers, service operators, audit/security reviewers, in a closed financial-network environment. This is an operations/audit/catalog-management tool, not a marketing surface.

Stack: React + TypeScript, Umi 4, Ant Design Pro v6, ProComponents, Ant Design theme tokens. Default font: Pretendard.

---

## 1. Design Direction

- **Trust** — calm navy palette, low saturation, consistent alignment. No decorative elements; information itself builds trust.
- **Precision** — IDs, `route_key`, `trace_id`, and similar values are always rendered in monospace and never dimmed to low contrast.
- **Low cognitive load** — compact density by default. Color is used only to carry state meaning, never for decoration.
- **Fast scanning** — table-first layouts, left-aligned text, one unified StatusTag system so the eye stops in a single column.
- **Security-aware UI** — dangerous actions, hidden permissions, and masked data each have distinct, consistent visual treatment.
- **Restraint** — no gradients, no hero sections, no heavy shadows, no high-saturation palettes.

### Honesty Principle (binding rule)
The console must only render UI for server contracts and permission models that actually exist.

- If a backend contract does not exist → do not render an interactive control at all in disguise; use `FutureFeatureNotice`.
- If a backend contract exists but the frontend route, service function, role gate, or UX test are not yet wired → also use `FutureFeatureNotice`.
- Never fabricate working pagination, filters, polling, or write actions to "look complete."

---

## 2. Theme Tokens (Ant Design)

Steel-blue based, low-saturation palette. No purple, no gradients. Success/warning/error use different hues but matched lightness/saturation so no state color visually dominates. State tag text/background pairs and any semantic text placed on white must meet ≥4.5:1 contrast; if a hue token is too light for direct text on white, use a darker text alias or a tinted tag surface.

| Token | Value | Notes |
|---|---|---|
| `colorPrimary` | `#1E4B8F` | primary actions, selected nav |
| `colorSuccess` | `#1E8A5F` | active / pass |
| `colorWarning` | `#B7791F` | clarify / production env badge |
| `colorError` | `#B3261E` | fail / high-risk actions |
| `colorInfo` | `#3D6FA5` | informational accents |
| `colorTextBase` | `#1B1F27` | primary text |
| `colorTextSecondary` (custom, min allowed for caption/disabled) | `#6B7688` | never go lighter than this on white |
| `colorBgLayout` | `#F2F4F7` | app background |
| `colorBgContainer` | `#FFFFFF` | cards, tables, drawers |
| `colorBorder` | `#DCE1E8` | all hairline borders |
| Sidebar background | `#0F1A2E` | AdminShell dark sider |
| `borderRadius` | `6` | tables, cards, buttons |
| `fontFamily` | `'Pretendard', -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif` | |

Density: compact by default (table row height 36px); `middle` allowed for logs/tables on request.

---

## 3. Typography

- Base font: Pretendard, fallback -apple-system / Malgun Gothic / sans-serif.
- Scale: H1 24/700, H2 18/700, Body 14/400, Caption 12/400, Code 13/mono.
- Code-like values (ID, `route_key`, `release_version`, `trace_id`, API key) are always monospace + light background chip.
- Numbers/versions in tables are right-aligned; ordinary text left-aligned.
- Minimum body size 12px; table density never drops below 11px.
- **Caption/secondary/disabled text must never be lighter than `#6B7688` on a white background** (contrast floor 4.5:1). State meaning is always carried by text/icon in addition to color, never by color alone.

---

## 4. Layout

Three-tier structure:
1. Dark Sidebar (`AdminShell`, ~240px) — logo, nav tree, selection state.
2. Compact Header (48px) — user info, notifications, logout.
3. Content — `ServiceScopeBar` pinned directly under the header, then page content.

Rules:
- Content area is not width-capped; tables/cards fill the container (no marketing-style centered columns).
- Page header = title + one-line description + at most one primary action on the right.

---

## 5. Authorization-First Onboarding Flow

This is the core UX of the console: getting a service into a state where it can safely route traffic. Onboarding a new service always follows this order, and each step gates the next on server-confirmed completion (not client-side assumption):

- **C-1 — Service creation.** A `system_admin` registers `service_id`, display name, environment, default threshold preset, and input limit. The new Service appears through the server-derived Service picker / `/me/services` refresh, and creation is recorded as audit evidence. C-2 membership controls remain disabled or informational until role-assignment contracts are wired; do not fake Service roles in C-1.
- **C-2 — Role assignment & validation.** Grant a service-scoped role (operator/developer/etc.) to a user. Server-side validation must pass before proceeding; validation failures are shown inline with the specific cause.
- **C-3 — Key / runtime / audit readiness.** Issue API key, configure runtime integration, confirm masked-log collection has started, confirm audit evidence is being generated. Only after all of C-3 is confirmed is the service "ready for operation."

### Implementation Phases

| Phase | Scope |
|---|---|
| **Phase 0** | Read-first: dashboard metrics, Intent Catalog list/detail from list data, Runtime Logs with masked query, and read-only Audit Logs. No dangerous writes. |
| **Phase 1** | Connect only current Admin API writes: Intent create/update, example create/approve, policy/catalog version create, test run create/results, release create/activate/rollback, and API key create/revoke. Gate from server-derived roles and confirm dangerous actions. |
| **Phase 2** | Governed workflows such as raw-query approval, release diff/approval, masked export, publish approval, and time-limited raw-query token stay disabled/informational until frontend routes, service functions, role gates, and UX tests are complete. |

---

## 6. Common Components

### 6.1 AdminShell
- **Purpose** — provides the console's skeleton; guarantees consistent navigation and context awareness everywhere.
- **Used in** — top-level layout of every authenticated screen.
- **Composition** — dark sidebar (logo, nav tree, selection state), compact header (user info, notifications, logout), content slot.
- **Key props** — `selectedMenuKey`, `collapsed`, `currentUser: {name, serverRole, permissionLevel}`, `serviceScope`, `permissionBadge`.
- **States** — session expired (re-login banner), reduced-permission mode (persistent read-only badge).
- **Permission handling** — menu visibility is derived only from `currentUser.serverRole` combined with the selected `serviceScope` (see §8.1). Hiding is preferred over disabling. Auditors never see write menu items rendered at all.
- **Style** — sidebar `#0F1A2E`; selected item = `colorPrimary` background + white text; header height fixed 48px; hairline borders instead of shadows for separation.
- **Accessibility** — sidebar text contrast ≥4.5:1; menu icons are always paired with a text label (never icon-only).

### 6.2 ServiceScopeBar
- **Purpose** — keeps the current operating scope (service · environment) always visible to prevent acting in the wrong environment.
- **Used in** — pinned directly below the header on every content screen.
- **Composition** — service select dropdown, environment badge, user role badge, secondary info on the right (last sync time, etc).
- **Key props** — `service, environment, role, locked`, `onServiceChange`, `availableServices`.
- **States** — `locked` (single-service accounts show fixed text instead of a picker), loading spinner during switch.
- **Permission handling** — the role value is always "this user's role for the currently selected service," taken from the server response. Switching to production may force a confirm modal or be disabled outright depending on role.
- **Style** — background one shade lighter than content background; environment communicated by color (production=amber, staging=blue, dev=neutral) rendered as pill badges.
- **Accessibility** — environment always carries a text label, never color alone.

### 6.3 ResourceTable (DataTable)
- **Purpose** — the shared way to scan/filter/act on every list-shaped resource: Intents, logs, audit records, releases, test runs.
- **Used in** — Intent Catalog, Runtime/Audit Logs, Releases, API Keys, Test Runs.
- **Composition** — toolbar (search, filters, refresh, primary action), ProTable columns, StatusTag status column, row action menu, and an optional pagination footer only when the current data shape or confirmed server contract supports it.
- **Key props** — `columns, filters, sortable, density('compact'|'middle')`, `rowActions, readOnly, selectable`, `emptyText, permission`, optional `paginationMode: 'none'|'client-array'|'server-contracted'`.
- **States** — loading (skeleton rows), empty (`EmptyState` slot), error (`ErrorState` + retry), no permission (`PermissionState`, columns can be masked).
- **Uncontracted features** — pagination modes, compound filters, or live polling that have no confirmed server contract must never be rendered as if functional. Disable the control or replace it with `FutureFeatureNotice`.
- **Permission handling** — the row-action column itself is not rendered when the user lacks write permission. Audit log tables are always `readOnly`.
- **Style** — 12px header text, no gimmicky uppercase/letter-spacing overrides; hover row `#F7F9FC`; compact density (36px row height) by default.
- **Accessibility** — code-like columns (IDs, route_key) use monospace + left alignment; long values truncate with a tooltip/copy affordance for the full value.

### 6.4 DetailDrawer
- **Purpose** — shows a resource's full context (summary, metadata, history, risk info) without leaving the list.
- **Used in** — row detail action on every `ResourceTable`.
- **Composition** — header (title + StatusTag + close), summary section, metadata key-value list, change-history timeline, related-ID section, optional risk/security section, footer action area.
- **Key props** — `width (480–560px default)`, `sections: string[]`, `showHistory, showRiskInfo`, `actions, readOnly`.
- **States** — loading (per-section skeleton), partial data (inline `EmptyState` for that section only).
- **Permission handling** — the risk/security section is hidden entirely (not just empty) for roles below audit/security tier. Runtime Log detail only ever shows the masked query — there is no raw-query button anywhere in this drawer (see §8.2).
- **Style** — right-side slide-in, 0.35 opacity overlay, 24px section spacing with hairline dividers, fixed-width left-aligned labels for key-value rows.
- **Accessibility** — ESC closes, focus trap, long values wrap (no truncation — this is the detail view).

### 6.5 StatusTag
- **Purpose** — one unified visual vocabulary for state across the whole console.
- **Used in** — every table status column, `DetailDrawer` header, dashboard cards.
- **Composition** — pill background + text label + icon (risk/error tiers only).
- **Key props** — `status: 'confident'|'clarify'|'fallback'|'off_topic'|'risk'|'unauthorized'|'active'|'draft'|'deprecated'|'pass'|'fail'`, `size`.
- **Color mapping**:
  - confident, active, pass → `#EAF3EE` bg / `#17724D` text (success tag text alias; keep `colorSuccess` for general semantic accents)
  - clarify → `#FDF3E3` bg / `#8A5A12` text
  - fallback, off_topic, draft, deprecated → `#EEF0F3` bg / `#5C6478` text
  - risk → `#FBE9E7` bg / `#A23B2E` text + ⚠ icon
  - unauthorized, fail → `#FBE7E5` bg / `#B3261E` text + icon
- **Permission handling** — the tag itself is display-only, never clickable. `risk`/`unauthorized` are always text+icon, never color-only.
- **Style** — all state colors share saturation/lightness band; success/warning/error differ only in hue.

### 6.6 ConfirmActionButton
- **Purpose** — structurally prevents mistakes on irreversible actions (release activate/rollback, API key revoke).
- **Used in** — Releases activate/rollback, API Keys revoke, any other destructive action.
- **Composition** — click → confirm modal (description, blast radius, optional typed-confirmation of the resource name) → execute → success toast → list refresh.
- **Key props** — `riskLevel: 'low'|'high'`, `confirmText, requireTypedConfirmation`, `permissionRequired, loading, onSuccessRefresh`.
- **States** — default, loading (in-button spinner + disabled), failure (inline error, modal stays open), success (modal closes + refresh).
- **Permission handling** — no permission → button disabled + short reason tooltip (e.g. "Requires release-manager role"). Prefer visible-but-disabled over hiding, so users know the capability exists.
- **Style** — high risk = `colorError` button; low risk = `colorPrimary`. Modal titles are always phrased as a question ("Roll back release-v3.2.1?").
- **API Key revoke specifics** — because raw secrets are never re-shown after creation, the revoke modal only ever displays `key_id` and a masked suffix. Copy must state that requests using the key will be rejected immediately after revoke.
- **Accessibility** — destructive modals default focus to "Cancel."

### 6.7 FutureFeatureNotice
- **Purpose** — communicates that a feature is not yet usable, without pretending it works, while still surfacing roadmap intent.
- **Applies to two categories**:
  - **(A) No backend contract** — the server API/schema doesn't exist yet.
  - **(B) Contract exists but not wired** — backend contract exists but frontend route, service function, role gate, or UX test is missing.
- **Used in** — pending nav items, disabled action buttons, dashboard metrics with no data source, `ResourceTable` controls with no contract.
- **Composition** — disabled button/menu item + "Coming soon" badge; hover reveals an informational tooltip/alert naming the category (A or B).
- **Key props** — `category: 'no-contract'|'not-wired'`, `variant: 'disabledAction'|'inlineAlert'|'roadmapNote'`, `message, eta` (optional).
- **States** — single state (always disabled); no loading/error state.
- **Permission handling** — identical for every role — the feature is absent regardless of permission level.
- **Style** — neutral gray only (never warning/error colors — this is not a fault state). Badge text is fixed: "Coming soon" (준비 중).
- **Accessibility** — disabled elements still announce "not currently supported" to screen readers.

### 6.8 EmptyState / ErrorState / PermissionState
- **Purpose** — one consistent layout language for "no data," "server error," "no permission," and "unsupported."
- **Used in** — `ResourceTable`, `DetailDrawer` sections, dashboard widget content slots.
- **Composition** — line icon, state title, one-line description, optional next-action button ("Retry," "Clear filters," "Request access").
- **Key props** — `variant: 'empty'|'error'|'permission'|'unsupported'`, `title, description, actionLabel, onAction`.
- **Permission handling** — the `permission` variant briefly names who to contact for access, without exposing internal policy detail.
- **Style** — same layout for all three; only icon color differs subtly (empty=neutral gray, error=`colorError` tone, permission=`colorTextBase` tone). Generous whitespace, not a full-bleed block.

---

## 7. Screen-Level Application

- **Dashboard** — widget cards + StatusTag for risk alerts at top; numbers first, icons minimal. Show onboarding progress (C-1/C-2/C-3) for any service not yet fully onboarded.
- **Intent Catalog** — `ResourceTable` (route_key monospace, example count, StatusTag active/draft/deprecated) + `DetailDrawer`.
- **Runtime Logs** — every column shows masked query only. There is no "view full" / "view raw" toggle in the Runtime Logs table or drawer. Raw query access, if ever needed, happens only through a separate Phase 2 governed workflow screen after the required frontend routes, service functions, role gates, and UX tests are wired.
- **Audit Logs** — `ResourceTable` fixed `readOnly`, no row actions; `DetailDrawer` is view-only. No edit/delete UI exists for this screen at all.
- **Releases** — `release_version` column monospace, `ConfirmActionButton` for activate/rollback, StatusTag (active/draft/deprecated).
- **API Keys** — secret is shown exactly once, in the creation-success modal, with a copy button and an explicit "you will not see this again" warning; it is masked immediately after. Inventory and runtime-setup screens always show only a masked suffix — never the raw secret. Revoke is a high-risk `ConfirmActionButton`.
- **Test Runs** — StatusTag (pass/fail), failed-only filter, `DetailDrawer` shows trace_id + failure reason.

---

## 8. State, Permission & Risk Rules

### 8.1 Permission decision order
Role and environment always come from the server response for the currently selected `ServiceScopeBar` context (service + environment). The UI must never assume or provide a way for the browser to inject/override an actor header, admin token, or role value — no such debug field or override control should exist.

Decide action visibility in this order:
1. No backend contract, or contract exists but not wired (route/service function/role gate/test missing) → **`FutureFeatureNotice`**.
2. Contract exists, current role lacks permission → **disabled + short reason**.
3. Action is structurally not applicable to this role (e.g. write actions for an auditor) → **hidden entirely**.

### 8.2 Runtime Logs / raw query
- Default and only in-UI representation is the masked query.
- No control in this console ("view full," "view raw," any permission-gated reveal) exposes the raw query string.
- Raw query access, when genuinely required, is a separate governed workflow: approval request → audit token issuance → controlled review. Runtime Logs table/drawer must not perform this directly; a dedicated Phase 2 governed workflow screen may handle it only after routes, service functions, role gates, and UX tests are wired.

### 8.3 Audit Logs
- Read-only under every state (loading, error, empty, permission). No write action is ever rendered, regardless of role.

### 8.4 Destructive actions
- Every irreversible action (release activate/rollback, API key revoke, etc.) goes through `ConfirmActionButton` — never a direct-execute button.

### 8.5 API Keys
- Raw secret is shown exactly once, at creation time.
- No inventory, detail, or runtime-setup view ever re-displays the raw secret; only masked suffixes are shown.
- Revoke is always `riskLevel: 'high'` with typed confirmation.

### 8.6 Future/unsupported features
- Covers both (A) no backend contract and (B) contract exists but not wired to route/service function/role gate/UX test.
- Always rendered via `FutureFeatureNotice`, never as a clickable-looking control.

### 8.7 Uncontracted list behaviors
- Pagination, compound filters, or live polling without a confirmed server contract must not be faked. Disable the control or use `FutureFeatureNotice`. Ties to the Phase 0/1/2 model in §5.

### 8.8 Color & accessibility
- State color axes are limited to success/warning/error/neutral; do not invent new colors per page.
- Color is never the sole carrier of meaning — always pair with text or icon.
- Caption/secondary/disabled text must not go lighter than `#6B7688` on white (≥4.5:1 contrast), including disabled states.

---

## 9. Ant Design Theme Token (reference code)

```ts
// theme/token.ts
import type { ThemeConfig } from 'antd';

export const aiIntentRoutingTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1E4B8F',
    colorSuccess: '#1E8A5F',
    colorWarning: '#B7791F',
    colorError: '#B3261E',
    colorInfo: '#3D6FA5',

    colorTextBase: '#1B1F27',
    colorTextSecondary: '#6B7688', // floor for caption/disabled text (>=4.5:1 on white)
    colorBgLayout: '#F2F4F7',
    colorBgContainer: '#FFFFFF',
    colorBorder: '#DCE1E8',
    colorBorderSecondary: '#E8ECF1',

    borderRadius: 6,
    fontSize: 14,
    fontFamily:
      "'Pretendard', -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif",

    wireframe: false,
  },
  components: {
    Layout: {
      siderBg: '#0F1A2E',
      headerBg: '#FFFFFF',
      headerHeight: 48,
      bodyBg: '#F2F4F7',
    },
    Menu: {
      darkItemBg: '#0F1A2E',
      darkItemSelectedBg: '#1E4B8F',
      darkItemColor: '#B9C2D6',
      darkItemHoverColor: '#FFFFFF',
    },
    Table: {
      headerBg: '#FAFBFC',
      rowHoverBg: '#F7F9FC',
      borderColor: '#DCE1E8',
      cellPaddingBlock: 8,
    },
    Tag: {
      defaultBg: '#EEF0F3',
      defaultColor: '#5C6478',
    },
    Drawer: {
      colorBgElevated: '#FFFFFF',
    },
  },
};

// ProLayout / ProTable density default
export const proTableDefaults = {
  size: 'small', // compact density
  options: { density: true, fullScreen: false },
};

// Permission decision order (see §8.1):
// 1) no backend contract / not wired to route+service-fn+role-gate+test -> FutureFeatureNotice
// 2) contract exists, current role lacks permission -> disabled + short reason
// 3) action structurally not applicable to this role -> hidden entirely
// Role/environment ALWAYS come from server response for the selected ServiceScope.
// Never accept a client-supplied actor/admin header or role override in the UI.
```

---

## 10. Forbidden UI Patterns Checklist

- Landing-page hero sections, large background imagery.
- Purple hues, high-saturation gradients.
- Exposing raw query text in Runtime Logs, or any "view full"/"view raw" toggle.
- Edit/delete actions on Audit Logs.
- Rollback/revoke buttons without a confirmation step.
- Re-displaying an API key secret after its one-time creation reveal.
- Any UI for directly injecting/overriding an actor header or admin token in the browser.
- Faking pagination, compound filters, or live polling with no server contract.
- Rendering a Phase 2 governed workflow as if it were a real, working mock state.
- Hiding a no-permission action without a reason, or treating it as an error.
- Presenting an unimplemented feature as a clickable, working control.
- Rendering ID/route_key/trace_id in non-monospace body text.
- Using a different state-color system per screen, or conveying state by color alone.
- Heavy shadows, overused rounded cards, decorative icon overuse.
- Using a gray lighter than `#6B7688` for body or disabled text on white.
