# Test Run Results Actionable Diagnostics UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Test Run result review actionable by showing Korean failure reasons, prioritized diagnosis, failure-pattern summaries, and concrete next actions in importance order.

**Architecture:** Keep the existing backend diagnostics API and frontend page flow. Add focused frontend utilities for Korean labels and rule-based result insights, then split the diagnostics UI into actionable diagnosis above the detailed table and catalog/vector metadata below it. Lift the diagnostics fetch to the Test Runs page so both rendered regions share one response and the screen reads from summary to root cause, patterns, actions, detailed results, and finally catalog/vector metadata.

**Tech Stack:** React, TypeScript, Umi 4, Ant Design Pro v6, ProComponents, existing `StatusTag`, Vitest contract tests.

## Global Constraints

- Admin Console is a desktop web operations console optimized for FHD usage; do not add mobile-specific UX.
- Use existing Umi `request` service patterns; do not introduce React Query, axios, or browser trusted headers.
- Keep all content surfaces light; use `StatusTag` for semantic states, severity, gate result, and result badges.
- Show `query_masked` only; do not display raw query text.
- Put information in importance order: 테스트 요약, 가장 먼저 확인할 문제, 실패 패턴 요약, 다음 조치, 상세 결과, Catalog / Vector 상태.
- Test result `reason` values must render in Korean in the visible table. Preserve the original English reason only as secondary detail such as tooltip/title text.
- Keep changes scoped to Test Runs UI and frontend tests unless a backend contract gap is proven.

---

## File Structure

- Modify `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
  - Owns actionable diagnosis sections only: primary issue, impact summary, failure-pattern summary, and next-action copy.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
  - Owns diagnostics fetching, page-level section order, result table column rendering, and Korean summary copy.
- Create `frontend/intent-routing-console/src/pages/TestRuns/TestRunCatalogStatusPanel.tsx`
  - Owns Catalog / Vector status metadata rendered below the detailed results table.
- Create `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.ts`
  - Pure mapping helpers for decisions, issue codes, result reasons, block reasons, and recommendations.
- Create `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.ts`
  - Pure rule-based aggregation over `API.TestRunResult[]` and `API.TestRunDiagnostics`.
- Create `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.test.ts`
  - Unit contract for Korean labels and fallback behavior.
- Create `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.test.ts`
  - Unit contract for prioritized issue, mismatch pattern, fallback pattern, and next-action generation.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
  - Contract checks for section order and Korean visible copy.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`
  - Contract checks for Korean reason rendering in the detailed result table.
- Create or modify `frontend/intent-routing-console/src/pages/TestRuns/testRunCatalogStatusPanelContract.test.ts`
  - Contract checks for catalog/vector metadata copy and page-level ordering below the table.

---

### Task 1: Korean Copy Helpers For Reasons, Decisions, And Diagnostics

**Files:**
- Create: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.ts`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.test.ts`

**Interfaces:**
- Produces:
  - `formatDecisionLabel(decision?: string | null): string`
  - `formatResultReason(reason?: string | null): string`
  - `formatIssueTitle(code: string): string`
  - `formatBlockReason(reason: string): string`
  - `formatRecommendation(recommendation: string): string`
  - `formatIntentLabel(intent?: string | null): string`
- Consumes: no project runtime state.

- [ ] **Step 1: Write the failing copy tests**

