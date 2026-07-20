import { describe, expect, it } from 'vitest';
import { selectCatalogVersionDiffBaseline } from './CatalogVersionDiffDrawer';

const version = (intent_catalog_version: string, created_at: string) =>
  ({ intent_catalog_version, created_at }) as API.CatalogVersionListItem;

describe('selectCatalogVersionDiffBaseline', () => {
  it('selects the closest earlier version rather than the newest or oldest row', () => {
    const oldest = version('catalog-1', '2026-07-01T09:00:00.000Z');
    const baseline = version('catalog-2', '2026-07-02T09:00:00.000Z');
    const target = version('catalog-3', '2026-07-03T09:00:00.000Z');
    const newest = version('catalog-4', '2026-07-04T09:00:00.000Z');

    expect(selectCatalogVersionDiffBaseline([newest, oldest, target, baseline], target)).toBe(
      baseline,
    );
  });
});
