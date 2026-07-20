import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'), 'utf8');
const configSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../../../config/config.ts'),
  'utf8',
);
const navigationSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../../components/adminShellNavigation.ts'),
  'utf8',
);

describe('CatalogVersions page contract', () => {
  it('is registered as an operational AdminShell route and menu item', () => {
    expect(configSource).toContain("path: '/catalog-versions'");
    expect(configSource).toContain("component: './CatalogVersions'");
    expect(navigationSource).toContain("name: 'Catalog 버전관리'");
    expect(navigationSource).toContain("path: '/catalog-versions'");
  });

  it('renders a table-first service-scoped catalog version list', () => {
    expect(source).toContain('<AdminShell title="Catalog 버전관리">');
    expect(source).toContain('ProTable<API.CatalogVersionListItem>');
    expect(source).toContain('listCatalogVersions(session.serviceId');
    expect(source).toContain('CATALOG_VERSION_LIST_LIMIT');
    expect(source).toContain("cardProps={{ title: 'Catalog 버전 목록' }}");
    expect(source).not.toContain('hero');
    expect(source).not.toContain('landing');
  });

  it('requires a 10-character description when creating catalog versions', () => {
    expect(source).toContain('Catalog 버전 등록');
    expect(source).toContain('createCatalogVersion(session.serviceId');
    expect(source).toContain('{ min: 10');
    expect(source).toContain('value.trim().length >= 10');
    expect(source).toContain('Input.TextArea');
  });

  it('supports compare, load-to-draft, and guarded deactivation row actions', () => {
    expect(source).toContain('fetchCatalogVersionDiff');
    expect(source).toContain('diffBaseline');
    expect(source).toContain('compare_to: baseline?.intent_catalog_version');
    expect(source).toContain('Drawer');
    expect(source).toContain('loadCatalogVersionToDraft');
    expect(source).toContain('현재 Intent Catalog 초안이 이 버전의 snapshot으로 덮어써질 수 있습니다.');
    expect(source).toContain('deactivateCatalogVersion');
    expect(source).toContain('disabled: row.released || row.release_count > 0');
  });

  it('shows required lifecycle and count columns without prohibited data clients', () => {
    [
      'display_version',
      'description',
      'status',
      'released',
      'release_count',
      'intent_count',
      'example_count',
      'embedding_count',
      'created_at',
    ].forEach((field) => expect(source).toContain(field));
    expect(source).not.toContain('axios');
    expect(source).not.toContain('useQuery');
    expect(source).not.toContain('Authorization: Bearer');
  });
});
