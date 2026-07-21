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
  fallback_failures_dominant: '실패한 케이스 중 분류 실패 결과 비율이 높습니다.',
  intent_mismatch_exists: 'Decision은 맞았지만 Intent가 다른 실패가 있습니다.',
  pass_rate_below_gate: '통과율이 Release 기준보다 낮습니다.',
  review_rate_above_guidance: '검토 대상 비율이 권장 기준보다 높습니다.',
};

export function formatDecisionLabel(decision?: string | null) {
  if (!decision) return '없음';
  return decisionCopy[decision] ?? '판단 값 확인 필요';
}

export function formatIntentLabel(intent?: string | null) {
  return intent || '인텐트 없음';
}

export function formatResultReason(reason?: string | null) {
  if (!reason) return '사유 없음';
  return resultReasonCopy[reason] ?? '해석되지 않은 사유입니다.';
}

export function formatIssueTitle(code: string) {
  return issueTitleCopy[code] ?? '해석되지 않은 진단 이슈입니다.';
}

export function formatBlockReason(reason: string) {
  const passRateMatch = reason.match(/^pass rate below ([0-9]+)%$/);
  if (passRateMatch) return `통과율이 ${passRateMatch[1]}% 기준보다 낮습니다.`;
  if (reason === 'risk case failed') return '위험 질문 차단 테스트가 실패했습니다.';
  return '차단 사유를 확인해 주세요.';
}

export function formatRecommendation(recommendation: string) {
  const reviewRateMatch = recommendation.match(/^review rate above ([0-9]+)%$/);
  if (reviewRateMatch) {
    return `검토 대상 비율이 ${reviewRateMatch[1]}% 권장 기준보다 높습니다.`;
  }
  return '권장 조치를 확인해 주세요.';
}
