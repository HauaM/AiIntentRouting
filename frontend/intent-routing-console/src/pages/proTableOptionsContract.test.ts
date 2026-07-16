import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const pagesDir = dirname(fileURLToPath(import.meta.url));
const readPage = (file: string) => readFileSync(join(pagesDir, file), 'utf8');

describe('workflow page ProTable options contract', () => {
  const pageFiles = ['TestRuns/index.tsx', 'ApiKeys/index.tsx', 'Releases/index.tsx'];

  it('disables ProTable built-in option icons on workflow pages', () => {
    for (const file of pageFiles) {
      const text = readPage(file);

      expect(text).not.toContain('options={{ density: true');
      expect(text).toContain('options={false}');
    }
  });

  it('keeps existing workflow guards and confirmations', () => {
    const apiKeys = readPage('ApiKeys/index.tsx');
    const releases = readPage('Releases/index.tsx');

    expect(apiKeys).toContain('canManageRuntimeSetup');
    expect(apiKeys).toContain('ConfirmActionButton');
    expect(apiKeys).toContain('handleRevokeById');
    expect(releases).toContain('canManageReleases');
    expect(releases).toContain('ConfirmActionButton');
    expect(releases).toContain('handleActivate');
    expect(releases).toContain('handleRollback');
  });
});
