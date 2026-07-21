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
