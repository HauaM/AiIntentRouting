import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('TestRunDiagnosticsPanel pre-merge contract', () => {
  it('renders a dependency notice instead of fake diagnostics before backend merge', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('FutureFeatureNotice');
    expect(source).toContain('backend diagnostics');
    expect(source).toContain('2026-07-20-test-run-diagnostics-ux.md');
    expect(source).not.toContain('fetchTestRunDiagnostics');
    expect(source).not.toContain('/diagnostics');
  });
});
