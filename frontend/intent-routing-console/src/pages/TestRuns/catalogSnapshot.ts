export type CatalogSnapshotIntent = {
  intent_id: string;
  display_name: string;
  description: string;
  route_key: string;
  status: string;
  positive_example_count: number;
  negative_example_count: number;
  example_count: number;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const asText = (value: unknown) => (typeof value === 'string' ? value : '');

export const extractCatalogSnapshotIntents = (
  snapshot: Record<string, unknown> | undefined,
): CatalogSnapshotIntent[] => {
  const rawIntents = snapshot?.intents;
  if (!Array.isArray(rawIntents)) return [];

  return rawIntents
    .filter(isRecord)
    .map((intent) => {
      const examples = Array.isArray(intent.examples) ? intent.examples : [];
      const exampleTypes = examples
        .filter(isRecord)
        .map((example) => asText(example.example_type));

      return {
        intent_id: asText(intent.intent_id),
        display_name: asText(intent.display_name),
        description: asText(intent.description),
        route_key: asText(intent.route_key),
        status: asText(intent.status),
        positive_example_count: exampleTypes.filter((type) => type === 'positive').length,
        negative_example_count: exampleTypes.filter((type) => type === 'negative').length,
        example_count: examples.length,
      };
    })
    .filter((intent) => intent.intent_id || intent.route_key);
};
