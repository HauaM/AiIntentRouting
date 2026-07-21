import { describe, expect, it, vi } from 'vitest';
import { completeApiKeyCreation } from './apiKeyCreateFlow';

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
};

describe('completeApiKeyCreation', () => {
  it('keeps a successful one-time secret when the selected scope changes before response', async () => {
    const createResponse = deferred<{ key_id: string; api_key: string }>();
    const onCreated = vi.fn();
    const reloadCurrentScope = vi.fn();

    const completion = completeApiKeyCreation({
      create: () => createResponse.promise,
      scope: { serviceId: 'svc-a', environment: 'dev' },
      isScopeCurrent: () => false,
      onCreated,
      reloadCurrentScope,
    });

    createResponse.resolve({ key_id: 'key_live_once', api_key: 'irt_once' });
    await completion;

    expect(onCreated).toHaveBeenCalledWith({
      response: { key_id: 'key_live_once', api_key: 'irt_once' },
      scope: { serviceId: 'svc-a', environment: 'dev' },
    });
    expect(reloadCurrentScope).not.toHaveBeenCalled();
  });
});
