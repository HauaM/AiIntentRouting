# Task 5 Report: Frontend Reveal Service And API Keys UI

## Status

DONE

## Implementation

- The service-scoped reveal client posts to `/services/{serviceId}/api-keys/{keyId}:reveal` through Umi `request` without trusted browser headers.
- The API Keys Authorization template row displays `Bearer {{intent_routing_api_key}}`; its `Secret 보기/복사` action reveals through the audited endpoint and copies `authorization_header`.
- The created-key modal is controlled directly by `createdKey`, so closing it clears the initial creation secret without retaining page-scoped modal or secret replay state.

## Verification

- `./node_modules/.bin/vitest run src/services/adminServices.test.ts src/pages/ApiKeys/runtimeSetup.test.ts src/pages/ApiKeys/apiKeyCreateFlow.test.ts src/components/intentRouteMultiSelectContract.test.ts` passed: 4 files, 46 tests.
- `./node_modules/.bin/tsc --noEmit` passed.
- Scoped diff check and Admin UI prohibited-pattern scans passed; the only trusted-header matches are the intentional runtime guidance filtering fixture.

## Scope

Only Task 5 API Keys source and test files were changed in this completion commit. Pre-existing unrelated dirty files were preserved.

## Cleanup Before Review (2026-07-22)

- Removed the out-of-scope runtime live-test client, UI, `/v1` development proxy, handbook guidance, CSS, and associated tests from the reveal-flow series.
- Kept the audited reveal client/type/UI, created-key modal clearing behavior, and active-release/scope-selector safeguards.

### Verification

- `./node_modules/.bin/vitest run src/services/adminServices.test.ts src/pages/ApiKeys/runtimeSetup.test.ts src/pages/ApiKeys/apiKeyCreateFlow.test.ts src/components/intentRouteMultiSelectContract.test.ts src/components/adminUiColorGuard.test.ts`: 5 files, 48 tests passed.
- `./node_modules/.bin/tsc --noEmit`: passed.
- `UV_CACHE_DIR=/private/tmp/ai-intent-routing-uv-cache uv run pytest tests/unit/test_admin_ui_handbook_docs_contract.py tests/unit/test_admin_ui_route_config.py -q`: 10 passed.

## Review Fix: Remove Active-Release Scope Gating (2026-07-22)

- Restored `IntentRouteMultiSelect` to its prior API without page-specific `disabled` or `loading` props.
- Removed the API Keys create-panel active-release display, missing-release and empty-candidate alerts, scope-selector gating, and create-button gating.
- Kept the audited reveal client/type/test, Authorization `Secret 보기/복사` flow, and created-key modal clearing behavior.

### Verification

- `./node_modules/.bin/vitest run src/services/adminServices.test.ts src/pages/ApiKeys/runtimeSetup.test.ts src/pages/ApiKeys/apiKeyCreateFlow.test.ts src/components/intentRouteMultiSelectContract.test.ts`: 4 files, 45 tests passed.
- `./node_modules/.bin/tsc --noEmit`: passed.
- Scoped `git diff --check`: passed.
