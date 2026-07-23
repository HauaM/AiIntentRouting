# Test Run Results UX Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Test Runs result screen understandable to service developers and operators by separating Release readiness, test judgment, router handling, dataset composition, and next actions.

**Architecture:** Keep the current Test Runs page and backend contracts as the primary source of truth. Add frontend view-model helpers that translate backend fields into user-facing concepts, then render those concepts in the summary, diagnostics, and detailed result areas. Keep backend/API changes out of this first pass except for clearly documented follow-up gaps.

**Tech Stack:** React, TypeScript, Umi 4, Ant Design Pro v6, ProComponents, Vitest, existing AiIntentRouting `StatusTag`, existing Admin UI service patterns.

## Required Skills

- `ai-intent-routing-admin-ui`: apply Admin Console v04 patterns, `StatusTag`, light semantic surfaces, Umi request, server-derived contracts, and Phase 0/1/2 honesty rules.
- `ai-intent-routing-ant-design-ui`: apply Ant Design and ProComponents layout heuristics for dense desktop operations screens.
- `superpowers:test-driven-development`: write failing tests before production code for every behavior change.
- `superpowers:subagent-driven-development`: execute this plan task-by-task with implementer and reviewer gates.

## Global Constraints

- Admin Console is FHD desktop-first; do not add mobile-specific UX.
- Preserve narrowed desktop robustness with wrapping, ellipsis, table overflow, and viewport-bounded floating layers.
- Use `StatusTag` for semantic state, gate, severity, result, and decision badges.
- Do not use Ant Design preset semantic `Tag color` values.
- Do not introduce React Query, `@tanstack/react-query`, axios, fake server pagination, live polling, or trusted browser headers.
- Do not send `Authorization: Bearer`, `X-Admin-Token`, `X-Actor-Id`, `X-Actor-Roles`, or `X-Service-Scope` from normal browser Admin UI code.
- Do not render backend-only issue codes or raw internal reason strings as primary user-facing copy.
- Keep backend contracts honest: if the API does not provide a field, show only what can be established from existing fields and document the follow-up gap.
- Do not remove or rewrite unrelated dirty work in `docs/pilot/*` or unrelated plan files.
- TDD is required: every production behavior change must first have a focused failing Vitest test.

---

## File Structure

- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.ts`
  - User-facing Korean labels for result/gate/decision concepts and reason copy.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.test.ts`
  - Copy contract tests for renamed concepts and internal-code shielding.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.ts`
  - View-model helpers for dataset composition, release readiness, review impact, and next-action grouping.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.test.ts`
  - Behavior tests for uploaded/common-risk composition, REVIEW impact, gate blockers, and source-aware actions.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
  - Render release blockers, router handling distribution, failure/review action groups, and diagnostics fallback states.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
  - Contract tests for the diagnostics panel structure and copy.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
  - Rename detailed table headings and pass summary-derived context into diagnostics.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`
  - Contract tests for detailed table terminology and summary placement.
- Optionally modify `frontend/intent-routing-console/src/pages/TestRuns/index.less` or `frontend/intent-routing-console/src/global.less`
  - Only if layout needs small scoped styling for inline metrics or badges.
- Create `docs/superpowers/reviews/2026-07-23-test-run-results-ux-clarity-api-followups.md`
  - Document backend/API gaps that cannot be solved honestly in the frontend-only pass.

## Task 1: User-Facing Concept Copy And View Models

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.test.ts`

**Interfaces:**
- Consumes: `API.TestRunSummary`, `API.TestRunDiagnostics`, `API.TestRunResult[]`
- Produces:
  - `formatTestJudgmentLabel(result?: string | null): string`
  - `formatRouterDecisionLabel(decision?: string | null): string`
  - `formatReleaseGateLabel(gatePassed: boolean): string`
  - `buildDatasetComposition(results: API.TestRunResult[]): TestRunDatasetComposition`
  - `buildReleaseReadiness(summary?: API.TestRunSummary, results?: API.TestRunResult[]): TestRunReleaseReadiness`
  - `buildTestRunInsights(results: API.TestRunResult[], diagnostics?: API.TestRunDiagnostics, resultsLoadState?: TestRunResultsLoadState): TestRunInsights`

- [ ] **Step 1: Write failing copy tests**

