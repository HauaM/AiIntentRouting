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
    else if (row.actual_decision === 'fallback') kind = 'fallback';
    else if (row.reason === 'actual decision did not match expected decision') kind = 'decision_mismatch';
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
