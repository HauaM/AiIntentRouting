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

  it('keeps unknown diagnostic issue codes out of visible copy', () => {
    expect(formatIssueTitle('future_backend_issue')).toBe('해석되지 않은 진단 이슈입니다.');
    expect(formatIssueTitle('future_backend_issue')).not.toContain('future_backend_issue');
  });

  it('renders null intent values consistently', () => {
    expect(formatIntentLabel('it_api_timeout')).toBe('it_api_timeout');
    expect(formatIntentLabel(null)).toBe('인텐트 없음');
  });
});
