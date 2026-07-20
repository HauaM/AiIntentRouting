import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('CatalogVersionStep contract', () => {
  it('auto-loads the latest active catalog version by default', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('listCatalogVersions(serviceId');
    expect(source).toContain("versionMode === 'active' ? 'active' : undefined");
    expect(source).toContain('onChange(nextVersions[0])');
    expect(source).toContain('최신 Catalog 버전');
  });

  it('allows loading older catalog versions without manual ID typing', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('전체 버전 불러오기');
    expect(source).toContain('setVersionMode');
    expect(source).toContain('status: versionMode ===');
    expect(source).toContain('reproducibility_status');
    expect(source).toContain('선택한 Catalog 버전 상태를 확인하세요');
    expect(source).toContain('<Select');
    expect(source).toContain('optionRender');
    expect(source).not.toContain('intent_catalog_version"');
  });

  it('uses the catalog-only step in the Test Runs wizard', () => {
    const page = read('index.tsx');

    expect(page).toContain('<Steps');
    expect(page).toContain('<CatalogVersionStep');
    expect(page).not.toContain('<ValidationVersionsPanel');
  });
});