Create `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  formatBlockReason,
  formatDecisionLabel,
  formatIntentLabel,
  formatIssueTitle,
  formatRecommendation,
  formatResultReason,
} from './testRunResultCopy';

describe('testRunResultCopy', () => {
  it('renders detailed result reasons in Korean', () => {
    expect(formatResultReason('actual intent did not match expected intent')).toBe(
      '기대 Intent와 실제 Intent가 다릅니다.',
    );
    expect(formatResultReason('actual decision did not match expected decision')).toBe(
      '기대 결정과 실제 결정이 다릅니다.',
    );
    expect(formatResultReason('requires human inspection')).toBe(
      '사람의 검토가 필요한 케이스입니다.',
    );
    expect(formatResultReason('matched expected decision')).toBe(
      '기대 결정과 일치합니다.',
    );
    expect(formatResultReason('matched expected decision and intent')).toBe(
      '기대 결과와 일치합니다.',
    );
  });

  it('keeps unknown result reasons Korean-only in visible copy', () => {
    expect(formatResultReason('custom backend reason')).toBe('해석되지 않은 사유입니다.');
    expect(formatResultReason('custom backend reason')).not.toContain('custom backend reason');
    expect(formatResultReason(null)).toBe('사유 없음');
  });

  it('renders decision labels in Korean', () => {
    expect(formatDecisionLabel('confident')).toBe('확정');
    expect(formatDecisionLabel('clarify')).toBe('확인 필요');
    expect(formatDecisionLabel('fallback')).toBe('분류 실패');
    expect(formatDecisionLabel('risk')).toBe('위험 차단');
    expect(formatDecisionLabel('off_topic')).toBe('업무 외 질문');
    expect(formatDecisionLabel('unauthorized')).toBe('권한 없음');
    expect(formatDecisionLabel(null)).toBe('없음');
  });

  it('covers all backend-produced reason and decision values with Korean labels', () => {
    const backendReasons = [
      'matched expected decision',
      'requires human inspection',
      'matched expected decision and intent',
      'actual decision did not match expected decision',
      'actual intent did not match expected intent',
    ];
    const backendDecisions = [
      'confident',
      'clarify',
      'fallback',
      'off_topic',
      'risk',
      'unauthorized',
    ];

    for (const reason of backendReasons) {
      expect(formatResultReason(reason)).toMatch(/[가-힣]/);
      expect(formatResultReason(reason)).not.toContain('해석되지 않은');
    }
    for (const decision of backendDecisions) {
      expect(formatDecisionLabel(decision)).toMatch(/[가-힣]/);
      expect(formatDecisionLabel(decision)).not.toBe(decision);
    }
  });

  it('renders diagnostic issue, block reason, and recommendation copy in Korean', () => {
    expect(formatIssueTitle('intent_mismatch_exists')).toBe(
      'Decision은 맞았지만 Intent가 다른 실패가 있습니다.',
    );
    expect(formatIssueTitle('pass_rate_below_gate')).toBe(
      '통과율이 Release 기준보다 낮습니다.',
    );
    expect(formatBlockReason('pass rate below 70%')).toBe('통과율이 70% 기준보다 낮습니다.');
    expect(formatRecommendation('review rate above 15%')).toBe(
      '검토 대상 비율이 15% 권장 기준보다 높습니다.',
    );
  });

  it('renders null intent values consistently', () => {
    expect(formatIntentLabel('it_api_timeout')).toBe('it_api_timeout');
    expect(formatIntentLabel(null)).toBe('인텐트 없음');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunResultCopy.test.ts
```

Expected: FAIL because `testRunResultCopy.ts` does not exist.

- [ ] **Step 3: Implement the copy helper**

Create `frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.ts`:

```ts
const decisionCopy: Record<string, string> = {
  confident: '확정',
  clarify: '확인 필요',
  fallback: '분류 실패',
  off_topic: '업무 외 질문',
  risk: '위험 차단',
  unauthorized: '권한 없음',
};

const resultReasonCopy: Record<string, string> = {
  'actual intent did not match expected intent': '기대 Intent와 실제 Intent가 다릅니다.',
  'actual decision did not match expected decision': '기대 결정과 실제 결정이 다릅니다.',
  'matched expected decision': '기대 결정과 일치합니다.',
  'requires human inspection': '사람의 검토가 필요한 케이스입니다.',
  'matched expected decision and intent': '기대 결과와 일치합니다.',
};

const issueTitleCopy: Record<string, string> = {
  catalog_version_not_active: '선택한 Catalog 버전이 활성 상태가 아닙니다.',
  catalog_version_not_reproducible: '선택한 Catalog 버전의 재현성 상태가 완전하지 않습니다.',
  catalog_version_has_no_intents: '선택한 Catalog 버전에 Intent가 없습니다.',
  catalog_version_has_no_examples: '선택한 Catalog 버전에 예시 데이터가 없습니다.',
  catalog_version_has_no_ready_vector_index: '선택한 Catalog 버전에 준비된 vector index가 없습니다.',
  catalog_version_has_no_embeddings: '선택한 Catalog 버전에 활성 embedding이 없습니다.',
  test_run_vector_index_not_ready: 'Test Run이 사용한 vector index가 현재 준비 상태와 일치하지 않습니다.',
  risk_case_failed: '위험 케이스 중 실패한 항목이 있습니다.',
  fallback_failures_dominant: '실패한 케이스 중 fallback 결과 비율이 높습니다.',
  intent_mismatch_exists: 'Decision은 맞았지만 Intent가 다른 실패가 있습니다.',
  pass_rate_below_gate: '통과율이 Release 기준보다 낮습니다.',
  review_rate_above_guidance: '검토 대상 비율이 권장 기준보다 높습니다.',
};

export function formatDecisionLabel(decision?: string | null) {
  if (!decision) return '없음';
  return decisionCopy[decision] ?? decision;
}

export function formatIntentLabel(intent?: string | null) {
  return intent || '인텐트 없음';
}

export function formatResultReason(reason?: string | null) {
  if (!reason) return '사유 없음';
  return resultReasonCopy[reason] ?? '해석되지 않은 사유입니다.';
}

export function formatIssueTitle(code: string) {
  return issueTitleCopy[code] ?? `해석되지 않은 진단 코드: ${code}`;
}

export function formatBlockReason(reason: string) {
  const passRateMatch = reason.match(/^pass rate below ([0-9]+)%$/);
  if (passRateMatch) return `통과율이 ${passRateMatch[1]}% 기준보다 낮습니다.`;
  if (reason === 'risk case failed') return '위험 질문 차단 테스트가 실패했습니다.';
  return `해석되지 않은 차단 사유: ${reason}`;
}

export function formatRecommendation(recommendation: string) {
  const reviewRateMatch = recommendation.match(/^review rate above ([0-9]+)%$/);
  if (reviewRateMatch) {
    return `검토 대상 비율이 ${reviewRateMatch[1]}% 권장 기준보다 높습니다.`;
  }
  return `해석되지 않은 권장 조치: ${recommendation}`;
}
```

