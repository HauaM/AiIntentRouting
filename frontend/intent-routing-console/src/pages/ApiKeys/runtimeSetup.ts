const TRUSTED_ADMIN_HEADERS = new Set([
  'x-admin-token',
  'x-actor-id',
  'x-actor-roles',
  'x-service-scope',
]);

export type RuntimeSetupHeaderRow = {
  name: string;
  value: string;
};

export const runtimeSetupHeaderRows = (
  guidance?: API.RuntimeSetupGuidance,
): RuntimeSetupHeaderRow[] => {
  if (!guidance) return [];
  return Object.entries(guidance.headers_template)
    .filter(([name]) => !TRUSTED_ADMIN_HEADERS.has(name.toLowerCase()))
    .map(([name, value]) => ({ name, value }));
};

export const runtimeSetupBodyTemplateText = (
  guidance?: API.RuntimeSetupGuidance,
) => {
  if (!guidance) return '';
  return JSON.stringify(guidance.body_template, null, 2);
};

export const runtimeSetupSelectedKeyLabel = (
  guidance?: API.RuntimeSetupGuidance,
) => {
  return (
    guidance?.selected_key?.key_id ?? guidance?.headers_template['X-Key-Id'] ?? ''
  );
};

export const runtimeSetupContainsRawSecret = (
  guidance: API.RuntimeSetupGuidance,
  rawSecret: string,
) => {
  const secret = rawSecret.trim();
  return Boolean(secret && JSON.stringify(guidance).includes(secret));
};
