import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('CatalogVersionStep contract', () => {
  it('loads catalog versions into a single labeled combo and selects the latest active version', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('listCatalogVersions(serviceId');
    expect(source).toContain('CATALOG_VERSION_LIMIT');
    expect(source).toContain('const defaultVersion = nextVersions.find');
    expect(source).toContain("version.status === 'active'");
    expect(source).toContain('onChangeRef.current(defaultVersion);');
    expect(source).toContain('htmlFor="test-run-catalog-version-select"');
    expect(source).toContain('id="test-run-catalog-version-select"');
    expect(source).toContain('Catalog 버전');
    expect(source).toContain('<Select');
    expect(
      source.includes('test-run-step-field-help') ||
        source.includes('선택한 Catalog 버전은 테스트 결과와 Release 후보에서 그대로 참조됩니다.'),
    ).toBeTruthy();
  });

  it('removes the separate latest and load-all buttons from step one', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).not.toContain('<Button');
    expect(source).not.toContain('handleLoadLatest');
    expect(source).not.toContain('setVersionMode');
    expect(source).not.toContain('versionMode');
    expect(source).not.toContain('최신 Catalog 버전');
    expect(source).not.toContain('전체 버전 불러오기');
  });

  it('keeps old catalog selection available through option metadata and warning state', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('status: undefined');
    expect(source).toContain('reproducibility_status');
    expect(source).toContain('선택한 Catalog 버전 상태를 확인하세요');
    expect(source).toContain('optionRender');
    expect(source).toContain('display_version');
    expect(source).toContain('embedding_count');
    expect(source).not.toContain('intent_catalog_version"');
  });

  it('uses the catalog-only step in the Test Runs wizard', () => {
    const page = read('index.tsx');

    expect(page).toContain('<Steps');
    expect(page).toContain('<CatalogVersionStep');
    expect(page).toContain('key={session.serviceId}');
    expect(page).not.toContain('<ValidationVersionsPanel');
  });
});