- [ ] **Step 4: Run the copy tests**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunResultCopy.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.ts frontend/intent-routing-console/src/pages/TestRuns/testRunResultCopy.test.ts
git commit -m "feat: localize test run result copy"
```

---

### Task 2: Rule-Based Failure Pattern And Next Action Insights

**Files:**
- Create: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.ts`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.test.ts`

**Interfaces:**
- Consumes:
  - `API.TestRunResult[]`
  - `API.TestRunDiagnostics | undefined`
- Produces:
  - `buildTestRunInsights(results: API.TestRunResult[], diagnostics?: API.TestRunDiagnostics): TestRunInsights`
  - `TestRunInsights.primaryProblem: string`
  - `TestRunInsights.impactBullets: string[]`
  - `TestRunInsights.patterns: TestRunPattern[]`
  - `TestRunInsights.nextActions: string[]`

- [ ] **Step 1: Write the failing insights tests**

Create `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { buildTestRunInsights } from './testRunResultInsights';

const result = (
  overrides: Partial<API.TestRunResult>,
): API.TestRunResult => ({
  case_id: 'C001',
  query_masked: '마스킹된 질의',
  case_type: 'positive',
  expected_decision: 'confident',
  expected_intent: 'it_api_timeout',
  actual_decision: 'confident',
  actual_intent: 'program_supported_question',
  actual_route_key: null,
  confidence: 1,
  result: 'FAIL',
  reason: 'actual intent did not match expected intent',
  ...overrides,
});

describe('buildTestRunInsights', () => {
  it('prioritizes intent mismatch when expected and actual intents differ repeatedly', () => {
    const insights = buildTestRunInsights([
      result({ case_id: 'P001', expected_intent: 'it_api_timeout', actual_intent: 'program_supported_question' }),
      result({ case_id: 'P002', expected_intent: 'it_api_timeout', actual_intent: 'program_supported_question' }),
      result({ case_id: 'P003', expected_intent: 'it_password_reset', actual_intent: 'risk_personal_data_included' }),
    ]);

    expect(insights.primaryProblem).toBe('기대 Intent와 실제 Intent가 다른 실패가 가장 먼저 보입니다.');
    expect(insights.patterns[0]).toEqual({
      key: 'it_api_timeout→program_supported_question',
      expected: 'it_api_timeout',
      actual: 'program_supported_question',
      count: 2,
      kind: 'intent_mismatch',
    });
    expect(insights.nextActions).toContain('it_api_timeout Intent 예시를 보강하세요.');
  });

  it('detects fallback concentration and suggests catalog example reinforcement', () => {
    const insights = buildTestRunInsights([
      result({
        case_id: 'P009',
        expected_intent: 'it_vpn_access',
        actual_decision: 'fallback',
        actual_intent: null,
        confidence: 0.024,
        reason: 'actual decision did not match expected decision',
      }),
      result({
        case_id: 'P010',
        expected_intent: 'it_vpn_access',
        actual_decision: 'fallback',
        actual_intent: null,
        confidence: 0.024,
        reason: 'actual decision did not match expected decision',
      }),
    ]);

    expect(insights.primaryProblem).toBe('분류 실패로 떨어진 케이스가 먼저 보입니다.');
    expect(insights.nextActions).toContain('it_vpn_access 관련 표현을 Catalog 예시에 추가하세요.');
  });

  it('classifies by backend reason before fallback decision value', () => {
    const insights = buildTestRunInsights([
      result({
        case_id: 'P011',
        expected_decision: 'fallback',
        expected_intent: 'it_vpn_access',
        actual_decision: 'fallback',
        actual_intent: 'program_supported_question',
        reason: 'actual intent did not match expected intent',
      }),
    ]);

    expect(insights.patterns[0].kind).toBe('intent_mismatch');
  });

  it('includes review-rate guidance when diagnostics reports review guidance', () => {
    const diagnostics = {
      primary_issue: null,
      issues: [{ code: 'review_rate_above_guidance', severity: 'recommendation', evidence: {} }],
      catalog_version: {} as API.TestRunCatalogVersionDiagnostics,
      result_counts: { FAIL: 15, REVIEW: 5, PASS: 5 },
      actual_decision_counts: { confident: 9, risk: 5, clarify: 7, fallback: 4 },
    };

    const insights = buildTestRunInsights([], diagnostics);

    expect(insights.nextActions).toContain(
      '검토 케이스를 확인하고 모호한 질의를 각 Intent 예시에 보강하세요.',
    );
  });
});
```

- [ ] **Step 2: Run the insights test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunResultInsights.test.ts
```

