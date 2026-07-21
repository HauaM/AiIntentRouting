import { describe, expect, it } from 'vitest';
import { extractCatalogSnapshotIntents } from './catalogSnapshot';

describe('catalog snapshot helpers', () => {
  it('extracts intent rows from immutable catalog snapshots', () => {
    const rows = extractCatalogSnapshotIntents({
      intents: [
        {
          intent_id: 'owner_contact_lookup',
          display_name: '담당자 정보 찾기',
          description: '담당자 연락처를 찾습니다.',
          route_key: 'owner.contact_lookup.search',
          status: 'active',
          examples: [
            { example_type: 'positive' },
            { example_type: 'negative' },
            { example_type: 'positive' },
          ],
        },
      ],
    });

    expect(rows).toEqual([
      {
        intent_id: 'owner_contact_lookup',
        display_name: '담당자 정보 찾기',
        description: '담당자 연락처를 찾습니다.',
        route_key: 'owner.contact_lookup.search',
        status: 'active',
        positive_example_count: 2,
        negative_example_count: 1,
        example_count: 3,
      },
    ]);
  });

  it('ignores malformed snapshot intent rows without breaking the step', () => {
    const rows = extractCatalogSnapshotIntents({
      intents: [
        null,
        'broken',
        {
          intent_id: 'risk_personal_data_included',
          route_key: 'privacy.personal_data.review',
          examples: 'not-array',
        },
      ],
    });

    expect(rows).toEqual([
      {
        intent_id: 'risk_personal_data_included',
        display_name: '',
        description: '',
        route_key: 'privacy.personal_data.review',
        status: '',
        positive_example_count: 0,
        negative_example_count: 0,
        example_count: 0,
      },
    ]);
  });
});
