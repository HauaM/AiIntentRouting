# Services Page Information Hierarchy Design

## Status

Approved direction: option B, reorganize the existing `/services` page without changing its API, authorization, or routing contracts.

## Goal

Make the Services page communicate the selected Service, onboarding progress, and current action in a clear order while reducing repeated information and excessive vertical space.

## Source Requirements

- `docs/THEME_AND_UX_GUIDE_v1.md` §1 Design Direction, §3 Typography, §4 Layout, and §5 Authorization-First Onboarding Flow.
- `docs/AdminUI_Handbook/v04/PATTERN_KIT.md` Layout Contract and Authorization-first onboarding.
- `docs/AdminUI_Handbook/v04/ONBOARDING_FLOW.md` C-1 Service Onboarding and C-2 Service Membership.
- `docs/IntentRouting_PRD_v0.2_20260624.md` §5.1 서비스 온보딩 흐름.
- Accepted direction from the 2026-07-16 UI review: option B.

## Scope

### In scope

- Reorder the existing Services page into a clear selected-Service and onboarding workflow.
- Reduce repeated selected-Service information.
- Add a compact C-1/C-2/C-3 onboarding progress summary based only on data already available to the frontend.
- Make Service IDs single-line, copyable, and discoverable through ellipsis plus tooltip.
- Reduce empty membership-table height.
- Make user-facing copy on this page consistently Korean while preserving domain terms such as Service ID, environment, and role where they are clearer than translated labels.
- Verify that the canonical dark `AdminShell` sidebar token is rendered. Fix only the token/theme wiring responsible if the browser output remains light.
- Add focused source/component tests and perform browser visual verification.

### Out of scope

- Admin API changes.
- Authorization, role-gate, session, or Service-scope behavior changes.
- New routes, tabs, wizard state, or persisted onboarding state.
- Fake completion state for C-2 or C-3.
- Changes to other Admin Console pages solely for language consistency.
- New dependencies.

## Information Architecture

The page uses this order:

1. `AdminShell` page title and existing global `ServiceScopeBar`.
2. A concise onboarding notice explaining the C-1 → C-2 → C-3 sequence.
3. A selected-Service summary card containing the Service identity, display name, environment, status, and current user's Service roles.
4. A compact onboarding progress row inside the selected-Service area:
   - C-1 is complete when a selected Service exists.
   - C-2 is presented as the current membership step; it is not marked complete from inferred client state.
   - C-3 is informational and links to no fake action from this page.
5. The selected Service membership panel as the primary current-stage panel.
6. Service creation as a secondary panel for `system_admin`, visually separated from the selected-Service workflow.
7. Accessible Services as a compact switcher/list at the bottom. The currently selected Service is not represented as a business-selected table row; selection remains an explicit text action.

The page remains a single route. No tab or stepper navigation state is introduced.

## Component Changes

### Selected Service summary

- Keep `Descriptions`, but use a two-column layout at desktop widths so labels and long values do not wrap into narrow cells.
- Render Service ID with `Typography.Text code copyable ellipsis` inside a bounded inline container.
- Add a tooltip containing the full Service ID.
- Keep semantic `StatusTag` and environment text badge behavior.
- Keep roles as compact tags.

### Onboarding progress

- Use a restrained three-item status row, not a marketing-style stepper or hero.
- Each item includes its C-stage label and text state so meaning is not carried by color alone.
- Use only light semantic surfaces; no dark summary card.
- C-2 and C-3 must not claim completion without server-confirmed data.

### Service membership

- Keep the existing `ServiceMembershipPanel` API and authorization behavior.
- Localize visible labels, placeholders, confirmation copy, and empty-state copy to Korean.
- When the member list is empty, show the standard compact empty state without reserving a 320px vertical scroll area.
- Retain bounded horizontal scrolling for narrow screens and populated tables.

### Service creation

- Preserve all five current fields, validation, request transformation, and success behavior.
- Use a responsive grid with predictable field widths instead of an irregular wrapping `Space` layout.
- Keep one primary submit action.
- Present it after the selected-Service workflow because it starts another C-1 flow rather than continuing the currently selected Service.

### Accessible Services

- Keep the list because it exposes every server-derived Service scope and supports explicit switching.
- Keep a compact table and fixed column widths.
- Use Korean column/action/empty-state copy.
- Preserve single-line Service IDs with tooltip and copy affordance.
- Avoid a large empty scroll region when only a few rows exist.

### AdminShell sidebar

- The canonical target is the dark sidebar defined by the theme guide.
- First verify actual browser output against `AdminShell` theme configuration.
- If the sidebar remains light, correct only the ProLayout/ConfigProvider token wiring needed to render the existing canonical dark palette.
- Do not redesign navigation, change route visibility, or alter role gates.

## Data And Permission Flow

All data continues to come from the existing `adminSession` model and Admin service functions.

- Selected Service: `session.serviceId` matched against `session.services`.
- Accessible Services: `session.services` from server-derived scope.
- Service creation: existing `createService`, followed by `restoreSession` and `setServiceId`.
- Membership: existing selected-Service member list, user search, grant, and revoke calls.
- Visibility: existing `canUseServicesPage`, `canCreateServices`, and `canManageServiceMembers` gates.

No client-supplied trusted headers, fabricated membership state, or new polling/pagination behavior is introduced.

## Error And Empty States

- Preserve existing API error handling and warning alerts.
- Empty Service membership uses a concise Korean empty state and no fixed blank canvas.
- Empty accessible Service scope uses a concise Korean empty state.
- A Service created but absent from refreshed scope retains the existing warning behavior.
- C-2/C-3 progress stays informational when the frontend lacks server-confirmed completion evidence.

## Accessibility And Responsive Behavior

- All icon-only actions require an accessible name and tooltip; existing global logout behavior is verified but not otherwise redesigned in this scope.
- Service ID remains keyboard-copyable and exposes the full value via tooltip.
- Status meaning is expressed with text as well as color.
- Disabled and secondary text must meet the theme guide contrast floor.
- Form fields stack to one column on narrow screens and use a stable multi-column grid on desktop.
- Tables retain horizontal scrolling when their minimum readable width exceeds the container.

## Testing And Verification

- Add failing source/component contract tests before production changes.
- Cover the page section order, bounded/copyable selected Service ID, Korean visible copy, responsive form grid, and compact table behavior.
- Cover the membership empty-state behavior without a fixed 320px blank region.
- Run focused Services page tests, then the frontend test suite and build.
- Search changed implementation files for prohibited dependencies, browser auth headers, fake pagination, and live polling.
- Start the local frontend or use the existing runtime, capture `/services` at desktop width, and verify section hierarchy, sidebar color, overflow, empty states, and contrast.

## Success Criteria

- The first screenful identifies the selected Service and current onboarding step without reading the entire page.
- Selected-Service identity is not redundantly repeated as equal-priority content.
- Long Service IDs do not wrap or break the description grid.
- Empty membership content does not create a large blank table canvas.
- Visible Services-page copy is consistently Korean except for deliberate domain identifiers.
- The rendered sidebar matches the canonical dark AdminShell design.
- Existing API, permission, session, and routing tests remain unchanged in behavior and pass.
