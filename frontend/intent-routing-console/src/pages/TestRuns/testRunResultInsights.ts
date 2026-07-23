import {
  formatBlockReason,
  formatDecisionLabel,
  formatIntentLabel,
  formatRecommendation,
  formatReleaseGateLabel,
} from './testRunResultCopy';

export type TestRunPatternKind = 'intent_mismatch' | 'decision_mismatch' | 'fallback' | 'route_key_mismatch';
export type TestRunResultsLoadState = 'not_loaded' | 'loading' | 'error' | 'loaded';
export type TestRunPatternValueType = 'intent' | 'decision' | 'route_key';

export type TestRunPattern = {
  key: string;
  expected: string;
  actual: string;
  expectedValueType: TestRunPatternValueType;
  actualValueType: TestRunPatternValueType;
  count: number;
  kind: TestRunPatternKind;
  caseIds: string[];
};

export type TestRunNextAction = {
  key: string;
  status: string;
  title: string;
  targetLabel: string;
  caseIds: string[];
  summary: string;
  helpSteps: string[];
};

export type TestRunInsights = {
  primaryProblem: string;
  impactBullets: string[];
  patterns: TestRunPattern[];
  nextActions: TestRunNextAction[];
};

export type TestRunDatasetComposition = {
  classificationCount: number;
  riskCount: number;
  totalCount: number;
  summary: string;
  sourceIsUnavailable: boolean;
};

export type TestRunReleaseReadiness = {
  gateLabel: string;
  status: 'pass' | 'blocked' | 'unknown';
  blockerMessages: string[];
  recommendationMessages: string[];
  datasetComposition: TestRunDatasetComposition;
};

const issueCodes = (diagnostics?: API.TestRunDiagnostics) =>
  new Set((diagnostics?.issues ?? []).map((issue) => issue.code));

const topPatterns = (patterns: TestRunPattern[]) =>
  [...patterns].sort((left, right) => right.count - left.count || left.key.localeCompare(right.key)).slice(0, 5);

const formatPatternValue = (value: string, valueType: TestRunPatternValueType) =>
  valueType === 'decision'
    ? formatDecisionLabel(value)
    : valueType === 'intent'
      ? formatIntentLabel(value)
      : value;

const caseIdList = (caseIds: string[]) =>
  caseIds.length ? caseIds.join(', ') : '대상 케이스 전체';

const diagnosticIssueRecommendations: Record<string, string> = {
  catalog_version_not_active: '활성화된 상태의 Catalog 버전을 선택하거나 현재 버전을 활성화한 뒤 테스트를 다시 실행하세요.',
  catalog_version_not_reproducible: '재현성 상태가 완전한 Catalog 버전을 준비한 뒤 테스트를 다시 실행하세요.',
  catalog_version_has_no_intents: 'Catalog 버전에 Intent를 등록하고 활성화한 뒤 테스트를 다시 실행하세요.',
  catalog_version_has_no_examples: 'Catalog의 각 Intent에 승인된 예시 데이터를 추가한 뒤 테스트를 다시 실행하세요.',
  catalog_version_has_no_ready_vector_index: '선택한 카탈로그 버전의 예시 검색 준비 상태를 확인한 뒤 테스트를 다시 실행하세요.',
  catalog_version_has_no_embeddings: 'Catalog 예시의 검색 준비 상태를 확인한 뒤 테스트를 다시 실행하세요.',
  test_run_vector_index_not_ready: 'Test Run에 연결된 Catalog 버전의 예시 검색 준비 상태를 확인한 뒤 테스트를 다시 실행하세요.',
  risk_case_failed: '위험 질문과 개인정보 포함 질문의 정책 기준 및 예상을 다시 확인하세요.',
  fallback_failures_dominant: '분류 실패가 많은 Intent의 예시 표현을 보강한 뒤 테스트를 다시 실행하세요.',
  intent_mismatch_exists: '기대한 분류와 실제 연결 결과가 다른 케이스의 기대값 또는 예시 데이터를 보강하세요.',
  pass_rate_below_gate: '실패 패턴을 수정한 뒤 통과율이 Release 기준을 넘는지 다시 확인하세요.',
  review_rate_above_guidance: '검토 케이스의 모호한 질의를 각 Intent 예시에 보강하세요.',
};