Expected: FAIL because `testRunResultInsights.ts` does not exist.

- [ ] **Step 3: Implement the insights helper**

Create `frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.ts`:

```ts
export type TestRunPatternKind = 'intent_mismatch' | 'decision_mismatch' | 'fallback';

export type TestRunPattern = {
  key: string;
  expected: string;
  actual: string;
  count: number;
  kind: TestRunPatternKind;
};

export type TestRunInsights = {
  primaryProblem: string;
  impactBullets: string[];
  patterns: TestRunPattern[];
  nextActions: string[];
};

const issueCodes = (diagnostics?: API.TestRunDiagnostics) =>
  new Set((diagnostics?.issues ?? []).map((issue) => issue.code));

const topPatterns = (patterns: TestRunPattern[]) =>
  [...patterns].sort((left, right) => right.count - left.count || left.key.localeCompare(right.key)).slice(0, 5);

export function buildTestRunInsights(
  results: API.TestRunResult[],
  diagnostics?: API.TestRunDiagnostics,
): TestRunInsights {
  const failed = results.filter((row) => row.result.toUpperCase() === 'FAIL');
  const patternMap = new Map<string, TestRunPattern>();

  for (const row of failed) {
    const expected = row.expected_intent ?? row.expected_decision;
    const actual = row.actual_intent ?? row.actual_route_key ?? row.actual_decision;
    let kind: TestRunPatternKind | undefined;
    if (row.reason === 'actual intent did not match expected intent') kind = 'intent_mismatch';
    else if (row.reason === 'actual decision did not match expected decision') kind = 'decision_mismatch';
    else if (row.actual_decision === 'fallback') kind = 'fallback';
    if (!kind) continue;

    const key = `${expected}→${actual}`;
    const previous = patternMap.get(key);
    patternMap.set(key, {
      key,
      expected,
      actual,
      kind,
      count: (previous?.count ?? 0) + 1,
    });
  }

  const allPatterns = [...patternMap.values()];
  const patterns = topPatterns(allPatterns);
  const codes = issueCodes(diagnostics);
  const fallbackPattern = allPatterns.find((pattern) => pattern.kind === 'fallback');
  const mismatchPattern = allPatterns.find((pattern) => pattern.kind === 'intent_mismatch');

  const primaryProblem = fallbackPattern && !mismatchPattern
    ? '분류 실패로 떨어진 케이스가 먼저 보입니다.'
    : mismatchPattern
      ? '기대 Intent와 실제 Intent가 다른 실패가 가장 먼저 보입니다.'
      : codes.has('pass_rate_below_gate')
        ? '통과율이 Release 기준보다 낮습니다.'
        : '진단 가능한 주요 패턴이 없습니다.';

  const impactBullets = [
    failed.length ? `실패 ${failed.length}건을 먼저 확인해야 합니다.` : '실패 케이스가 없습니다.',
    diagnostics?.result_counts
      ? `결과 집계: 실패 ${diagnostics.result_counts.FAIL ?? 0}건, 검토 ${diagnostics.result_counts.REVIEW ?? 0}건, 통과 ${diagnostics.result_counts.PASS ?? 0}건입니다.`
      : `결과 집계: 실패 ${failed.length}건입니다.`,
  ];

  const nextActions = new Set<string>();
  for (const pattern of patterns) {
    if (pattern.kind === 'fallback') {
      nextActions.add(`${pattern.expected} 관련 표현을 Catalog 예시에 추가하세요.`);
    } else if (pattern.kind === 'intent_mismatch') {
      nextActions.add(`${pattern.expected} Intent 예시를 보강하세요.`);
    } else if (pattern.kind === 'decision_mismatch') {
      nextActions.add(`${pattern.expected}의 기대 결정과 위험/검토 기준을 점검하세요.`);
    }
  }
  if (patterns.some((pattern) => pattern.actual === 'program_supported_question')) {
    nextActions.add('program_supported_question이 구체 Intent를 과도하게 흡수하는지 점검하세요.');
  }
  if (codes.has('review_rate_above_guidance')) {
    nextActions.add('검토 케이스를 확인하고 모호한 질의를 각 Intent 예시에 보강하세요.');
  }
  if (codes.has('risk_case_failed')) {
    nextActions.add('위험 질문과 개인정보 포함 질문의 정책 기준을 다시 확인하세요.');
  }

  return {
    primaryProblem,
    impactBullets,
    patterns,
    nextActions: [...nextActions].slice(0, 5),
  };
}
```

