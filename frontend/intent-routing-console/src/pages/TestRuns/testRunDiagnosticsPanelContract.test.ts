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

    expect(source).toContain('diagnosticsError ? (');
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
    expect(source).toContain('program_supported_question이 구체 Intent를 과도하게 흡수');
    expect(source).not.toContain('label={`${issue.severity}: ${issue.code}`}');
  });
});
