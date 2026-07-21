import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('TestRunCatalogStatusPanel contract', () => {
  it('renders catalog and vector metadata in its own panel', () => {
    const source = read('TestRunCatalogStatusPanel.tsx');

    expect(source).toContain('Catalog / Vector 상태');
    expect(source).toContain('준비된 vector index');
    expect(source).toContain('Test Run vector index');
  });

  it('renders catalog lifecycle and reproducibility as semantic status tags', () => {
    const source = read('TestRunCatalogStatusPanel.tsx');

    expect(source).toContain("import { StatusTag } from '@/components/StatusTag';");
    expect(source).toContain('catalogStatusTone(catalog.status)');
    expect(source).toContain('catalogStatusLabel(catalog.status)');
    expect(source).toContain('reproducibilityTone(catalog.reproducibility_status)');
    expect(source).toContain('reproducibilityLabel(catalog.reproducibility_status)');
  });
});
