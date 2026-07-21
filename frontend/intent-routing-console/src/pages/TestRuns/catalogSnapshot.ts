export type CatalogSnapshotIntent = {
  intent_id: string;
  display_name: string;
  description: string;
  route_key: string;
  status: string;
  positive_example_count: number;
  negative_example_count: number;
  example_count: number;
  positive_examples: CatalogSnapshotExample[];
  negative_examples: CatalogSnapshotExample[];
};

export type CatalogSnapshotExample = {
  example_id: string;
  example_type: 'positive' | 'negative';
  text_masked: string;
  source: string;
  approved: boolean;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const asText = (value: unknown) => (typeof value === 'string' ? value : '');
const asBoolean = (value: unknown) => (typeof value === 'boolean' ? value : false);

const toSnapshotExample = (example: Record<string, unknown>): CatalogSnapshotExample | null => {
  const exampleType = asText(example.example_type);
  if (exampleType !== 'positive' && exampleType !== 'negative') return null;

  return {
    example_id: asText(example.example_id),
    example_type: exampleType,
    text_masked: asText(example.text_masked),
    source: asText(example.source),
    approved: asBoolean(example.approved),
  };
};

export const extractCatalogSnapshotIntents = (
  snapshot: Record<string, unknown> | undefined,
): CatalogSnapshotIntent[] => {
  const rawIntents = snapshot?.intents;
  if (!Array.isArray(rawIntents)) return [];

  return rawIntents
    .filter(isRecord)
    .map((intent) => {
      const examples = Array.isArray(intent.examples)
        ? intent.examples
            .filter(isRecord)
            .map(toSnapshotExample)
            .filter((example): example is CatalogSnapshotExample => Boolean(example))
        : [];
      const positiveExamples = examples.filter((example) => example.example_type === 'positive');
      const negativeExamples = examples.filter((example) => example.example_type === 'negative');

      return {
        intent_id: asText(intent.intent_id),
        display_name: asText(intent.display_name),
        description: asText(intent.description),
        route_key: asText(intent.route_key),
        status: asText(intent.status),
        positive_example_count: positiveExamples.length,
        negative_example_count: negativeExamples.length,
        example_count: examples.length,
        positive_examples: positiveExamples,
        negative_examples: negativeExamples,
      };
    })
    .filter((intent) => intent.intent_id || intent.route_key);
};