Add tests to `testRunResultCopy.test.ts`:

```ts
it('uses separate labels for release gate, test judgment, and router handling', () => {
  expect(formatReleaseGateLabel(true)).toBe('Release 가능');
  expect(formatReleaseGateLabel(false)).toBe('Release 차단');
  expect(formatTestJudgmentLabel('PASS')).toBe('통과');
  expect(formatTestJudgmentLabel('FAIL')).toBe('실패');
  expect(formatTestJudgmentLabel('REVIEW')).toBe('검토 필요');
  expect(formatRouterDecisionLabel('confident')).toBe('정상 연결');
  expect(formatRouterDecisionLabel('risk')).toBe('위험 차단');
});

it('does not expose unknown backend reason strings as primary copy', () => {
  expect(formatResultReason('some new backend reason')).toBe('판정 이유를 해석할 수 없습니다.');
});
```

- [ ] **Step 2: Run copy tests and verify RED**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns/testRunResultCopy.test.ts
```

Expected: FAIL because the new exported helpers do not exist or current copy does not match.

- [ ] **Step 3: Implement copy helpers**

Update `testRunResultCopy.ts` so the existing `formatDecisionLabel` can stay for compatibility, but new UI uses the more specific names:

```ts
export function formatRouterDecisionLabel(decision?: string | null) {
  if (!decision) return '처리 방식 없음';
  return routerDecisionCopy[decision] ?? '처리 방식 확인 필요';
}

export function formatTestJudgmentLabel(result?: string | null) {
  if (!result) return '판정 없음';
  return testJudgmentCopy[result.toUpperCase()] ?? '판정 확인 필요';
}

export function formatReleaseGateLabel(gatePassed: boolean) {
  return gatePassed ? 'Release 가능' : 'Release 차단';
}
```

Keep `formatDecisionLabel` exported as an alias or wrapper so existing code and tests keep working during migration.

- [ ] **Step 4: Write failing view-model tests**

Add tests to `testRunResultInsights.test.ts`:

```ts
it('summarizes classification and risk rows without claiming unsupported provenance', () => {
  const composition = buildDatasetComposition([
    resultFixture({ case_id: 'P001', case_type: 'positive' }),
    resultFixture({ case_id: 'P002', case_type: 'positive' }),
    resultFixture({ case_id: 'risk-common-abuse-001', case_type: 'risk' }),
  ]);

  expect(composition.classificationCount).toBe(2);
  expect(composition.riskCount).toBe(1);
  expect(composition.totalCount).toBe(3);
  expect(composition.summary).toBe('분류 테스트 2건 + 위험 테스트 1건 = 총 3건');
});

it('explains review rows as not failed but release-impacting', () => {
  const insights = buildTestRunInsights([
    resultFixture({ case_id: 'P001', result: 'REVIEW', reason: 'requires human inspection' }),
  ], diagnosticsFixture({
    result_counts: { PASS: 0, REVIEW: 1, FAIL: 0 },
    actual_decision_counts: { clarify: 1 },
  }), 'loaded');

  expect(insights.nextActions.some((action) => action.title === '검토 필요한 케이스 줄이기')).toBe(true);
  expect(insights.impactBullets).toContain('검토 1건은 실패는 아니지만 Release 통과율을 낮춥니다.');
});
```

- [ ] **Step 5: Run view-model tests and verify RED**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns/testRunResultInsights.test.ts
```

Expected: FAIL because `buildDatasetComposition` and new REVIEW behavior are not implemented.

- [ ] **Step 6: Implement view models**

Implement `TestRunDatasetComposition` using existing fields only:

```ts
export type TestRunDatasetComposition = {
  classificationCount: number;
  riskCount: number;
  totalCount: number;
  summary: string;
  sourceIsUnavailable: boolean;
};
```

Classification rows are `case_type !== 'risk'`. Risk rows are `case_type === 'risk'`. Do not label rows as uploaded CSV, automatic common risk pack, or custom risk CSV because the current result API does not expose a first-class row source/provenance field.

Implement REVIEW actions so REVIEW rows are visible even when there are no FAIL rows.