- [ ] **Step 4: Run the insights tests**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunResultInsights.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.ts frontend/intent-routing-console/src/pages/TestRuns/testRunResultInsights.test.ts
git commit -m "feat: summarize test run failure patterns"
```

---

### Task 3: Reorder Diagnostics UI By Importance And Split Catalog Metadata Below The Table

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/TestRunCatalogStatusPanel.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
- Create or modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunCatalogStatusPanelContract.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`

**Interfaces:**
- Consumes:
  - `buildTestRunInsights(results, diagnostics)`
  - Korean copy functions from `testRunResultCopy.ts`
- Produces:
  - Page-level top-down UI order inside the result step:
    1. 진단 / 가장 먼저 확인할 문제
    2. 실패 패턴 요약
    3. 다음 조치
    4. 상세 결과
    5. Catalog / Vector 상태
- Note: `TestRunDiagnosticsPanel` owns sections 2-4 from the full wireframe. `TestRunCatalogStatusPanel` owns section 6 and must be rendered after the `ProTable` in `index.tsx`.

- [ ] **Step 1: Write the failing panel contract test**

Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts` by updating existing assertions and adding:

```ts
  it('orders diagnostic sections from most actionable to supporting metadata', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    const firstProblemIndex = source.indexOf('가장 먼저 확인할 문제');
    const patternIndex = source.indexOf('실패 패턴 요약');
    const nextActionIndex = source.indexOf('다음 조치');

    expect(firstProblemIndex).toBeGreaterThan(-1);
    expect(patternIndex).toBeGreaterThan(firstProblemIndex);
    expect(nextActionIndex).toBeGreaterThan(patternIndex);
    expect(source).not.toContain('Catalog / Vector 상태');
  });

  it('does not show raw diagnostic codes as the primary user-facing message', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('formatIssueTitle');
    expect(source).toContain('buildTestRunInsights');
    expect(source).toContain('program_supported_question이 구체 Intent를 과도하게 흡수');
    expect(source).not.toContain('label={`${issue.severity}: ${issue.code}`}');
  });
```

Update pre-existing contract assertions deliberately:
- If `issueTitleCopy` moves to `testRunResultCopy.ts`, assert that `TestRunDiagnosticsPanel.tsx` imports `formatIssueTitle` instead of requiring every issue-code literal in the panel file.
- Replace raw `label="결과 집계"` / `label="실제 결정 집계"` expectations with Korean prose expectations from `insights.impactBullets` and a localized actual-decision count display if the counts remain visible.
- Replace `'백엔드 진단에서 주요 이슈를 찾지 못했습니다.'` with the new empty-state copy only if the new design intentionally removes that sentence.

Create or update `testRunCatalogStatusPanelContract.test.ts`:

```ts
  it('renders catalog and vector metadata in its own panel', () => {
    const source = read('TestRunCatalogStatusPanel.tsx');

    expect(source).toContain('Catalog / Vector 상태');
    expect(source).toContain('준비된 vector index');
    expect(source).toContain('Test Run vector index');
  });
```

Add a cross-file page-order assertion to `testRunsPageContract.test.ts`:

```ts
  it('renders catalog and vector status after the detailed results table', () => {
    const source = read('index.tsx');

    const diagnosticsIndex = source.indexOf('<TestRunDiagnosticsPanel');
    const tableIndex = source.indexOf('<ProTable<API.TestRunResult>');
    const catalogStatusIndex = source.indexOf('<TestRunCatalogStatusPanel');

    expect(diagnosticsIndex).toBeGreaterThan(-1);
    expect(tableIndex).toBeGreaterThan(diagnosticsIndex);
    expect(catalogStatusIndex).toBeGreaterThan(tableIndex);
  });
```

- [ ] **Step 2: Run the panel contract test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunDiagnosticsPanelContract.test.ts
npm run test:unit -- testRunsPageContract.test.ts
```

Expected: FAIL because the new section titles and imports are not present.

- [ ] **Step 3: Lift diagnostics fetching to the page**

Move the `fetchTestRunDiagnostics` state/effect currently inside `TestRunDiagnosticsPanel.tsx` into `index.tsx` so one diagnostics response can feed both the actionable panel above the table and the catalog status panel below the table.

Add page-level state:

```ts
const [diagnostics, setDiagnostics] = useState<API.TestRunDiagnostics | null>(null);
const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);
const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);
```

Use the existing service request function and keep the same error behavior. Reset diagnostics when service, test run, or result step changes.

- [ ] **Step 4: Update `TestRunDiagnosticsPanel` props and rendering**

Change the props type:

```ts
type TestRunDiagnosticsPanelProps = {
  testRunId?: string;
  diagnostics?: API.TestRunDiagnostics | null;
  diagnosticsLoading?: boolean;
  diagnosticsError?: string | null;
  results?: API.TestRunResult[];
};
```

Import helpers:

