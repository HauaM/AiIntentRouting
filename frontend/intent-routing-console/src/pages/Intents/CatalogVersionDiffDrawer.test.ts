import { describe, expect, it } from 'vitest';
import {
  groupCatalogVersionExampleDiffItems,
  selectCatalogVersionDiffBaseline,
} from './CatalogVersionDiffDrawer';

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

describe('groupCatalogVersionExampleDiffItems', () => {
  it('groups examples by intent before splitting them into positive and negative buckets', () => {
    const groups = groupCatalogVersionExampleDiffItems([
      {
        intent_id: 't1',
        intent_display_name: '테스트 문의',
        route_key: 'test.route',
        example_type: 'positive',
        text_masked: '이 오류 메시지가 뜰 때 조치 방법 알려줘',
      },
      {
        intent_id: 't1',
        intent_display_name: '테스트 문의',
        route_key: 'test.route',
        example_type: 'negative',
        text_masked: '담당자 전화번호를 알려줘',
      },
      {
        intent_id: 't2',
        intent_display_name: '계정 문의',
        route_key: 'account.route',
        example_type: 'positive',
        text_masked: '계정 잠김 해제 방법 알려줘',
      },
    ]);

    expect(groups).toEqual([
      {
        intent_id: 't1',
        intent_display_name: '테스트 문의',
        route_key: 'test.route',
        positive: ['이 오류 메시지가 뜰 때 조치 방법 알려줘'],
        negative: ['담당자 전화번호를 알려줘'],
      },
      {
        intent_id: 't2',
        intent_display_name: '계정 문의',
        route_key: 'account.route',
        positive: ['계정 잠김 해제 방법 알려줘'],
        negative: [],
      },
    ]);
  });
});