const catalogReadinessIssueCodes = new Set([
  'catalog_version_not_active',
  'catalog_version_not_reproducible',
  'catalog_version_has_no_intents',
  'catalog_version_has_no_examples',
  'catalog_version_has_no_ready_vector_index',
  'catalog_version_has_no_embeddings',
  'test_run_vector_index_not_ready',
]);

export function formatDiagnosticIssueRecommendation(code?: string | null) {
  if (!code) return '진단 내용을 확인하고 설정과 데이터를 점검하세요.';
  return diagnosticIssueRecommendations[code] ?? '진단 내용을 확인하고 설정과 데이터를 점검하세요.';
}

export function buildDatasetComposition(
  results: API.TestRunResult[],
): TestRunDatasetComposition {
  const classificationCount = results.filter((row) => row.case_type !== 'risk').length;
  const riskCount = results.filter((row) => row.case_type === 'risk').length;
  const totalCount = results.length;

  return {
    classificationCount,
    riskCount,
    totalCount,
    summary: `분류 테스트 ${classificationCount}건 + 위험 테스트 ${riskCount}건 = 총 ${totalCount}건`,
    sourceIsUnavailable: true,
  };
}

export function buildActualDecisionCounts(results: API.TestRunResult[]) {
  return results.reduce<Record<string, number>>((counts, row) => {
    if (row.actual_decision) {
      counts[row.actual_decision] = (counts[row.actual_decision] ?? 0) + 1;
    }
    return counts;
  }, {});
}

export function buildReleaseReadiness(
  summary?: API.TestRunSummary,
  results?: API.TestRunResult[],
): TestRunReleaseReadiness {
  return {
    gateLabel: summary ? formatReleaseGateLabel(summary.gate_passed) : 'Release 상태 확인 필요',
    status: summary ? (summary.gate_passed ? 'pass' : 'blocked') : 'unknown',
    blockerMessages: (summary?.block_reasons ?? []).map(formatBlockReason),
    recommendationMessages: (summary?.recommendations ?? []).map(formatRecommendation),
    datasetComposition: buildDatasetComposition(results ?? []),
  };
}