```ts
import { Card, List } from 'antd';
import { buildTestRunInsights } from './testRunResultInsights';
import { formatIssueTitle } from './testRunResultCopy';
```

Compute insights after diagnostics:

```ts
const insights = useMemo(
  () => buildTestRunInsights(results ?? [], diagnostics ?? undefined),
  [diagnostics, results],
);
```

Replace the current diagnostic body with this order:

```tsx
<Space direction="vertical" size={12} style={{ width: '100%' }}>
  <Alert
    type={primaryIssue?.severity === 'blocker' ? 'error' : 'info'}
    showIcon
    message="가장 먼저 확인할 문제"
    description={
      <Space direction="vertical" size={6}>
        <Typography.Text strong>
          {primaryIssue ? formatIssueTitle(primaryIssue.code) : insights.primaryProblem}
        </Typography.Text>
        {insights.impactBullets.map((item) => (
          <Typography.Text key={item}>{item}</Typography.Text>
        ))}
      </Space>
    }
  />

  <Card size="small" title="실패 패턴 요약">
    {insights.patterns.length ? (
      <List
        size="small"
        dataSource={insights.patterns}
        renderItem={(pattern) => (
          <List.Item>
            <Space>
              <Typography.Text code>{pattern.expected}</Typography.Text>
              <Typography.Text>→</Typography.Text>
              <Typography.Text code>{pattern.actual}</Typography.Text>
              <StatusTag status={pattern.kind} label={`${pattern.count}건`} />
            </Space>
          </List.Item>
        )}
      />
    ) : (
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="집계된 실패 패턴이 없습니다." />
    )}
  </Card>

  <Card size="small" title="다음 조치">
    {insights.nextActions.length ? (
      <List
        size="small"
        dataSource={insights.nextActions}
        renderItem={(action, index) => (
          <List.Item>
            <Typography.Text>{index + 1}. {action}</Typography.Text>
          </List.Item>
        )}
      />
    ) : (
      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="추가 권장 조치가 없습니다." />
    )}
  </Card>

  <Space wrap>
    {diagnostics.issues.map((issue) => (
      <StatusTag
        key={issue.code}
        status={issue.severity}
        label={formatIssueTitle(issue.code)}
      />
    ))}
  </Space>
</Space>
```

- [ ] **Step 5: Create `TestRunCatalogStatusPanel`**

Create `frontend/intent-routing-console/src/pages/TestRuns/TestRunCatalogStatusPanel.tsx`.

Move the existing Catalog `Descriptions` content from `TestRunDiagnosticsPanel.tsx` into this component and keep all metadata available today:
- Catalog version id
- 상태
- 재현성
- Intent 수
- 예시 수
- Embedding 수
- 준비된 vector index
- Test Run vector index

Do not render raw diagnostic issue codes here; this panel is supporting metadata only.

- [ ] **Step 6: Wire the page-level order**

In `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`, update the panel call:

```tsx
<TestRunDiagnosticsPanel
  testRunId={summary?.test_run_id}
  diagnostics={diagnostics}
  diagnosticsLoading={diagnosticsLoading}
  diagnosticsError={diagnosticsError}
  results={results}
/>
```

Render `<TestRunCatalogStatusPanel diagnostics={diagnostics} />` immediately after the `ProTable`, so the final page order is:

```text
테스트 요약 → 가장 먼저 확인할 문제 → 실패 패턴 요약 → 다음 조치 → 상세 결과 → Catalog / Vector 상태
```

- [ ] **Step 7: Run panel and page contract tests**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunDiagnosticsPanelContract.test.ts
npm run test:unit -- testRunCatalogStatusPanelContract.test.ts
npm run test:unit -- testRunsPageContract.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx frontend/intent-routing-console/src/pages/TestRuns/TestRunCatalogStatusPanel.tsx frontend/intent-routing-console/src/pages/TestRuns/index.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts frontend/intent-routing-console/src/pages/TestRuns/testRunCatalogStatusPanelContract.test.ts frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts
git commit -m "feat: prioritize actionable test run diagnostics"
```

---

### Task 4: Korean Detailed Result Table Rendering

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`

**Interfaces:**
- Consumes:
  - `formatDecisionLabel`
  - `formatIntentLabel`
  - `formatResultReason`
- Produces:
  - Table cells that show Korean decision labels and Korean reason text.

- [ ] **Step 1: Write the failing page contract test**

Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts` by adding:

```ts
  it('renders detailed result decisions and reasons with Korean copy helpers', () => {
    const source = read('index.tsx');

    expect(source).toContain('formatDecisionLabel');
    expect(source).toContain('formatIntentLabel');
    expect(source).toContain('formatResultReason');
    expect(source).toContain('title={row.reason}');
    expect(source).toContain('render: (_, row) => (');
    expect(source).toContain('{formatResultReason(row.reason)}');
  });
```

- [ ] **Step 2: Run the contract test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunsPageContract.test.ts
```

