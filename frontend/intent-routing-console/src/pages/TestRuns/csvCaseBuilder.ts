export type CsvCaseType =
  | 'positive'
  | 'confusing'
  | 'clarify'
  | 'risk'
  | 'off_topic'
  | 'fallback';

export type CsvCaseDraft = {
  case_id: string;
  query: string;
  expected_intent: string;
  case_type: CsvCaseType;
  memo: string;
};

export type CsvParseResult =
  | { ok: true; cases: CsvCaseDraft[] }
  | { ok: false; errors: string[] };

export const CSV_COLUMNS: Array<keyof CsvCaseDraft> = [
  'case_id',
  'query',
  'expected_intent',
  'case_type',
  'memo',
];

export const CSV_CASE_TYPES: CsvCaseType[] = [
  'positive',
  'confusing',
  'clarify',
  'risk',
  'off_topic',
  'fallback',
];

const expectedIntentRequiredTypes = new Set<CsvCaseType>(['positive', 'confusing']);

const escapeCell = (value: string) => {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
};

const parseRows = (csvText: string): string[][] => {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = '';
  let inQuotes = false;

  for (let index = 0; index < csvText.length; index += 1) {
    const character = csvText[index];
    const nextCharacter = csvText[index + 1];

    if (character === '"') {
      if (inQuotes && nextCharacter === '"') {
        cell += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (character === ',' && !inQuotes) {
      row.push(cell);
      cell = '';
      continue;
    }

    if ((character === '\n' || character === '\r') && !inQuotes) {
      if (character === '\r' && nextCharacter === '\n') {
        index += 1;
      }
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
      continue;
    }

    cell += character;
  }

  if (inQuotes) {
    throw new Error('CSV has an unterminated quoted cell');
  }
  row.push(cell);
  if (row.some((value) => value !== '') || rows.length === 0) {
    rows.push(row);
  }
  return rows;
};

export function parseCsvText(csvText: string): CsvParseResult {
  let rows: string[][];
  try {
    rows = parseRows(csvText.trim());
  } catch (error) {
    return { ok: false, errors: [(error as Error).message] };
  }

  const [header, ...bodyRows] = rows;
  const errors: string[] = [];

  if (
    !header ||
    header.length !== CSV_COLUMNS.length ||
    header.some((column, index) => column !== CSV_COLUMNS[index])
  ) {
    return {
      ok: false,
      errors: [`CSV columns must be exactly: ${CSV_COLUMNS.join(', ')}`],
    };
  }

  const cases: CsvCaseDraft[] = [];
  const seenCaseIds = new Set<string>();

  bodyRows.forEach((row, rowIndex) => {
    const rowNumber = rowIndex + 2;
    if (row.length !== CSV_COLUMNS.length) {
      errors.push(`row ${rowNumber}: CSV columns must match header`);
      return;
    }

    const draft = {
      case_id: row[0].trim(),
      query: row[1].trim(),
      expected_intent: row[2].trim(),
      case_type: row[3].trim() as CsvCaseType,
      memo: row[4].trim(),
    };

    if (!draft.case_id) errors.push(`row ${rowNumber}: case_id is required`);
    if (!draft.query) errors.push(`row ${rowNumber}: query is required`);
    if (!draft.memo) errors.push(`row ${rowNumber}: memo is required`);
    if (draft.case_id && seenCaseIds.has(draft.case_id)) {
      errors.push(`row ${rowNumber}: duplicate case_id ${draft.case_id}`);
    }
    seenCaseIds.add(draft.case_id);

    if (!CSV_CASE_TYPES.includes(draft.case_type)) {
      errors.push(`row ${rowNumber}: unknown case_type ${draft.case_type}`);
    } else if (expectedIntentRequiredTypes.has(draft.case_type)) {
      if (!draft.expected_intent) {
        errors.push(`row ${rowNumber}: expected_intent is required`);
      }
    } else if (draft.expected_intent) {
      errors.push(`row ${rowNumber}: expected_intent must be empty`);
    }

    cases.push(draft);
  });

  if (!cases.length) {
    errors.push('CSV must include at least one test case');
  }

  if (errors.length) {
    return { ok: false, errors };
  }
  return { ok: true, cases };
}

export const buildCsvText = (drafts: CsvCaseDraft[]) =>
  [
    CSV_COLUMNS.join(','),
    ...drafts.map((draft) =>
      CSV_COLUMNS.map((column) => escapeCell(String(draft[column] ?? ''))).join(','),
    ),
  ].join('\n');

export function downloadCsvFile(filename: string, drafts: CsvCaseDraft[]) {
  const blob = new Blob([buildCsvText(drafts)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename.trim() || 'test-cases.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}
