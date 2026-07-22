import { describe, expect, it } from 'vitest';
import {
  buildTestRunInsights,
  formatDiagnosticIssueRecommendation,
} from './testRunResultInsights';

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
      key: 'intent_mismatch:it_api_timeout→program_supported_question',
      expected: 'it_api_timeout',
      actual: 'program_supported_question',
      expectedValueType: 'intent',
      actualValueType: 'intent',
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

  it('keeps route-key mismatches visible with a route-key action', () => {
    const insights = buildTestRunInsights([
      result({
        case_id: 'RK001',
        actual_intent: 'it_api_timeout',
        actual_route_key: 'it.api_timeout.legacy',
        reason: 'actual route key did not match expected route key',
      }),
    ]);

    expect(insights.patterns).toContainEqual({
      key: 'route_key_mismatch:it_api_timeout→it.api_timeout.legacy',
      expected: 'it_api_timeout',
      actual: 'it.api_timeout.legacy',
      expectedValueType: 'intent',
      actualValueType: 'route_key',
      count: 1,
      kind: 'route_key_mismatch',
    });
    expect(insights.nextActions).toContain(
      'it_api_timeout Intent에 설정된 route_key와 실제 라우팅 경로를 점검하세요.',
    );
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

  it('keeps result-derived empty copy out of diagnostics until rows are loaded', () => {
    const notLoadedInsights = buildTestRunInsights([], undefined, 'not_loaded');
    const loadingInsights = buildTestRunInsights([], undefined, 'loading');
    const failedInsights = buildTestRunInsights([], undefined, 'error');

    expect(notLoadedInsights.impactBullets).toContain('상세 결과를 아직 불러오지 않았습니다.');
    expect(loadingInsights.impactBullets).toContain('상세 결과를 불러오는 중입니다.');
    expect(failedInsights.impactBullets).toContain('상세 결과를 불러오지 못했습니다.');
    expect(notLoadedInsights.impactBullets).not.toContain('실패 케이스가 없습니다.');
    expect(loadingInsights.impactBullets).not.toContain('실패 케이스가 없습니다.');
    expect(failedInsights.impactBullets).not.toContain('실패 케이스가 없습니다.');
  });

  it('uses decision values for decision mismatches and does not merge pattern kinds', () => {
    const insights = buildTestRunInsights([
      result({
        case_id: 'D001',
        expected_decision: 'confident',
        actual_decision: 'risk',
        expected_intent: 'shared_expected',
        actual_intent: 'shared_actual',
        reason: 'actual decision did not match expected decision',
      }),
      result({
        case_id: 'D002',
        expected_intent: 'shared_expected',
        actual_intent: 'shared_actual',
        reason: 'actual intent did not match expected intent',
      }),
    ]);

    expect(insights.patterns).toContainEqual({
      key: 'decision_mismatch:confident→risk',
      expected: 'confident',
      actual: 'risk',
      expectedValueType: 'decision',
      actualValueType: 'decision',
      count: 1,
      kind: 'decision_mismatch',
    });
    expect(insights.patterns).toContainEqual({
      key: 'intent_mismatch:shared_expected→shared_actual',
      expected: 'shared_expected',
      actual: 'shared_actual',
      expectedValueType: 'intent',
      actualValueType: 'intent',
      count: 1,
      kind: 'intent_mismatch',
    });
    expect(insights.nextActions).toContain('확정의 기대 결정과 위험/검토 기준을 점검하세요.');
    expect(insights.nextActions).not.toContain('confident의 기대 결정과 위험/검토 기준을 점검하세요.');
  });

  it('localizes fallback guidance when the expected intent is unavailable', () => {
    const insights = buildTestRunInsights([
      result({
        case_id: 'F001',
        expected_intent: null,
        expected_decision: 'clarify',
        actual_decision: 'fallback',
        actual_intent: null,
        actual_route_key: null,
        reason: 'actual decision did not match expected decision',
      }),
    ]);

    expect(insights.patterns).toContainEqual({
      key: 'fallback:clarify→fallback',
      expected: 'clarify',
      actual: 'fallback',
      expectedValueType: 'decision',
      actualValueType: 'decision',
      count: 1,
      kind: 'fallback',
    });
    expect(insights.nextActions).toContain('확인 필요 관련 표현을 Catalog 예시에 추가하세요.');
    expect(insights.nextActions).not.toContain('clarify 관련 표현을 Catalog 예시에 추가하세요.');
  });

  it('puts the primary catalog blocker action before pattern actions', () => {
    const diagnostics = {
      primary_issue: {
        code: 'catalog_version_has_no_ready_vector_index',
        severity: 'blocker',
        evidence: {},
      },
      issues: [],
      catalog_version: {} as API.TestRunCatalogVersionDiagnostics,
      result_counts: {},
      actual_decision_counts: {},
    } satisfies API.TestRunDiagnostics;
    const insights = buildTestRunInsights([
      result({ actual_decision: 'fallback', actual_intent: null, reason: 'actual decision did not match expected decision' }),
    ], diagnostics);

    expect(formatDiagnosticIssueRecommendation('catalog_version_has_no_ready_vector_index')).toBe(
      '선택한 카탈로그 버전의 벡터 인덱스를 준비 상태로 만든 뒤 테스트를 다시 실행하세요.',
    );
    expect(insights.nextActions[0]).toBe(
      '선택한 카탈로그 버전의 벡터 인덱스를 준비 상태로 만든 뒤 테스트를 다시 실행하세요.',
    );
  });
});
