const decisionCopy: Record<string, string> = {
  confident: '확정',
  clarify: '확인 필요',
  fallback: '분류 실패',
  off_topic: '업무 외 질문',
  risk: '위험 차단',
  unauthorized: '권한 없음',
};

const routerDecisionCopy: Record<string, string> = {
  confident: '정상 연결',
  clarify: '추가 확인',
  fallback: '분류 실패',
  off_topic: '업무 외 질문',
  risk: '위험 차단',
  unauthorized: '권한 없음',
};

const testJudgmentCopy: Record<string, string> = {
  PASS: '통과',
  FAIL: '실패',
  REVIEW: '검토 필요',
};

const resultReasonCopy: Record<string, string> = {
  'actual intent did not match expected intent': '기대한 분류와 실제 연결 결과가 다릅니다.',
  'actual decision did not match expected decision': '기대한 처리와 실제 처리 결과가 다릅니다.',
  'matched expected decision': '기대한 처리 결과와 일치합니다.',
  'requires human inspection': '사람의 검토가 필요한 케이스입니다.',
  'matched expected decision and intent': '기대한 분류와 실제 연결 결과가 일치합니다.',
  'matched expected decision, intent, and route key': '기대한 분류와 실제 연결 결과가 일치합니다.',
  'actual route key did not match expected route key': '기대한 연결 경로와 실제 연결 결과가 다릅니다.',
};

const issueTitleCopy: Record<string, string> = {
  catalog_version_not_active: '선택한 Catalog 버전이 활성 상태가 아닙니다.',
  catalog_version_not_reproducible: '선택한 Catalog 버전의 재현성 상태가 완전하지 않습니다.',
  catalog_version_has_no_intents: '선택한 Catalog 버전에 분류 항목이 없습니다.',
  catalog_version_has_no_examples: '선택한 Catalog 버전에 예시 데이터가 없습니다.',
  catalog_version_has_no_ready_vector_index: '선택한 Catalog 버전의 예시 검색 준비가 완료되지 않았습니다.',
  catalog_version_has_no_embeddings: '선택한 Catalog 버전의 예시 검색 데이터가 준비되지 않았습니다.',
  test_run_vector_index_not_ready: 'Test Run의 예시 검색 준비 상태가 현재 Catalog 상태와 다릅니다.',
  risk_case_failed: '위험 케이스 중 실패한 항목이 있습니다.',
  fallback_failures_dominant: '실패한 케이스 중 분류 실패 결과 비율이 높습니다.',
  intent_mismatch_exists: '기대한 분류와 실제 연결 결과가 다른 케이스가 있습니다.',
  pass_rate_below_gate: 'Release 기준 통과율을 넘지 못했습니다.',
  review_rate_above_guidance: '검토 대상 비율이 권장 기준보다 높습니다.',
};

export function formatDecisionLabel(decision?: string | null) {
  if (!decision) return '없음';
  return decisionCopy[decision] ?? '판단 값 확인 필요';
}

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

export function formatIntentLabel(intent?: string | null) {
  return intent || '인텐트 없음';
}

export function formatResultReason(reason?: string | null) {
  if (!reason) return '사유 없음';
  return resultReasonCopy[reason] ?? '판정 이유를 해석할 수 없습니다.';
}

export function formatIssueTitle(code: string) {
  return issueTitleCopy[code] ?? '해석되지 않은 진단 이슈입니다.';
}

export function formatBlockReason(reason: string) {
  const passRateMatch = reason.match(/^pass rate below ([0-9]+)%$/);
  if (passRateMatch) return `통과율이 ${passRateMatch[1]}% 기준보다 낮습니다.`;
  if (reason === 'risk case failed') return '위험 질문 차단 테스트가 실패했습니다.';
  if (reason === 'risk cases required') return '위험 질문 차단 테스트 케이스가 필요합니다.';
  return '차단 사유를 확인해 주세요.';
}

export function formatRecommendation(recommendation: string) {
  const reviewRateMatch = recommendation.match(/^review rate above ([0-9]+)%$/);
  if (reviewRateMatch) {
    return `검토 대상 비율이 ${reviewRateMatch[1]}% 권장 기준보다 높습니다.`;
  }
  return '권장 조치를 확인해 주세요.';
}
