# Task 3 Report: Reorder Diagnostics UI By Importance And Split Catalog Metadata Below The Table

## Implementation Summary

- Lifted Test Run diagnostics loading from `TestRunDiagnosticsPanel.tsx` into `index.tsx`. The page owns the diagnostics response, loading state, error state, cancellation guard, and reset behavior when the service, selected Test Run, or result step changes.
- Reworked `TestRunDiagnosticsPanel` into an actionable, results-aware panel. It now uses `buildTestRunInsights` and `formatIssueTitle` to render the Korean-first order: `가장 먼저 확인할 문제`, `실패 패턴 요약`, and `다음 조치`.
- Added `TestRunCatalogStatusPanel` after the `ProTable`. It contains the catalog version, state, reproducibility, intent/example/embedding counts, ready vector index, and Test Run vector index metadata.
- Preserved the visible diagnostics failure state and exact copy: `진단 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.`

## TDD Evidence

### RED

Ran before production implementation from `frontend/intent-routing-console`:

```bash
npm run test:unit -- testRunDiagnosticsPanelContract.test.ts
npm run test:unit -- testRunsPageContract.test.ts
npm run test:unit -- testRunCatalogStatusPanelContract.test.ts
```

Observed the expected failures:

- Diagnostics panel contract: 5 failures for the missing page-owned props, insight imports, Korean actionable sections, and error-state wiring.
- Test Runs page contract: 3 failures for missing diagnostics state/fetching, panel props, and post-table catalog status panel.
- Catalog status panel contract: failed because `TestRunCatalogStatusPanel.tsx` did not exist.

### GREEN

After implementation, the focused suites passed:

```bash
npm run test:unit -- testRunDiagnosticsPanelContract.test.ts
npm run test:unit -- testRunCatalogStatusPanelContract.test.ts
npm run test:unit -- testRunsPageContract.test.ts
```

Results: 5/5, 1/1, and 16/16 tests passed respectively.

Broader verification also passed:

```bash
npm run test:unit -- src/pages/TestRuns
npm run typecheck
git diff --check
```

Results: 12 TestRuns test files and 62 tests passed; `max setup && tsc --noEmit` exited 0; `git diff --check` produced no whitespace errors.

## Files Changed

- `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
- `frontend/intent-routing-console/src/pages/TestRuns/TestRunCatalogStatusPanel.tsx`
- `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
- `frontend/intent-routing-console/src/pages/TestRuns/testRunCatalogStatusPanelContract.test.ts`
- `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`
- `.superpowers/sdd/task-3-report.md`

## Self-Review

- Confirmed one page-level diagnostics request feeds both panels and is cancelled before stale service/Test Run/step responses can update state.
- Confirmed the visible order is test summary, actionable diagnostics, detailed results table, then catalog/vector metadata.
- Confirmed issue tags use `formatIssueTitle` rather than raw diagnostic code labels; raw JSON count displays were removed in favor of `insights.impactBullets` prose.
- Confirmed changed UI code adds no React Query, axios, trusted browser headers, semantic Ant Design tag colors, or dark content surfaces.

## Concerns

- Verification is contract/unit/type focused. No authenticated browser session was available for a live visual check of the Test Runs workflow, so runtime layout with production diagnostics data remains unverified.

## Review Fixes

- Localized the detailed results-table reason with `formatResultReason`; the raw backend reason is now retained only in the cell `title` tooltip.
- Mapped failure patterns to supported `StatusTag` tones: Intent mismatch to warning, decision mismatch to fail, and fallback to fallback.
- Rendered Catalog lifecycle and reproducibility as Korean `StatusTag` values rather than plain backend status text.
- Changed unknown diagnostic issue copy to the Korean-only generic `해석되지 않은 진단 이슈입니다.` so raw codes are not visible as primary labels.
- Restored `actual_decision_counts` as the `실제 결정 분포` card with localized decision labels and counts.

## Review Fix TDD Evidence

### RED

Updated the four covering contract/copy suites first, then ran:

```bash
npm run test:unit -- testRunResultCopy.test.ts
npm run test:unit -- testRunDiagnosticsPanelContract.test.ts
npm run test:unit -- testRunCatalogStatusPanelContract.test.ts
npm run test:unit -- testRunsPageContract.test.ts
```

Observed the intended failures: unknown issue copy included the raw code; the diagnostics panel lacked pattern-tone mapping and actual-decision distribution; the catalog panel lacked semantic tags; and the page lacked localized reason rendering with raw tooltip detail.

### GREEN

Reran the same suites after the fixes:

```bash
npm run test:unit -- testRunResultCopy.test.ts
npm run test:unit -- testRunDiagnosticsPanelContract.test.ts
npm run test:unit -- testRunCatalogStatusPanelContract.test.ts
npm run test:unit -- testRunsPageContract.test.ts
npm run typecheck
```

Results: 7/7, 7/7, 2/2, and 17/17 tests passed; `max setup && tsc --noEmit` exited 0.
