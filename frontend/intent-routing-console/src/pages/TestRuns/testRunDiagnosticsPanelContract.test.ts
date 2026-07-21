import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('TestRunDiagnosticsPanel contract after actionable diagnostics redesign', () => {
  it('receives page-owned diagnostics for the selected test run', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('diagnostics?: API.TestRunDiagnostics | null;');
    expect(source).toContain('diagnosticsLoading?: boolean;');
    expect(source).toContain('diagnosticsError?: string | null;');
    expect(source).toContain('results?: API.TestRunResult[];');
    expect(source).toContain('resultsLoadState?: TestRunResultsLoadState;');
    expect(source).toContain('primary_issue');
    expect(source).not.toContain('FutureFeatureNotice');
  });

  it('uses centralized Korean issue copy and actionable result insights', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('formatIssueTitle');
    expect(source).toContain('buildTestRunInsights');
    expect(source).toContain('insights.impactBullets');
    expect(source).not.toContain('issueCopy');
    expect(source).not.toContain('JSON.stringify');
  });

  it('keeps a visible Korean failure state when diagnostics loading fails', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('if (diagnosticsError) {');
    expect(source).toContain('message="진단 결과를 불러오지 못했습니다."');
    expect(source).toContain('description={diagnosticsError}');
    expect(source).toContain('조회된 진단 결과가 없습니다.');
  });

  it('orders diagnostic sections from most actionable to supporting metadata', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    const firstProblemIndex = source.indexOf('가장 먼저 확인할 문제');
    const patternIndex = source.indexOf('실패 패턴 요약');
    const nextActionIndex = source.indexOf('다음 조치');

    expect(firstProblemIndex).toBeGreaterThan(-1);
    expect(patternIndex).toBeGreaterThan(firstProblemIndex);
    expect(nextActionIndex).toBeGreaterThan(patternIndex);
    expect(source).not.toContain('Catalog / Vector 상태');
  });

  it('does not show raw diagnostic codes as the primary user-facing message', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('formatIssueTitle');
    expect(source).toContain('buildTestRunInsights');
    expect(source).not.toContain('label={`${issue.severity}: ${issue.code}`}');
  });

  it('maps failure patterns to supported semantic status tones', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain("intent_mismatch: 'warning'");
    expect(source).toContain("decision_mismatch: 'fail'");
    expect(source).toContain("fallback: 'fallback'");
    expect(source).toContain('status={patternStatus[pattern.kind]}');
    expect(source).not.toContain('status={pattern.kind}');
  });

  it('shows actual decision counts with localized decision labels', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('actual_decision_counts');
    expect(source).toContain('formatDecisionLabel');
    expect(source).toContain('실제 결정 분포');
    expect(source).toContain('Object.entries(diagnostics.actual_decision_counts)');
  });

  it('renders result-load-specific copy instead of empty findings until rows are loaded', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('description="진단 결과를 불러오는 중입니다."');
    expect(source).toContain('buildTestRunInsights(results ?? [], diagnostics ?? undefined, resultsLoadState)');
    expect(source).toContain("const resultSectionState = resultsLoadState === 'loaded'");
    expect(source).toContain("description={resultSectionState.patternDescription}");
    expect(source).toContain("description={resultSectionState.nextActionDescription}");
    expect(source).toContain("patternDescription: '상세 결과를 불러오지 못해 실패 패턴을 집계할 수 없습니다.'");
    expect(source).toContain("nextActionDescription: '상세 결과를 불러오지 못해 추가 권장 조치를 제시할 수 없습니다.'");
    expect(source).toContain("{resultSectionState.isLoaded && insights.patterns.length ? (");
    expect(source).toContain("{resultSectionState.isLoaded && insights.nextActions.length ? (");
  });

  it('groups distributions and issue tags under the required failure pattern section', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('formatPatternValue(pattern.expectedValueType, pattern.expected)');
    expect(source).toContain('formatPatternValue(pattern.actualValueType, pattern.actual)');
    expect(source.indexOf('title="실패 패턴 요약"')).toBeLessThan(source.indexOf('title="다음 조치"'));
    expect(source.indexOf('실제 결정 분포')).toBeGreaterThan(source.indexOf('title="실패 패턴 요약"'));
    expect(source.indexOf('실제 결정 분포')).toBeLessThan(source.indexOf('title="다음 조치"'));
  });
});
