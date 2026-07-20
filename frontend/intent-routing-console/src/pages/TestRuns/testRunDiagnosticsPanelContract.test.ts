import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

const readApiTypes = () => readFileSync(resolve(process.cwd(), 'src/types/api.d.ts'), 'utf8');

describe('TestRunDiagnosticsPanel contract after backend merge', () => {
  it('loads backend diagnostics for the selected test run', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('fetchTestRunDiagnostics');
    expect(source).toContain('primary_issue');
    expect(source).toContain('catalog_version');
    expect(source).toContain('result_counts');
    expect(source).not.toContain('FutureFeatureNotice');
  });

  it('maps stable issue codes to Korean UI copy in the frontend', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('catalog_version_not_active');
    expect(source).toContain('catalog_version_not_reproducible');
    expect(source).toContain('fallback_failures_dominant');
    expect(source).toContain('intent_mismatch_exists');
  });

  it('clears stale diagnostics and presents Korean failure state when loading fails', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('const [error, setError] = useState<string>();');
    expect(source).toContain(
      'let alive = true;\n    setDiagnostics(undefined);\n    setError(undefined);\n    setLoading(true);',
    );
    expect(source).toContain('.catch(() => {');
    expect(source).toContain(
      "setError('진단 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');",
    );
    expect(source).toContain('error ? (');
    expect(source).toContain('진단 결과를 불러오지 못했습니다.');
  });

  it('localizes diagnostics labels and types the complete catalog response', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');
    const apiTypes = readApiTypes();

    expect(source).toContain('label="Catalog 버전"');
    expect(source).toContain('label="상태"');
    expect(source).toContain('label="재현성"');
    expect(source).toContain('label="결과 집계"');
    expect(source).toContain('label="실제 결정 집계"');
    expect(source).toContain("?? '없음'");
    expect(source).toContain('백엔드 진단에서 주요 이슈를 찾지 못했습니다.');
    expect(source).not.toContain('Backend diagnostics did not identify');
    expect(apiTypes).toContain('test_run_vector_index_ready: boolean | null;');
    expect(apiTypes).toContain('test_run_vector_index_status: string | null;');
  });
});