- [ ] **Step 7: Run task tests and verify GREEN**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns/testRunResultCopy.test.ts src/pages/TestRuns/testRunResultInsights.test.ts
```

Expected: PASS.

## Task 2: Results Summary And Diagnostics Panel Restructure

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`

**Interfaces:**
- Consumes Task 1 helpers:
  - `buildDatasetComposition(results)`
  - `buildReleaseReadiness(summary, results)`
  - `formatRouterDecisionLabel(decision)`
  - `formatTestJudgmentLabel(result)`
  - `formatReleaseGateLabel(summary.gate_passed)`
- Produces:
  - A summary area that separates `Release 가능 여부`, `데이터 구성`, and `품질 지표`.
  - A diagnostics panel that shows router handling distribution in one row and renders REVIEW as a visible action group.

- [ ] **Step 1: Write failing panel contract tests**

Add tests to `testRunDiagnosticsPanelContract.test.ts`:

```ts
it('separates release blockers from router handling distribution', () => {
  const source = read('TestRunDiagnosticsPanel.tsx');

  expect(source).toContain('Release 차단 사유');
  expect(source).toContain('라우터가 실제로 처리한 방식');
  expect(source).not.toContain('실제 결정 분포');
});

it('renders result-derived insights even when diagnostics loading fails', () => {
  const source = read('TestRunDiagnosticsPanel.tsx');

  expect(source).toContain('diagnosticsUnavailable');
  expect(source).not.toContain('return (\\n      <Alert\\n        type=\"error\"');
});
```

- [ ] **Step 2: Run panel contract tests and verify RED**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts
```

Expected: FAIL because the panel still uses old structure or early-returns on diagnostics error.

- [ ] **Step 3: Update diagnostics panel**

Change `TestRunDiagnosticsPanel` to:

- show `Release 차단 사유` as a distinct section when summary/readiness data is provided;
- rename `실제 결정 분포` to `라우터가 실제로 처리한 방식`;
- keep the decision distribution as one inline row using `StatusTag`;
- show REVIEW next actions when `buildTestRunInsights` produces them;
- if diagnostics API fails but result rows are loaded, render result-derived insights and a small warning that detailed diagnostics are unavailable.

- [ ] **Step 4: Write failing page contract tests**

Add tests to `testRunsPageContract.test.ts`:

```ts
it('uses user-facing table headings for expected classification and test judgment', () => {
  const source = read('index.tsx');

  expect(source).toContain("title: '기대한 분류'");
  expect(source).toContain("title: '실제 연결 결과'");
  expect(source).toContain("title: '테스트 판정'");
  expect(source).not.toContain("title: '기대 결과'");
  expect(source).not.toContain("title: '실제 결과'");
});
```

- [ ] **Step 5: Run page contract test and verify RED**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns/testRunsPageContract.test.ts
```

Expected: FAIL until headings are changed.

- [ ] **Step 6: Update result table and summary wiring**

Update `index.tsx`:

- `기대 결과` -> `기대한 분류`
- `실제 결과` -> `실제 연결 결과`
- `결과` -> `테스트 판정`
- `사유` -> `판정 이유`
- render the gate tag with `formatReleaseGateLabel`
- pass `summary` to `TestRunDiagnosticsPanel` if Task 2 adds that prop.

- [ ] **Step 7: Run task tests and verify GREEN**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts src/pages/TestRuns/testRunsPageContract.test.ts
```

Expected: PASS.

## Task 3: Actionable Next Steps And API Follow-Up Documentation

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
- Create: `docs/superpowers/reviews/2026-07-23-test-run-results-ux-clarity-api-followups.md`

**Interfaces:**
- Consumes Task 1 and Task 2 next-action model.
- Produces:
  - next actions grouped by target case IDs and user-facing fix path;
  - modal copy that references real Admin Console pages: Test Runs, Intent Catalog, Catalog version registration;
  - API follow-up doc for fields the frontend cannot honestly infer.

- [ ] **Step 1: Write failing next-action tests**

Add tests to `testRunResultInsights.test.ts`:

```ts
it('groups next actions by case ids instead of anonymous numbering', () => {
  const insights = buildTestRunInsights([
    resultFixture({
      case_id: 'P006',
      expected_intent: 'owner_contact_lookup',
      actual_intent: 'program_supported_question',
      result: 'FAIL',
      reason: 'actual intent did not match expected intent',
    }),
  ], undefined, 'loaded');

  expect(insights.nextActions[0].caseIds).toEqual(['P006']);
  expect(insights.nextActions[0].helpSteps.join(' ')).toContain('Intent Catalog 화면');
  expect(insights.nextActions[0].helpSteps.join(' ')).toContain('Catalog 버전');
});
```

- [ ] **Step 2: Run next-action test and verify RED**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns/testRunResultInsights.test.ts
```

