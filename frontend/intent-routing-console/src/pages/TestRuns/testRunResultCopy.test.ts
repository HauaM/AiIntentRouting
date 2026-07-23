import { describe, expect, it } from 'vitest';
import {
  formatBlockReason,
  formatDecisionLabel,
  formatIntentLabel,
  formatIssueTitle,
  formatReleaseGateLabel,
  formatRecommendation,
  formatResultReason,
  formatRouterDecisionLabel,
  formatTestJudgmentLabel,
} from './testRunResultCopy';

describe('testRunResultCopy', () => {
  it('renders detailed result reasons in Korean', () => {
    expect(formatResultReason('actual intent did not match expected intent')).toBe(
      '기대한 분류와 실제 연결 결과가 다릅니다.',
    );
    expect(formatResultReason('actual decision did not match expected decision')).toBe(
      '기대한 처리와 실제 처리 결과가 다릅니다.',
    );
    expect(formatResultReason('requires human inspection')).toBe(
      '사람의 검토가 필요한 케이스입니다.',
    );
    expect(formatResultReason('matched expected decision')).toBe(
      '기대한 처리 결과와 일치합니다.',
    );
    expect(formatResultReason('matched expected decision and intent')).toBe(
      '기대한 분류와 실제 연결 결과가 일치합니다.',
    );
    expect(formatResultReason('matched expected decision, intent, and route key')).toBe(
      '기대한 분류와 실제 연결 결과가 일치합니다.',
    );
    expect(formatResultReason('actual route key did not match expected route key')).toBe(
      '기대한 연결 경로와 실제 연결 결과가 다릅니다.',
    );
  });

  it('keeps unknown result reasons Korean-only in visible copy', () => {
    expect(formatResultReason('custom backend reason')).toBe('판정 이유를 해석할 수 없습니다.');
    expect(formatResultReason('custom backend reason')).not.toContain('custom backend reason');
    expect(formatResultReason(null)).toBe('사유 없음');
  });

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

  it('renders decision labels in Korean', () => {
    expect(formatDecisionLabel('confident')).toBe('확정');
    expect(formatDecisionLabel('clarify')).toBe('확인 필요');
    expect(formatDecisionLabel('fallback')).toBe('분류 실패');
    expect(formatDecisionLabel('risk')).toBe('위험 차단');
    expect(formatDecisionLabel('off_topic')).toBe('업무 외 질문');
    expect(formatDecisionLabel('unauthorized')).toBe('권한 없음');
    expect(formatDecisionLabel(null)).toBe('없음');
    expect(formatDecisionLabel('future_backend_decision')).toBe('판단 값 확인 필요');
  });

  it('covers all backend-produced reason and decision values with Korean labels', () => {
    const backendReasons = [
      'matched expected decision',
      'requires human inspection',
      'matched expected decision and intent',
      'actual decision did not match expected decision',
      'actual intent did not match expected intent',
      'matched expected decision, intent, and route key',
      'actual route key did not match expected route key',
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
      '기대한 분류와 실제 연결 결과가 다른 케이스가 있습니다.',
    );
    expect(formatIssueTitle('intent_mismatch_exists')).not.toContain('Decision');
    expect(formatIssueTitle('fallback_failures_dominant')).toContain('분류 실패');
    expect(formatIssueTitle('fallback_failures_dominant')).not.toContain('fallback');
    expect(formatIssueTitle('pass_rate_below_gate')).toBe(
      'Release 기준 통과율을 넘지 못했습니다.',
    );
    expect(formatBlockReason('pass rate below 70%')).toBe('통과율이 70% 기준보다 낮습니다.');
    expect(formatBlockReason('risk cases required')).toBe(
      '위험 질문 차단 테스트 케이스가 필요합니다.',
    );
    expect(formatRecommendation('review rate above 15%')).toBe(
      '검토 대상 비율이 15% 권장 기준보다 높습니다.',
    );
  });

  it('keeps result and diagnostic copy free of internal backend terms', () => {
    const reasons = [
      'matched expected decision',
      'requires human inspection',
      'matched expected decision and intent',
      'actual decision did not match expected decision',
      'actual intent did not match expected intent',
      'matched expected decision, intent, and route key',
      'actual route key did not match expected route key',
    ];
    const issueCodes = [
      'catalog_version_has_no_intents',
      'catalog_version_has_no_examples',
      'catalog_version_has_no_ready_vector_index',
      'catalog_version_has_no_embeddings',
      'test_run_vector_index_not_ready',
      'intent_mismatch_exists',
    ];
    const visibleCopy = [
      ...reasons.map((reason) => formatResultReason(reason)),
      ...issueCodes.map((code) => formatIssueTitle(code)),
    ].join(' ');

    expect(visibleCopy).not.toMatch(/Decision|vector index|embedding|expected_intent|route_key/i);
    expect(formatIssueTitle('catalog_version_has_no_intents')).toBe(
      '선택한 Catalog 버전에 분류 항목이 없습니다.',
    );
    expect(formatIssueTitle('catalog_version_has_no_ready_vector_index')).toBe(
      '선택한 Catalog 버전의 예시 검색 준비가 완료되지 않았습니다.',
    );
    expect(formatIssueTitle('catalog_version_has_no_embeddings')).toBe(
      '선택한 Catalog 버전의 예시 검색 데이터가 준비되지 않았습니다.',
    );
  });

  it('keeps unknown diagnostic issue codes out of visible copy', () => {
    expect(formatIssueTitle('future_backend_issue')).toBe('해석되지 않은 진단 이슈입니다.');
    expect(formatIssueTitle('future_backend_issue')).not.toContain('future_backend_issue');
  });

  it('keeps unknown summary guidance Korean-only', () => {
    expect(formatBlockReason('future backend block reason')).toBe('차단 사유를 확인해 주세요.');
    expect(formatRecommendation('future backend recommendation')).toBe('권장 조치를 확인해 주세요.');
  });

  it('renders null intent values consistently', () => {
    expect(formatIntentLabel('it_api_timeout')).toBe('it_api_timeout');
    expect(formatIntentLabel(null)).toBe('인텐트 없음');
  });
});
