# Test Run Actionable Diagnostics UX: Final Re-review Fix 2

## Status

Implemented the two remaining Important findings from the second final re-review.

## Changes

- Result rows in `not_loaded`, `loading`, and `error` states now render state-specific Korean content in both the failure-pattern and next-action sections. The loaded-only empty messages remain available only after result rows have loaded.
- Failure patterns now retain whether each expected/actual value is an Intent or a decision. Decision values are localized with `formatDecisionLabel` in both the pattern UI and generated next actions.
- Added regressions for result-fetch error copy, decision-mismatch guidance, and fallback patterns without an expected Intent.

## Verification

Run from `frontend/intent-routing-console`:

- `npm run test:unit -- testRunResultInsights.test.ts`
- `npm run test:unit -- testRunDiagnosticsPanelContract.test.ts`
- `npm run test:unit -- testRunsPageContract.test.ts`
- `npm run typecheck`
- `npm run test:unit -- TestRuns`

All commands passed during final verification. `git diff --check` also passed.

## Concern

The new UI-state regression is a source contract test because this checkout's Test Runs suite does not mount the Ant Design panel. It asserts that non-loaded result states use dedicated descriptions and gate both loaded-only empty messages.
