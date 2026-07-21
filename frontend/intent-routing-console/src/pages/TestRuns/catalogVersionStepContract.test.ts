import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('CatalogVersionStep contract', () => {
  it('lets the catalog selection and explanation summary use the full wizard width', () => {
    const globalLess = read('../../global.less');
    const selectRule = globalLess.match(/\.test-run-step-select\s*\{[^}]*\}/)?.[0] ?? '';
    const summaryRule = globalLess.match(/\.test-run-step-summary\s*\{[^}]*\}/)?.[0] ?? '';

    expect(selectRule).toContain('width: 100%');
    expect(selectRule).not.toContain('max-width: 552px');
    expect(summaryRule).not.toContain('max-width: 552px');
  });

  it('loads catalog versions into a single labeled combo and selects the latest active version', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('listCatalogVersions(serviceId');
    expect(source).toContain('fetchCatalogVersion(serviceId');
    expect(source).toContain('CATALOG_VERSION_LIMIT');
    expect(source).toContain("status: 'active'");
    expect(source).toContain('const defaultVersion = nextVersions[0];');
    expect(source).toContain('onChangeRef.current(defaultVersion);');
    expect(source).toContain('htmlFor="test-run-catalog-version-select"');
    expect(source).toContain('id="test-run-catalog-version-select"');
    expect(source).toContain('Catalog 버전');
    expect(source).toContain('<Select');
    expect(source).toContain('optionFilterProp="searchLabel"');
    expect(source).toContain('label: catalogVersionOptionLabel(version)');
    expect(source).toContain('searchLabel: catalogVersionSearchLabel(version)');
    expect(source).toContain('className="test-run-step-field-help"');
    expect(source).toContain('선택한 Catalog 버전은 테스트 결과와 Release 후보에서 그대로 참조됩니다.');
    const catalogSelectIdIndex = source.indexOf('id="test-run-catalog-version-select"');
    const helperClassIndex = source.indexOf('className="test-run-step-field-help"');
    const helperCopyIndex = source.indexOf(
      '선택한 Catalog 버전은 테스트 결과와 Release 후보에서 그대로 참조됩니다.',
    );
    expect(helperClassIndex).toBeGreaterThan(catalogSelectIdIndex);
    expect(helperCopyIndex).toBeGreaterThan(helperClassIndex);
  });

  it('removes the separate latest and load-all buttons from step one', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).not.toContain('handleLoadLatest');
    expect(source).not.toContain('setVersionMode');
    expect(source).not.toContain('versionMode');
    expect(source).not.toContain('최신 Catalog 버전');
    expect(source).not.toContain('전체 버전 불러오기');
  });

  it('keeps old catalog selection available through option metadata and warning state', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain("status: 'active'");
    expect(source).toContain('reproducibility_status');
    expect(source).toContain('선택한 Catalog 버전 상태를 확인하세요');
    expect(source).toContain('optionRender');
    expect(source).toContain('display_version');
    expect(source).toContain('embedding_count');
    expect(source).not.toContain('intent_catalog_version"');
  });

  it('renders the selected catalog ID once, shortened to 8 visible characters with copy retained', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain("label: 'Catalog'");
    expect(source).toContain('<VersionChip');
    expect(source).toContain('value={selectedVersion.intent_catalog_version}');
    expect(source).toContain('maxDisplayLength={8}');
    expect(source).not.toContain('label="Catalog"');
  });

  it('shows the selected catalog version immutable intent snapshot as a searchable grid', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('extractCatalogSnapshotIntents');
    expect(source).toContain('setSnapshotIntents');
    expect(source).toContain('선택한 Catalog의 Intent 목록');
    expect(source).toContain('test-run-catalog-intent-toolbar');
    expect(source).toContain('placeholder="Intent 검색"');
    expect(source).toContain('placeholder="전체 상태"');
    expect(source).toContain('<Table<CatalogSnapshotIntent>');
    expect(source).toContain("title: 'Intent'");
    expect(source).toContain("title: 'Route key'");
    expect(source).toContain("title: 'Example'");
    expect(source).toContain("title: 'Status'");
    expect(source).toContain('filteredSnapshotIntents.length');
  });

  it('opens an example popup from positive and negative counts in the intent grid', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('exampleModal');
    expect(source).toContain('openExampleModal');
    expect(source).toContain("type: 'positive'");
    expect(source).toContain("openExampleModal(row, 'negative')");
    expect(source).toContain('positive_examples');
    expect(source).toContain('negative_examples');
    expect(source).toContain('<Button');
    expect(source).toContain('<Modal');
    expect(source).toContain("title: 'Example'");
    expect(source).toContain('test-run-example-modal-table');
  });

  it('uses the catalog-only step in the Test Runs wizard', () => {
    const page = read('index.tsx');

    expect(page).toContain('<Steps');
    expect(page).toContain('<CatalogVersionStep');
    expect(page).toContain('items={testRunModeTabs}');
    expect(page).toContain('key={session.serviceId}');
    expect(page).not.toContain('<ValidationVersionsPanel');
  });
});
