import { describe, expect, it } from 'vitest';
import {
  buildDatasetComposition,
  buildActualDecisionCounts,
  buildReleaseReadiness,
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

    expect(insights.primaryProblem).toBe('기대한 분류와 실제 연결 결과가 다른 케이스를 먼저 확인하세요.');
    expect(insights.patterns[0]).toEqual({
      key: 'intent_mismatch:it_api_timeout→program_supported_question',
      expected: 'it_api_timeout',
      actual: 'program_supported_question',
      expectedValueType: 'intent',
      actualValueType: 'intent',
      count: 2,
      kind: 'intent_mismatch',
      caseIds: ['P001', 'P002'],
    });
    expect(insights.nextActions[0]).toMatchObject({
      title: '기대한 분류와 실제 연결 결과가 다른 케이스 확인',
      targetLabel: 'it_api_timeout → program_supported_question',
      caseIds: ['P001', 'P002'],
    });
    expect(insights.nextActions[0].helpSteps.join('\n')).toContain('Intent Catalog 화면');
    expect(insights.nextActions[0].helpSteps.join('\n')).toContain('Test Runs 화면');
  });

  it('groups mismatch guidance by case id and separates CSV correction from catalog reinforcement', () => {
    const insights = buildTestRunInsights([
      result({
        case_id: 'P006',
        expected_intent: 'owner_contact_lookup',
        actual_intent: 'program_supported_question',
      }),
    ]);

    const action = insights.nextActions[0];
    const help = action.helpSteps.join('\n');

    expect(action.caseIds).toEqual(['P006']);
    expect(help).toContain('Test Runs 화면');
    expect(help).toContain('Intent Catalog 화면');
    expect(help).toContain('Intent Catalog 화면에서 Catalog 버전을 등록');
    expect(help).toContain('CSV 가져오기에서 해당 행의 CSV 기대 분류를 수정');
    expect(help).toContain('Positive Example을 비슷한 표현으로 보강');
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
    expect(insights.nextActions[0]).toMatchObject({
      title: '분류 실패로 떨어진 케이스 보강',
      targetLabel: 'it_vpn_access → 분류 실패',
      caseIds: ['P009', 'P010'],
    });
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
      caseIds: ['RK001'],
    });
    expect(insights.nextActions[0]).toMatchObject({
      title: '라우팅 경로 설정 확인',
      targetLabel: 'it_api_timeout → it.api_timeout.legacy',
      caseIds: ['RK001'],
    });
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

    expect(insights.nextActions[0]).toMatchObject({
      title: '검토 필요한 케이스 줄이기',
      targetLabel: '전체 테스트',
      caseIds: [],
    });
  });

  it('reserves release-impacting actions before lower-priority failure patterns', () => {
    const diagnostics = {
      primary_issue: {
        code: 'catalog_version_has_no_ready_vector_index',
        severity: 'blocker',
        evidence: {},
      },
      issues: [
        { code: 'review_rate_above_guidance', severity: 'recommendation', evidence: {} },
        { code: 'risk_case_failed', severity: 'blocker', evidence: {} },
        { code: 'pass_rate_below_gate', severity: 'blocker', evidence: {} },
      ],
      catalog_version: {} as API.TestRunCatalogVersionDiagnostics,
      result_counts: { PASS: 0, REVIEW: 1, FAIL: 6 },
      actual_decision_counts: {},
    } satisfies API.TestRunDiagnostics;
    const insights = buildTestRunInsights([
      result({ case_id: 'REVIEW-001', result: 'REVIEW', reason: 'requires human inspection' }),
      result({ case_id: 'I001', expected_intent: 'expected-a', actual_intent: 'actual-a' }),
      result({ case_id: 'I002', expected_intent: 'expected-b', actual_intent: 'actual-b' }),
      result({ case_id: 'I003', expected_intent: 'expected-c', actual_intent: 'actual-c' }),
      result({ case_id: 'I004', expected_intent: 'expected-d', actual_intent: 'actual-d' }),
      result({ case_id: 'I005', expected_intent: 'expected-e', actual_intent: 'actual-e' }),
      result({ case_id: 'RISK-001', case_type: 'risk', actual_decision: 'confident' }),
    ], diagnostics);

    expect(insights.nextActions).toHaveLength(5);
    expect(insights.nextActions.map((action) => action.title)).toEqual([
      'Catalog 버전 준비 상태 확인',
      '검토 필요한 케이스 줄이기',
      '위험 질문 차단 결과 확인',
      'Release 기준 통과율 맞추기',
      '기대한 분류와 실제 연결 결과가 다른 케이스 확인',
    ]);
  });

  it('derives actual decision counts from loaded result rows', () => {
    expect(buildActualDecisionCounts([
      result({ actual_decision: 'clarify' }),
      result({ actual_decision: 'risk' }),
      result({ actual_decision: 'clarify' }),
    ])).toEqual({ clarify: 2, risk: 1 });
  });

  it('summarizes classification and risk rows without inferring data provenance', () => {
    const composition = buildDatasetComposition([
      result({ case_id: 'risk-common-looking-custom-id', case_type: 'positive' }),
      result({ case_id: 'P002', case_type: 'positive' }),
      result({ case_id: 'RISK-CSV-001', case_type: 'risk' }),
    ]);

    expect(composition).toEqual({
      classificationCount: 2,
      riskCount: 1,
      totalCount: 3,
      summary: '분류 테스트 2건 + 위험 테스트 1건 = 총 3건',
      sourceIsUnavailable: true,
    });
  });

  it('builds release readiness from the gate, formatted guidance, and dataset composition', () => {
    const readiness = buildReleaseReadiness({
      gate_passed: false,
      block_reasons: ['pass rate below 70%', 'risk case failed'],
      recommendations: ['review rate above 15%'],
    } as API.TestRunSummary, [
      result({ case_id: 'P001', case_type: 'positive' }),
      result({ case_id: 'risk-common-abuse-001', case_type: 'risk' }),
      result({ case_id: 'risk-uploaded-001', case_type: 'risk' }),
    ]);

    expect(readiness).toMatchObject({
      gateLabel: 'Release 차단',
      status: 'blocked',
      blockerMessages: ['통과율이 70% 기준보다 낮습니다.', '위험 질문 차단 테스트가 실패했습니다.'],
      recommendationMessages: ['검토 대상 비율이 15% 권장 기준보다 높습니다.'],
      datasetComposition: {
        classificationCount: 1,
        riskCount: 2,
        totalCount: 3,
        summary: '분류 테스트 1건 + 위험 테스트 2건 = 총 3건',
        sourceIsUnavailable: true,
      },
    });
  });

  it('uses the supported pass status when a release is ready', () => {
    const readiness = buildReleaseReadiness({
      gate_passed: true,
      block_reasons: [],
      recommendations: [],
    } as unknown as API.TestRunSummary);

    expect(readiness.status).toBe('pass');
  });

  it('explains review rows as not failed but release-impacting', () => {
    const diagnostics = {
      primary_issue: null,
      issues: [],
      catalog_version: {} as API.TestRunCatalogVersionDiagnostics,
      result_counts: { PASS: 0, REVIEW: 1, FAIL: 0 },
      actual_decision_counts: { clarify: 1 },
    } satisfies API.TestRunDiagnostics;
    const insights = buildTestRunInsights([
      result({ case_id: 'P001', result: 'REVIEW', reason: 'requires human inspection' }),
    ], diagnostics, 'loaded');

    expect(insights.nextActions.some((action) => action.title === '검토 필요한 케이스 줄이기')).toBe(true);
    expect(insights.impactBullets).toContain('검토 1건은 실패는 아니지만 Release 통과율을 낮춥니다.');
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
      caseIds: ['D001'],
    });
    expect(insights.patterns).toContainEqual({
      key: 'intent_mismatch:shared_expected→shared_actual',
      expected: 'shared_expected',
      actual: 'shared_actual',
      expectedValueType: 'intent',
      actualValueType: 'intent',
      count: 1,
      kind: 'intent_mismatch',
      caseIds: ['D002'],
    });
    expect(insights.nextActions).toContainEqual(expect.objectContaining({
      title: '기대 결과 유형과 실제 처리 방식 확인',
      targetLabel: '확정 → 위험 차단',
      caseIds: ['D001'],
    }));
    expect(insights.nextActions.map((action) => action.targetLabel)).not.toContain('confident → risk');
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
      caseIds: ['F001'],
    });
    expect(insights.nextActions[0]).toMatchObject({
      title: '분류 실패로 떨어진 케이스 보강',
      targetLabel: '확인 필요 → 분류 실패',
      caseIds: ['F001'],
    });
  });

  it('attaches loaded result case IDs to the primary catalog readiness action', () => {
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
      '선택한 카탈로그 버전의 예시 검색 준비 상태를 확인한 뒤 테스트를 다시 실행하세요.',
    );
    expect(insights.nextActions[0]).toMatchObject({
      title: 'Catalog 버전 준비 상태 확인',
      targetLabel: '전체 테스트',
      caseIds: ['C001'],
    });
  });

  it('uses operator-facing language in next-action help steps', () => {
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
      result({
        case_id: 'RK001',
        actual_intent: 'it_api_timeout',
        actual_route_key: 'it.api_timeout.legacy',
        reason: 'actual route key did not match expected route key',
      }),
    ], diagnostics);

    const help = insights.nextActions.flatMap((action) => action.helpSteps).join('\n');

    expect(help).not.toMatch(/\bactive\b|\bembedding\b|\bvector index\b|\bexpected_intent\b|\broute_key\b/i);
    expect(help).toContain('활성화된 상태');
    expect(help).toContain('예시 검색 준비 상태');
    expect(help).toContain('연결 경로');
  });

  it('gives risk actions only through currently available operator workflows', () => {
    const diagnostics = {
      primary_issue: null,
      issues: [{ code: 'risk_case_failed', severity: 'blocker', evidence: {} }],
      catalog_version: {} as API.TestRunCatalogVersionDiagnostics,
      result_counts: { PASS: 0, REVIEW: 0, FAIL: 1 },
      actual_decision_counts: { confident: 1 },
    } satisfies API.TestRunDiagnostics;
    const insights = buildTestRunInsights([
      result({ case_id: 'RISK-001', case_type: 'risk', actual_decision: 'confident' }),
    ], diagnostics);
    const riskAction = insights.nextActions.find((action) => action.key === 'issue:risk_case_failed');
    const help = riskAction?.helpSteps.join('\n') ?? '';

    expect(help).toContain('위험 정책 스위치');
    expect(help).toContain('위험 테스트 행');
    expect(help).toContain('공통 위험 테스트 묶음');
    expect(help).toContain('정책 버전 생성 흐름');
    expect(help).toContain('다시 실행합니다.');
    expect(help).not.toMatch(/위험 정책 키워드|risk CSV|정책을 다시 저장/);
  });
});
