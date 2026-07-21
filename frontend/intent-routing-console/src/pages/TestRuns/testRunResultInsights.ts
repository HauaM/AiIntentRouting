export type TestRunPatternKind = 'intent_mismatch' | 'decision_mismatch' | 'fallback';
export type TestRunResultsLoadState = 'not_loaded' | 'loading' | 'error' | 'loaded';

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

const diagnosticIssueRecommendations: Record<string, string> = {
  catalog_version_not_active: '활성 상태의 Catalog 버전을 선택하거나 현재 버전을 활성화한 뒤 테스트를 다시 실행하세요.',
  catalog_version_not_reproducible: '재현성 상태가 완전한 Catalog 버전을 준비한 뒤 테스트를 다시 실행하세요.',
  catalog_version_has_no_intents: 'Catalog 버전에 Intent를 등록하고 활성화한 뒤 테스트를 다시 실행하세요.',
  catalog_version_has_no_examples: 'Catalog의 각 Intent에 승인된 예시 데이터를 추가한 뒤 테스트를 다시 실행하세요.',
  catalog_version_has_no_ready_vector_index: '선택한 카탈로그 버전의 벡터 인덱스를 준비 상태로 만든 뒤 테스트를 다시 실행하세요.',
  catalog_version_has_no_embeddings: 'Catalog 예시의 embedding과 벡터 인덱스를 준비한 뒤 테스트를 다시 실행하세요.',
  test_run_vector_index_not_ready: 'Test Run에 연결된 벡터 인덱스가 준비 상태인지 확인한 뒤 테스트를 다시 실행하세요.',
  risk_case_failed: '위험 질문과 개인정보 포함 질문의 정책 기준 및 예상을 다시 확인하세요.',
  fallback_failures_dominant: '분류 실패가 많은 Intent의 예시 표현을 보강한 뒤 테스트를 다시 실행하세요.',
  intent_mismatch_exists: '기대 Intent와 실제 Intent가 다른 케이스의 예시 데이터를 보강하세요.',
  pass_rate_below_gate: '실패 패턴을 수정한 뒤 통과율이 Release 기준을 넘는지 다시 확인하세요.',
  review_rate_above_guidance: '검토 케이스의 모호한 질의를 각 Intent 예시에 보강하세요.',
};

export function formatDiagnosticIssueRecommendation(code?: string | null) {
  if (!code) return '진단 내용을 확인하고 설정과 데이터를 점검하세요.';
  return diagnosticIssueRecommendations[code] ?? '진단 내용을 확인하고 설정과 데이터를 점검하세요.';
}

export function buildTestRunInsights(
  results: API.TestRunResult[],
  diagnostics?: API.TestRunDiagnostics,
  resultsLoadState: TestRunResultsLoadState = 'loaded',
): TestRunInsights {
  const failed = results.filter((row) => row.result.toUpperCase() === 'FAIL');
  const patternMap = new Map<string, TestRunPattern>();

  for (const row of failed) {
    let kind: TestRunPatternKind | undefined;
    if (row.reason === 'actual intent did not match expected intent') kind = 'intent_mismatch';
    else if (row.actual_decision === 'fallback') kind = 'fallback';
    else if (row.reason === 'actual decision did not match expected decision') kind = 'decision_mismatch';
    if (!kind) continue;

    const expected = kind === 'decision_mismatch'
      ? row.expected_decision
      : row.expected_intent ?? row.expected_decision;
    const actual = kind === 'decision_mismatch'
      ? row.actual_decision
      : row.actual_intent ?? row.actual_route_key ?? row.actual_decision;
    const key = `${kind}:${expected}→${actual}`;
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

  const impactBullets = resultsLoadState === 'not_loaded'
    ? ['상세 결과를 아직 불러오지 않았습니다.']
    : resultsLoadState === 'loading'
    ? ['상세 결과를 불러오는 중입니다.']
    : resultsLoadState === 'error'
      ? ['상세 결과를 불러오지 못했습니다.']
      : [
          failed.length ? `실패 ${failed.length}건을 먼저 확인해야 합니다.` : '실패 케이스가 없습니다.',
          diagnostics?.result_counts
            ? `결과 집계: 실패 ${diagnostics.result_counts.FAIL ?? 0}건, 검토 ${diagnostics.result_counts.REVIEW ?? 0}건, 통과 ${diagnostics.result_counts.PASS ?? 0}건입니다.`
            : `결과 집계: 실패 ${failed.length}건입니다.`,
        ];

  const nextActions: string[] = [];
  const addNextAction = (action: string) => {
    if (!nextActions.includes(action)) nextActions.push(action);
  };
  if (diagnostics?.primary_issue) {
    addNextAction(formatDiagnosticIssueRecommendation(diagnostics.primary_issue.code));
  }
  for (const pattern of patterns) {
    if (pattern.kind === 'fallback') {
      addNextAction(`${pattern.expected} 관련 표현을 Catalog 예시에 추가하세요.`);
    } else if (pattern.kind === 'intent_mismatch') {
      addNextAction(`${pattern.expected} Intent 예시를 보강하세요.`);
    } else if (pattern.kind === 'decision_mismatch') {
      addNextAction(`${pattern.expected}의 기대 결정과 위험/검토 기준을 점검하세요.`);
    }
  }
  if (patterns.some((pattern) => pattern.actual === 'program_supported_question')) {
    addNextAction('program_supported_question이 구체 Intent를 과도하게 흡수하는지 점검하세요.');
  }
  if (codes.has('review_rate_above_guidance')) {
    addNextAction('검토 케이스를 확인하고 모호한 질의를 각 Intent 예시에 보강하세요.');
  }
  if (codes.has('risk_case_failed')) {
    addNextAction('위험 질문과 개인정보 포함 질문의 정책 기준을 다시 확인하세요.');
  }

  return {
    primaryProblem,
    impactBullets,
    patterns,
    nextActions: nextActions.slice(0, 5),
  };
}