Expected: FAIL because the table still renders raw values.

- [ ] **Step 3: Import copy helpers**

In `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`, add:

```ts
import {
  formatDecisionLabel,
  formatIntentLabel,
  formatResultReason,
} from './testRunResultCopy';
```

- [ ] **Step 4: Render Korean expected and actual results**

Replace expected result rendering with:

```tsx
render: (_, row) => (
  <Space direction="vertical" size={0}>
    <span>{formatDecisionLabel(row.expected_decision)}</span>
    <span className="muted-small">{formatIntentLabel(row.expected_intent)}</span>
  </Space>
),
```

Replace actual result rendering with:

```tsx
render: (_, row) => (
  <Space direction="vertical" size={0}>
    <span>{formatDecisionLabel(row.actual_decision)}</span>
    <span className="muted-small">
      {formatIntentLabel(row.actual_intent ?? row.actual_route_key)}
    </span>
  </Space>
),
```

- [ ] **Step 5: Render Korean reason with original reason as secondary detail**

Replace the current reason column with:

```tsx
{
  title: '사유',
  dataIndex: 'reason',
  search: false,
  ellipsis: true,
  render: (_, row) => (
    <Typography.Text title={row.reason}>
      {formatResultReason(row.reason)}
    </Typography.Text>
  ),
},
```

- [ ] **Step 6: Run page contract test**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunsPageContract.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/index.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts
git commit -m "feat: localize test run result table"
```

---

### Task 5: Summary Block And Recommendation Copy Koreanization

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`

**Interfaces:**
- Consumes:
  - `formatBlockReason`
  - `formatRecommendation`
- Produces:
  - Korean `차단 사유` and `권장 조치` values in Test Run summary.

- [ ] **Step 1: Write the failing test**

Add to `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`:

```ts
  it('renders summary block reasons and recommendations in Korean', () => {
    const source = read('index.tsx');

    expect(source).toContain('formatBlockReason');
    expect(source).toContain('formatRecommendation');
    expect(source).not.toContain('summary.block_reasons.join');
    expect(source).not.toContain('summary.recommendations.join');
  });
```

- [ ] **Step 2: Run the page contract test to verify it fails**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunsPageContract.test.ts
```

Expected: FAIL because raw joins are still used.

- [ ] **Step 3: Import summary copy helpers**

Extend the `testRunResultCopy` import:

```ts
import {
  formatBlockReason,
  formatDecisionLabel,
  formatIntentLabel,
  formatRecommendation,
  formatResultReason,
} from './testRunResultCopy';
```

- [ ] **Step 4: Replace summary raw joins**

Replace `차단 사유` content with:

```tsx
{summary.block_reasons.length
  ? summary.block_reasons.map(formatBlockReason).join(', ')
  : '없음'}
```

Replace `권장 조치` content with:

```tsx
{summary.recommendations.length
  ? summary.recommendations.map(formatRecommendation).join(', ')
  : '없음'}
```

- [ ] **Step 5: Run page contract test**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- testRunsPageContract.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/index.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts
git commit -m "feat: localize test run summary guidance"
```

---

### Task 6: Full Frontend Verification And Guardrail Search

**Files:**
- Verify only. Do not modify files unless a command fails.

**Interfaces:**
- Consumes all previous task outputs.
- Produces verified branch state ready for review.

- [ ] **Step 1: Run focused Test Runs tests**

Run:

```bash
cd frontend/intent-routing-console
npm run test:unit -- TestRuns
```

Expected: PASS for Test Runs related tests.

- [ ] **Step 2: Run broader frontend checks available in package scripts**

Run:

```bash
cd frontend/intent-routing-console
npm run typecheck
npm run test:unit
```

Expected: PASS. If `typecheck` is not defined in `package.json`, run the repository's closest TypeScript verification script listed in `package.json` and record the exact command.

- [ ] **Step 3: Run Admin UI prohibited-pattern search**

Run:

```bash
command -v rg
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/pages/TestRuns frontend/intent-routing-console/src/services/adminServices.ts
```

Expected: no implementation matches. Documentation-only matches are acceptable only if they explicitly prohibit those patterns. If `rg` is not available in the execution shell, use:

```bash
grep -rnE "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/pages/TestRuns frontend/intent-routing-console/src/services/adminServices.ts
```

- [ ] **Step 4: Run Admin UI color guardrail search**

Run:

```bash
command -v rg
rg -n "<Tag[^\\n]*\\bcolor=|darkAlgorithm|color-scheme:\\s*dark|background(-color)?\\s*:\\s*#0|background(-color)?\\s*:\\s*#1" frontend/intent-routing-console/src/pages/TestRuns frontend/intent-routing-console/src/global.less
```

Expected: no new semantic `Tag color` or near-dark content-surface matches in changed Test Runs files. If `rg` is not available in the execution shell, use:

