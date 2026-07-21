import { describe, expect, it } from 'vitest';
import {
  canApplyCatalogVersionDiffResult,
  nextCatalogVersionDiffRequestId,
} from './catalogVersionDiffRequest';

describe('catalog version diff request guard', () => {
  it('rejects out-of-order compare responses and service-scope changes', () => {
    const firstRequest = {
      requestId: nextCatalogVersionDiffRequestId(0),
      serviceId: 'svc-a',
    };
    const secondRequest = {
      requestId: nextCatalogVersionDiffRequestId(firstRequest.requestId),
      serviceId: 'svc-a',
    };

    expect(canApplyCatalogVersionDiffResult(firstRequest, secondRequest)).toBe(false);
    expect(canApplyCatalogVersionDiffResult(secondRequest, secondRequest)).toBe(true);
    expect(
      canApplyCatalogVersionDiffResult(secondRequest, {
        ...secondRequest,
        serviceId: 'svc-b',
      }),
    ).toBe(false);
  });
});
