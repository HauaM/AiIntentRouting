import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('TestRunHistorySelect contract', () => {
  it('loads previous test runs from the service-scoped API into a labeled Select', () => {
    const source = read('TestRunHistorySelect.tsx');

    expect(source).toContain('listTestRuns(serviceId');
    expect(source).toContain('TEST_RUN_HISTORY_LIMIT');
    expect(source).toContain('htmlFor="test-run-history-select"');
    expect(source).toContain('id="test-run-history-select"');
    expect(source).toContain('기존 테스트 실행 결과');
    expect(source).toContain('<Select');
    expect(source).toContain('showSearch');
    expect(source).not.toContain('allowClear');
    expect(source).toContain('optionFilterProp="searchLabel"');
    expect(source).toContain('label: testRunOptionLabel(run)');
    expect(source).toContain('searchLabel: testRunSearchLabel(run)');
    expect(source).toContain('setRuns([]);');
    expect(source).toContain('setLoadError');
    expect(source).toContain('optionRender');
  });

  it('shows decision fields in each history option without a manual test_run_id input', () => {
    const source = read('TestRunHistorySelect.tsx');

    expect(source).toContain('source_filename');
    expect(source).toContain('gate_passed');
    expect(source).toContain('pass_rate');
    expect(source).toContain('risk_pass_rate');
    expect(source).toContain('policy_version');
    expect(source).toContain('intent_catalog_version');
    expect(source).toContain('created_at');
    expect(source).toContain('test_run_id');
    expect(source).not.toContain('<Input');
    expect(source).not.toContain('test_run_id를 입력하세요');
  });

  it('selects a prior run through the component callback', () => {
    const source = read('TestRunHistorySelect.tsx');

    expect(source).toContain('onSelect: (testRunId: string) => void;');
    expect(source).toContain('onSelect(nextTestRunId);');
    expect(source).toContain('이전 실행을 선택하면 테스트 결과 확인 단계로 이동합니다.');
  });
});