Expected: FAIL if current copy still lacks the required page-specific guidance.

- [ ] **Step 3: Implement next-action copy improvements**

Ensure next actions:

- always show target case IDs when available;
- avoid backend terms like `decision mismatch` as titles;
- describe exact user path in the Admin Console;
- distinguish “CSV expected_intent 수정” from “Intent Catalog example 보강”.

- [ ] **Step 4: Write API follow-up document**

Create `docs/superpowers/reviews/2026-07-23-test-run-results-ux-clarity-api-followups.md` with this content:

```md
# Test Run Results UX Clarity API Follow-Ups

## Confirmed Frontend-Only Limits

The current Test Run result response includes `actual_route_key` but does not include `expected_route_key`, so the frontend cannot honestly show expected vs actual route key side by side for route-key mismatch rows.

The current row response includes `confidence` but not threshold comparison detail, top candidate margin, or candidate list, so the frontend cannot fully explain why a row became `clarify`, `fallback`, or `review`.

The current result rows include `case_type` but not a first-class source field such as `uploaded_csv`, `common_risk_pack`, or `custom_risk_csv`. The frontend must not present row source/provenance as confirmed until such a field exists.

## Recommended API Additions

- Add `expected_route_key` to `TestRunResultResponse`.
- Add `case_source` with values `uploaded_csv`, `common_risk_pack`, `custom_risk_csv`.
- Add a row-level explanation object for threshold outcomes: `threshold_value`, `confidence`, `margin`, `top_candidates`, and `decision_reason`.
- Add display metadata for expected and actual intents: `display_name`, `domain`, and `intent_id`.

## Product Rule

Until these fields exist, the Admin UI must not claim more precision than the backend response supports.
```

- [ ] **Step 5: Run task tests and verify GREEN**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns/testRunResultInsights.test.ts src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts
```

Expected: PASS.

## Task 4: Full Verification And Guardrails

**Files:**
- Verify all changed files from Tasks 1-3.
- Do not modify production code unless a verification issue requires a small fix with a failing test first.

**Interfaces:**
- Consumes all previous tasks.
- Produces final evidence that the feature is safe to hand over.

- [ ] **Step 1: Run focused Test Runs suite**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/vitest run src/pages/TestRuns
```

Expected: all Test Runs tests PASS.

- [ ] **Step 2: Run TypeScript check**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/tsc --noEmit
```

Expected: PASS.

- [ ] **Step 3: Run production build**

Run:

```bash
cd frontend/intent-routing-console
./node_modules/.bin/max build
```

Expected: build completes successfully.

- [ ] **Step 4: Run Admin UI guardrail searches**

Run:

```bash
cd frontend/intent-routing-console
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" src/pages/TestRuns
rg -n "<Tag[^\\n]*\\bcolor=|darkAlgorithm|color-scheme:\\s*dark|background(-color)?\\s*:\\s*#0|background(-color)?\\s*:\\s*#1" src/pages/TestRuns
```

Expected: no implementation matches. If matches occur only in tests that assert forbidden strings are absent, document that in the report.

- [ ] **Step 5: Optional visual smoke**

If an authenticated browser session is available, open `/test-runs` and verify the results step at FHD desktop width and narrowed desktop width. If not available, state that authenticated visual QA was not run.

## Self-Review Checklist

- [ ] Every user-facing label separates Release readiness, test judgment, and router handling.
- [ ] REVIEW cases are visible as a quality concern even when they are not FAIL.
- [ ] Risk rows are explained as risk tests without inventing uploaded/common/custom source provenance.
- [ ] Next actions reference case IDs and concrete Admin Console pages.
- [ ] Frontend does not claim expected route key, candidate margin, or row source unless provided or safely inferred.
- [ ] Required UI skills and constraints are explicitly included in this plan.
