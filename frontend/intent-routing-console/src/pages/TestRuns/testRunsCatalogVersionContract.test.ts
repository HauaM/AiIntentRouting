import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), 'ValidationVersionsPanel.tsx'),
  'utf8',
);

describe('ValidationVersionsPanel catalog version contract', () => {
  it('loads selectable active catalog versions instead of only the latest catalog', () => {
    expect(source).toContain('CATALOG_VERSION_LIMIT = 100');
    expect(source).toContain("status: 'active'");
    expect(source).toContain('setCatalogVersions');
    expect(source).toContain('useState<API.CatalogVersionListItem[]>([])');
    expect(source).not.toContain('listCatalogVersions(serviceId, 1)');
  });

  it('renders active catalog versions through an Ant Design Select with metadata', () => {
    expect(source).toContain('<Select');
    expect(source).toContain('catalogVersions.map');
    expect(source).toContain('optionRender');
    expect(source).toContain('version.display_version');
    expect(source).toContain('version.description');
    expect(source).toContain('version.embedding_count');
    expect(source).toContain('version.model_version');
    expect(source).toContain('version.vector_index_version');
  });

  it('keeps catalog selection wired to the parent test-run form', () => {
    expect(source).toContain('onChange({ policy, catalogVersion: selectedCatalogVersionValue })');
    expect(source).toContain('VersionChip label="Catalog"');
    expect(source).not.toContain('createCatalogVersion');
    expect(source).not.toContain('새 Catalog 버전 만들기');
  });
});
