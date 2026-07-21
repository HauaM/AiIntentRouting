export type ApiKeyCreateScope = {
  serviceId: string;
  environment: 'dev' | 'qa' | 'prod';
};

export type CreatedApiKey<T> = {
  response: T;
  scope: ApiKeyCreateScope;
};

export async function completeApiKeyCreation<T>({
  create,
  scope,
  isScopeCurrent,
  onCreated,
  reloadCurrentScope,
}: {
  create: () => Promise<T>;
  scope: ApiKeyCreateScope;
  isScopeCurrent: () => boolean;
  onCreated: (created: CreatedApiKey<T>) => void;
  reloadCurrentScope: (response: T) => Promise<void>;
}): Promise<void> {
  const response = await create();
  onCreated({ response, scope });
  if (isScopeCurrent()) {
    await reloadCurrentScope(response);
  }
}