export function buildTestRunInsights(
  results: API.TestRunResult[],
  diagnostics?: API.TestRunDiagnostics,
  resultsLoadState: TestRunResultsLoadState = 'loaded',
): TestRunInsights {
  const failed = results.filter((row) => row.result.toUpperCase() === 'FAIL');
  const reviewCaseIds = results
    .filter((row) => row.result.toUpperCase() === 'REVIEW')
    .map((row) => row.case_id);
  const riskFailureCaseIds = failed
    .filter((row) => row.case_type === 'risk')
    .map((row) => row.case_id);
  const patternMap = new Map<string, TestRunPattern>();

  for (const row of failed) {
    let kind: TestRunPatternKind | undefined;
    if (row.reason === 'actual intent did not match expected intent') kind = 'intent_mismatch';
    else if (row.actual_decision === 'fallback') kind = 'fallback';
    else if (row.reason === 'actual decision did not match expected decision') kind = 'decision_mismatch';
    else if (row.reason === 'actual route key did not match expected route key') kind = 'route_key_mismatch';
    if (!kind) continue;

    const expectedValueType = kind === 'decision_mismatch' || row.expected_intent === null
      ? 'decision'
      : 'intent';
    const actualValueType = kind === 'route_key_mismatch'
      ? 'route_key'
      : kind === 'decision_mismatch' || (row.actual_intent === null && row.actual_route_key === null)
      ? 'decision'
      : 'intent';
    const expected = kind === 'decision_mismatch'
      ? row.expected_decision
      : row.expected_intent ?? row.expected_decision;
    const actual = kind === 'decision_mismatch'
      ? row.actual_decision
      : kind === 'route_key_mismatch'
        ? row.actual_route_key ?? row.actual_decision
      : row.actual_intent ?? row.actual_route_key ?? row.actual_decision;
    const key = `${kind}:${expected}→${actual}`;
    const previous = patternMap.get(key);
    patternMap.set(key, {
      key,
      expected,
      actual,
      expectedValueType,
      actualValueType,
      kind,
      count: (previous?.count ?? 0) + 1,
      caseIds: [...(previous?.caseIds ?? []), row.case_id],
    });
  }

  const allPatterns = [...patternMap.values()];
  const patterns = topPatterns(allPatterns);
  const codes = issueCodes(diagnostics);
  const fallbackPattern = allPatterns.find((pattern) => pattern.kind === 'fallback');
  const mismatchPattern = allPatterns.find((pattern) => pattern.kind === 'intent_mismatch');
  const routeKeyMismatchPattern = allPatterns.find((pattern) => pattern.kind === 'route_key_mismatch');

  const primaryProblem = fallbackPattern && !mismatchPattern
    ? '분류 실패로 떨어진 케이스가 먼저 보입니다.'
    : mismatchPattern
      ? '기대한 분류와 실제 연결 결과가 다른 케이스를 먼저 확인하세요.'
      : routeKeyMismatchPattern
        ? '기대 라우팅 경로와 실제 라우팅 경로가 다른 실패가 보입니다.'
      : codes.has('pass_rate_below_gate')
        ? 'Release 기준 통과율을 넘지 못했습니다.'
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
          ...(reviewCaseIds.length
            ? [`검토 ${reviewCaseIds.length}건은 실패는 아니지만 Release 통과율을 낮춥니다.`]
            : []),
        ];

  const releaseActions: TestRunNextAction[] = [];
  const patternActions: TestRunNextAction[] = [];
  const addNextAction = (action: TestRunNextAction, priority: 'release' | 'pattern' = 'pattern') => {
    const allActions = [...releaseActions, ...patternActions];
    if (allActions.some((item) => item.key === action.key)) return;
    (priority === 'release' ? releaseActions : patternActions).push(action);
  };

  const issueAction = (code: string): TestRunNextAction | null => {
    if (catalogReadinessIssueCodes.has(code)) {
      return {
        key: `issue:${code}`,
        status: 'blocker',
        title: 'Catalog 버전 준비 상태 확인',
        targetLabel: '전체 테스트',
        caseIds: results.map((row) => row.case_id),
        summary: formatDiagnosticIssueRecommendation(code),
        helpSteps: [
          'Test Runs 화면의 Intent Catalog 선택 단계에서 현재 선택한 Catalog 버전이 활성화된 상태인지 확인합니다.',
          'Intent Catalog 화면에서 해당 버전에 Intent와 승인된 예시가 들어 있는지 확인합니다.',
          'Intent Catalog 화면에서 Catalog 버전을 등록한 뒤 예시 검색 준비 상태를 확인합니다.',
          '준비가 끝나면 Test Runs 화면으로 돌아와 같은 CSV로 다시 실행합니다.',
        ],
      };
    }
    if (code === 'review_rate_above_guidance') {
      return {
        key: 'issue:review_rate_above_guidance',
        status: 'warning',
        title: '검토 필요한 케이스 줄이기',
        targetLabel: '전체 테스트',
        caseIds: reviewCaseIds,
        summary: '검토로 남은 질문은 시스템이 하나의 분류로 확정하기 어려운 케이스입니다.',
        helpSteps: [
          `Test Runs 화면의 상세 결과에서 ${caseIdList(reviewCaseIds)} 행을 확인합니다.`,
          '질문 표현이 애매하면 CSV의 질문을 실제 사용자 표현에 가깝게 다듬습니다.',
          '기대한 분류가 명확하다면 Intent Catalog 화면에서 해당 Intent의 Positive Example을 보강합니다.',
          '비슷한 다른 Intent와 자주 헷갈리면 Negative Example 또는 제외 키워드를 보강합니다.',
          'Intent Catalog 화면에서 Catalog 버전을 등록한 뒤 Test Runs 화면에서 다시 실행합니다.',
        ],
      };
    }
    if (code === 'risk_case_failed') {
      return {
        key: 'issue:risk_case_failed',
        status: 'blocker',
        title: '위험 질문 차단 결과 확인',
        targetLabel: '위험 테스트',
        caseIds: riskFailureCaseIds,
        summary: '위험 질문은 일반 분류보다 먼저 차단되어야 합니다.',
        helpSteps: [
          `Test Runs 화면의 상세 결과에서 ${caseIdList(riskFailureCaseIds)} 행이 위험 테스트 행인지와 실제 처리 결과를 확인합니다.`,
          'Test Runs 화면의 테스트 정책 설정에서 위험 정책 스위치가 켜져 있는지 확인합니다.',
          '필요하면 공통 위험 테스트 묶음과 후속 운영 문서를 확인해 해당 케이스의 기대 결과를 다시 점검합니다.',
          '조정이 필요하면 테스트 정책 설정의 정책 버전 생성 흐름으로 새 정책 버전을 만들고 현재 테스트에 선택합니다.',
          'Test Runs 화면에서 다시 실행합니다.',
        ],
      };
    }
    if (code === 'pass_rate_below_gate') {
      return {
        key: 'issue:pass_rate_below_gate',
        status: 'blocker',
        title: 'Release 기준 통과율 맞추기',
        targetLabel: '전체 테스트',
        caseIds: failed.map((row) => row.case_id),
        summary: 'Release 후보가 되려면 실패 케이스를 줄여 통과율 기준을 넘어야 합니다.',
        helpSteps: [
          `Test Runs 화면의 상세 결과에서 ${caseIdList(failed.map((row) => row.case_id))} 행을 먼저 확인합니다.`,
          '아래 실패 패턴별 조치가 있다면 각 패턴의 조치 방법을 먼저 적용합니다.',
          'CSV의 기대 분류가 잘못된 행은 CSV 가져오기에서 CSV 기대 분류를 수정합니다.',
          '분류 기준이 부족한 행은 Intent Catalog 화면에서 예시와 키워드를 보강합니다.',
          'Intent Catalog 화면에서 Catalog 버전을 등록한 뒤 Test Runs 화면에서 다시 실행합니다.',
        ],
      };
    }
    return null;
  };

  if (diagnostics?.primary_issue && catalogReadinessIssueCodes.has(diagnostics.primary_issue.code)) {
    const action = issueAction(diagnostics.primary_issue.code);
    if (action) addNextAction(action, 'release');
  }

  for (const pattern of patterns) {
    const expectedLabel = formatPatternValue(pattern.expected, pattern.expectedValueType);
    const actualLabel = formatPatternValue(pattern.actual, pattern.actualValueType);
    const targetLabel = `${expectedLabel} → ${actualLabel}`;
    if (pattern.kind === 'fallback') {
      addNextAction({
        key: `pattern:${pattern.key}`,
        status: pattern.kind,
        title: '분류 실패로 떨어진 케이스 보강',
        targetLabel,
        caseIds: pattern.caseIds,
        summary: `${pattern.count}건이 기대한 분류로 확정되지 못했습니다.`,
        helpSteps: [
          `Test Runs 화면의 상세 결과에서 ${caseIdList(pattern.caseIds)} 행의 질문을 확인합니다.`,
          '서비스가 처리해야 하는 질문이면 Intent Catalog 화면에서 기존 Intent의 Positive Example을 보강하거나 새 Intent를 추가합니다.',
          '서비스 범위 밖 질문이면 Catalog에 등록된 업무밖 Intent를 CSV 기대 분류로 쓰는지 확인합니다.',
          'Intent Catalog 화면에서 Catalog 버전을 등록한 뒤 Test Runs 화면에서 같은 CSV로 다시 실행합니다.',
        ],
      });
    } else if (pattern.kind === 'intent_mismatch') {
      addNextAction({
        key: `pattern:${pattern.key}`,
        status: pattern.kind,
        title: '기대한 분류와 실제 연결 결과가 다른 케이스 확인',
        targetLabel,
        caseIds: pattern.caseIds,
        summary: `${pattern.count}건이 CSV에 적은 기대 분류와 다른 곳으로 연결되었습니다.`,
        helpSteps: [
          `Test Runs 화면의 상세 결과에서 ${caseIdList(pattern.caseIds)} 행의 질문과 실제 결과를 확인합니다.`,
          `실제 연결 결과인 ${actualLabel}이 맞다면 CSV 가져오기에서 해당 행의 CSV 기대 분류를 수정합니다.`,
          `기대한 분류인 ${expectedLabel}이 맞다면 Intent Catalog 화면에서 ${expectedLabel}의 Positive Example을 비슷한 표현으로 보강합니다.`,
          `${actualLabel}이 너무 넓게 잡힌다면 해당 Intent의 Negative Example 또는 제외 키워드를 보강합니다.`,
          'Intent Catalog 화면에서 Catalog 버전을 등록한 뒤 Test Runs 화면에서 같은 CSV로 다시 실행합니다.',
        ],
      });
    } else if (pattern.kind === 'decision_mismatch') {
      addNextAction({
        key: `pattern:${pattern.key}`,
        status: pattern.kind,
        title: '기대 결과 유형과 실제 처리 방식 확인',
        targetLabel,
        caseIds: pattern.caseIds,
        summary: `${pattern.count}건의 처리 방식이 테스트 기대와 다릅니다.`,
        helpSteps: [
          `Test Runs 화면의 상세 결과에서 ${caseIdList(pattern.caseIds)} 행의 기대 결과와 실제 결과를 확인합니다.`,
          '위험 질문이어야 하는 케이스는 일반 CSV의 분류 기대값이 아니라 위험 테스트 기준으로 확인합니다.',
          '정상 분류 질문이라면 질문 안의 개인정보, 명령어, 프롬프트 우회 표현 때문에 위험 정책에 걸리지 않는지 확인합니다.',
          '테스트 설정의 정책 기준과 Intent Catalog 예시를 조정한 뒤 다시 실행합니다.',
        ],
      });
    } else if (pattern.kind === 'route_key_mismatch') {
      addNextAction({
        key: `pattern:${pattern.key}`,
        status: pattern.kind,
        title: '라우팅 경로 설정 확인',
        targetLabel,
        caseIds: pattern.caseIds,
        summary: `${pattern.count}건의 실제 연결 경로가 기대한 경로와 다릅니다.`,
        helpSteps: [
          `Test Runs 화면의 상세 결과에서 ${caseIdList(pattern.caseIds)} 행의 실제 라우팅 경로를 확인합니다.`,
          `Intent Catalog 화면에서 ${expectedLabel} Intent의 연결 경로 설정을 확인합니다.`,
          '서비스 코드가 기대하는 연결 경로와 Catalog의 연결 경로가 다르면 Intent 설정을 수정합니다.',
          'Intent Catalog 화면에서 Catalog 버전을 등록한 뒤 Test Runs 화면에서 다시 실행합니다.',
        ],
      });
    }
  }

  if (reviewCaseIds.length) {
    const action = issueAction('review_rate_above_guidance');
    if (action) addNextAction(action, 'release');
  }
  if (codes.has('review_rate_above_guidance')) {
    const action = issueAction('review_rate_above_guidance');
    if (action) addNextAction(action, 'release');
  }
  if (codes.has('risk_case_failed')) {
    const action = issueAction('risk_case_failed');
    if (action) addNextAction(action, 'release');
  }
  if (codes.has('pass_rate_below_gate')) {
    const action = issueAction('pass_rate_below_gate');
    if (action) addNextAction(action, 'release');
  }

  return {
    primaryProblem,
    impactBullets,
    patterns,
    nextActions: [...releaseActions, ...patternActions].slice(0, 5),
  };
}
