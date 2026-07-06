export type CsvCaseDraft = {
  case_id: string;
  query: string;
  expected_intent: string;
  case_type: 'positive' | 'confusing' | 'clarify' | 'risk' | 'off_topic' | 'fallback';
  memo: string;
};

const columns: Array<keyof CsvCaseDraft> = [
  'case_id',
  'query',
  'expected_intent',
  'case_type',
  'memo',
];

const escapeCell = (value: string) => {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
};

export const buildCsvText = (drafts: CsvCaseDraft[]) =>
  [
    columns.join(','),
    ...drafts.map((draft) =>
      columns.map((column) => escapeCell(String(draft[column] ?? ''))).join(','),
    ),
  ].join('\n');