```bash
grep -rnE "<Tag[^\\n]*\\bcolor=|darkAlgorithm|color-scheme:\\s*dark|background(-color)?\\s*:\\s*#0|background(-color)?\\s*:\\s*#1" frontend/intent-routing-console/src/pages/TestRuns frontend/intent-routing-console/src/global.less
```

- [ ] **Step 5: Manual desktop visual verification**

Open the Test Runs page in the local dev browser and verify the FHD desktop order:

```text
1. 테스트 요약
2. 가장 먼저 확인할 문제
3. 실패 패턴 요약
4. 다음 조치
5. 상세 결과
6. Catalog / Vector 상태
```

Acceptance:
- No visible English result reason in the detailed table.
- Diagnostic issue codes are not the primary text.
- `Catalog / Vector 상태` is below the action-oriented sections.
- Table columns remain readable in a narrowed desktop browser window.

- [ ] **Step 6: Commit verification-only fixes if needed**

If verification required a fix, commit the exact files:

```bash
git add <fixed-files>
git commit -m "fix: verify actionable test run diagnostics ux"
```

If no fixes were required, do not create an empty commit.

---

## Wireframe Acceptance Order

The implementation must preserve this top-to-bottom order on the Test Run result step:

```text
┌────────────────────────────────────────────┐
│ 1. 테스트 요약                              │
│ - Release 차단 여부                         │
│ - 통과율 / 검토율 / 위험 통과율              │
│ - 한글 차단 사유 / 한글 권장 조치            │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ 2. 가장 먼저 확인할 문제                    │
│ - 주요 진단 문장                            │
│ - 영향 범위                                 │
│ - 우선 확인 대상 Intent                     │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ 3. 실패 패턴 요약                           │
│ - 기대 Intent → 실제 Intent TOP             │
│ - Decision mismatch TOP                     │
│ - fallback 집중 Intent                      │
│ - risk 오분류 케이스                         │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ 4. 다음 조치                                │
│ - Intent 예시 보강                           │
│ - catch-all Intent 범위 조정                 │
│ - risk/off-topic 기준 점검                   │
│ - clarify 케이스 검토                        │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ 5. 상세 결과                                │
│ - 케이스별 기대/실제/신뢰도/결과/한글 사유   │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ 6. Catalog / Vector 상태                    │
│ - Catalog active / complete                 │
│ - Intent 수 / 예시 수 / Embedding 수         │
│ - 준비된 vector index / Test Run vector index│
└────────────────────────────────────────────┘
```

---

## Claude Review Decisions

Review report: `docs/superpowers/reviews/2026-07-21-test-run-results-actionable-diagnostics-ux-claude-review-20260721-134341-438541.md`

- F-1 accepted: `reason` copy now covers the five backend-produced literals from `_compare_result`, including `requires human inspection` and `matched expected decision`.
- F-2 accepted: existing diagnostics panel contract assertions must be updated deliberately instead of silently removed. Raw JSON count displays should either be replaced with Korean prose or preserved as localized count summaries.
- F-3 accepted: `Catalog / Vector 상태` cannot be below the detailed table while it remains inside `TestRunDiagnosticsPanel`; the plan now splits catalog metadata into `TestRunCatalogStatusPanel` rendered after `ProTable`.
- F-4 accepted: verification commands now use `npm run test:unit` and remove the Jest-only serial-execution flag.
- F-5 accepted: decision copy now includes `off_topic` and `unauthorized`.
- F-6 partially accepted: implementation should map pattern `StatusTag` statuses to existing semantic statuses if grey tags make the summary hard to scan; do not expand shared status tokens unless necessary.
- F-7 accepted: `primaryProblem` detection uses unsliced `allPatterns`; `topPatterns` is display-only.
- F-8 accepted: pattern classification uses backend `reason` before the fallback decision value.
- F-9 accepted: the page contract test now uses positive render assertions instead of a fragile multi-line negative assertion.
- F-10 accepted: issue copy keeps the backend trigger semantics for `intent_mismatch_exists` and `fallback_failures_dominant`.
- F-11 deferred: transient empty `results` behavior is a known lifecycle risk. If it appears during implementation, distinguish "results loading or failed" from "loaded with no failures"; do not block the first implementation on this unless the UI visibly contradicts diagnostics.

---

## Self-Review

- Spec coverage: The plan covers Korean result reasons, Korean diagnostic copy, importance-based section ordering, failure pattern summary, next actions, detailed table copy, and desktop Admin UI verification.
- Placeholder scan: No TBD/TODO placeholders are present.
- Type consistency: Helper names are defined in Task 1 and Task 2 before later tasks consume them.
- Scope check: The plan is frontend-focused and does not require backend contract changes because current API responses already include summary, result rows, diagnostics issues, result counts, and actual decision counts.
- Review incorporation: Claude plan-review blocker findings F-1 through F-5 are reflected in the executable plan before implementation begins.
