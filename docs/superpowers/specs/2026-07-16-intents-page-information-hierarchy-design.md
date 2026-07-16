# Intents Page Information Hierarchy Design

**Date:** 2026-07-16  
**Status:** Approved direction — implementation specification  
**Target:** `frontend/intent-routing-console` route `/intents`

## Context

The Intent Catalog is the working surface where a service developer creates and
reviews Intents, maps each Intent to a stable `route_key`, maintains positive and
negative examples, and then continues to Test Runs. The current page has the
correct list-to-drawer workflow, but several visual choices make the catalog
slower to scan and can imply readiness that the server has not confirmed.

This specification implements the previously approved option B: improve both
the catalog list and the detail drawer without changing backend contracts,
authorization rules, or mutation behavior.

## Goals

- Make the identifying and decision-making fields scannable in one pass.
- Replace ambiguous counts and generic tags with explicit, shared semantics.
- Keep simple catalog filters in one compact line instead of a separate ProTable
  query form.
- Organize the detail drawer into named sections with readable code values and
  explicit empty states.
- Keep the Test Runs transition visible without claiming that the catalog is
  ready when readiness is not server-derived.
- Prevent avoidable horizontal overflow at common desktop and narrow widths.

## Non-goals

- Add server pagination, compound server filters, polling, or readiness APIs.
- Add Example edit, delete, or reject behavior.
- Change Intent or Example API payloads.
- Change service-scope or role-gate behavior.
- Redesign the global Admin shell or other catalog workflow pages.

## Design

### 1. Next-step guidance

Keep `WorkflowNextActionBar`, but use neutral Korean copy:

- Title: `다음 단계: Test Runs에서 검증`
- Description: `Intent와 Example을 정리한 뒤 Test Runs에서 검증 bundle을 만드세요.`
- Primary action: `Test Runs로 이동`

The action remains permission-gated exactly as it is today. The page must not
use words such as `ready`, `complete`, or `validated` because no server contract
currently proves those states.

### 2. Catalog toolbar and filters

Disable the generated ProTable search form. Render one compact toolbar row with:

- A text input labeled by placeholder `Intent ID 또는 이름 검색`.
- A status select with `전체 상태`, `Active`, `Draft`, and `Deprecated`.
- A result count derived from the filtered client array.
- Refresh and density controls retained through ProTable options.
- `Intent 추가` as the only primary action, visible only to catalog editors.

Filtering remains client-side over the already returned array. The UI must not
send or imply unsupported server-side filters. The text query matches
`intent_id`, `display_name`, and `route_key`, case-insensitively. The status
filter performs an exact match.

### 3. Catalog table hierarchy

Use this column order:

1. `Intent`: monospace `intent_id`, followed by secondary `display_name`.
2. `Route key`: monospace text with ellipsis, tooltip, and copy affordance.
3. `Keywords`: explicit `포함 N · 제외 N` copy instead of an unlabeled ratio.
4. `Status`: shared `StatusTag` using the canonical neutral treatment for
   `draft` and `deprecated`.
5. Actions: `상세` and, when permitted, `편집`.

All cells remain single-line where practical. The table receives an explicit
horizontal scroll floor so long route keys or narrow viewports do not squeeze
columns into unreadable layouts.

### 4. Detail drawer hierarchy

Use a 560px detail drawer and divide its content into these sections:

- Header: monospace Intent ID, shared `StatusTag`, and the existing edit action.
- `기본 정보`: display name, domain, description, route key, created, updated.
- `키워드`: separate `포함 키워드` and `제외 키워드` groups. Each group has an
  explicit `없음` empty value when no keywords exist.
- `Examples`: existing add action, capability notice, and table.

`route_key` is monospace and copyable. Missing timestamps use `없음`, not
`none`. Example behavior and masking remain unchanged. The Examples table gets
horizontal scrolling at a compact minimum width.

### 5. Form drawers

Keep the current Intent and Example form fields and API flow. Align both form
drawer widths to 560px and preserve the fixed visible cancel/save action area.
No form validation or payload behavior changes are included in this task.

### 6. Responsive behavior

- The catalog toolbar wraps into multiple rows when space is insufficient.
- Search input and status select use bounded widths on desktop and fill the
  available width on small screens.
- Tables scroll horizontally rather than clipping or compressing identifiers.
- Drawer widths continue to use Ant Design viewport fallback behavior.

## Component boundaries

- `IntentCatalogTable.tsx` owns toolbar state, client filtering, column
  presentation, and table overflow behavior.
- `pages/Intents/index.tsx` owns workflow copy, drawer composition, and existing
  mutation/data-loading flows.
- `global.less` owns only reusable responsive layout classes required by the
  catalog toolbar and detail sections.
- `StatusTag.tsx` is reused without adding another status-color mapping.

## Testing

- Add a source-contract unit test for the table to prove generated ProTable
  search is disabled, shared `StatusTag` is used, route keys are monospace and
  copyable, keyword counts are labeled, and horizontal scrolling is configured.
- Add a source-contract unit test for the page to prove readiness language is
  absent, neutral next-step copy is present, drawer sections are named, missing
  values use `없음`, and drawer/table widths are bounded.
- Run the focused tests first, then the complete frontend unit suite,
  TypeScript check, production build, prohibited-pattern search, and an
  authenticated browser smoke when credentials are available.

## Acceptance criteria

- No visible UI claims the catalog is ready without server-derived evidence.
- A user can distinguish include and exclude keyword counts without learning a
  slash convention.
- `intent_id` and `route_key` are visually identifiable code values.
- All catalog statuses use the shared semantic StatusTag system.
- Simple filters occupy one toolbar line at desktop width and wrap safely.
- Detail content is grouped into named sections with explicit empty values.
- No API, authorization, mutation, pagination, or unsupported Phase 2 behavior
  is introduced.
