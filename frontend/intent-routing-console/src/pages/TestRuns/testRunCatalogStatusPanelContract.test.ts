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

  it('receives shared diagnostic loading and error state before rendering an empty catalog claim', () => {
    const source = read('TestRunCatalogStatusPanel.tsx');

    expect(source).toContain('diagnosticsLoading?: boolean;');
    expect(source).toContain('diagnosticsError?: string | null;');
    expect(source).toContain('description="Catalog 상태를 불러오는 중입니다."');
    expect(source).toContain('message="Catalog 상태를 불러오지 못했습니다."');
    expect(source.indexOf('diagnosticsLoading')).toBeLessThan(source.indexOf('조회된 Catalog 상태가 없습니다.'));
    expect(source.indexOf('diagnosticsError')).toBeLessThan(source.indexOf('조회된 Catalog 상태가 없습니다.'));
  });
});
