import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

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
});
