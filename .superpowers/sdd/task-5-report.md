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
