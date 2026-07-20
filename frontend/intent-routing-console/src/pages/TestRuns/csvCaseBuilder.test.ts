import {
  buildCsvText,
  downloadCsvFile,
  parseCsvText,
  type CsvCaseDraft,
} from './csvCaseBuilder';

const validCsv = [
  'case_id,query,expected_intent,case_type,memo',
  'tc-001,password reset help,it_password_reset,positive,known happy path',
  'tc-002,ambiguous login problem,it_login,confusing,similar intent coverage',
  'tc-003,maybe login maybe password,,clarify,should request clarification',
  'tc-004,show me payroll,,off_topic,out of scope',
  'tc-005,delete all customer data,,risk,blocked safety case',
  'tc-006,unknown request,,fallback,no matching intent',
].join('\n');

it('parses backend-compatible CSV into case drafts', () => {
  const result = parseCsvText(validCsv);

  expect(result.ok).toBe(true);
  if (result.ok) {
    expect(result.cases).toHaveLength(6);
    expect(result.cases[0]).toMatchObject({
      case_id: 'tc-001',
      expected_intent: 'it_password_reset',
      case_type: 'positive',
    });
    expect(result.cases[2]).toMatchObject({
      case_id: 'tc-003',
      expected_intent: '',
      case_type: 'clarify',
    });
  }
});

it('builds backend-compatible CSV from case drafts', () => {
  const drafts: CsvCaseDraft[] = [
    {
      case_id: 'tc-001',
      query: 'password reset help',
      expected_intent: 'it_password_reset',
      case_type: 'positive',
      memo: 'happy path',
    },
    {
      case_id: 'tc-002',
      query: 'show me payroll',
      expected_intent: '',
      case_type: 'off_topic',
      memo: 'out of scope',
    },
  ];

  expect(buildCsvText(drafts)).toBe(
    [
      'case_id,query,expected_intent,case_type,memo',
      'tc-001,password reset help,it_password_reset,positive,happy path',
      'tc-002,show me payroll,,off_topic,out of scope',
    ].join('\n'),
  );
});

it('handles quoted CSV cells containing commas, quotes, and newlines', () => {
  const csv = [
    'case_id,query,expected_intent,case_type,memo',
    'tc-003,"reset password, please","it_password_reset",positive,"contains ""quote"""',
    'tc-004,"line one',
    'line two",,fallback,"multi-line query"',
  ].join('\n');

  const result = parseCsvText(csv);

  expect(result.ok).toBe(true);
  if (result.ok) {
    expect(result.cases[0].query).toBe('reset password, please');
    expect(result.cases[0].memo).toBe('contains "quote"');
    expect(result.cases[1].query).toBe('line one\nline two');
  }
});

it('reports detailed validation errors for invalid CSV', () => {
  const result = parseCsvText(
    [
      'case_id,query,expected_intent,case_type,memo',
      'tc-001,password reset,,positive,missing expected intent',
      'tc-001,another query,,fallback,duplicate id',
      'tc-003,off topic,it_payroll,off_topic,intent must be empty',
      'tc-004,unknown,,unknown,bad type',
    ].join('\n'),
  );

  expect(result.ok).toBe(false);
  if (!result.ok) {
    expect(result.errors).toContain('row 2: expected_intent is required');
    expect(result.errors).toContain('row 3: duplicate case_id tc-001');
    expect(result.errors).toContain('row 4: expected_intent must be empty');
    expect(result.errors).toContain('row 5: unknown case_type unknown');
  }
});

it('rejects empty CSV and incorrect headers', () => {
  const emptyResult = parseCsvText('case_id,query,expected_intent,case_type,memo');
  const badHeaderResult = parseCsvText('case_id,query\nTC001,hello');

  expect(emptyResult.ok).toBe(false);
  expect(badHeaderResult.ok).toBe(false);
  if (!emptyResult.ok) {
    expect(emptyResult.errors).toContain('CSV must include at least one test case');
  }
  if (!badHeaderResult.ok) {
    expect(badHeaderResult.errors[0]).toContain(
      'CSV columns must be exactly: case_id, query, expected_intent, case_type, memo',
    );
  }
});

it('exports CSV through a browser download without backend export contracts', () => {
  const createObjectURL = vi.fn(() => 'blob:test');
  const revokeObjectURL = vi.fn();
  const click = vi.fn();
  const anchor = {
    href: '',
    download: '',
    click,
  } as unknown as HTMLAnchorElement;
  vi.stubGlobal('document', { createElement: vi.fn() });
  const createElement = vi.spyOn(document, 'createElement').mockReturnValue(anchor);
  vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });

  downloadCsvFile('cases.csv', [
    {
      case_id: 'tc-001',
      query: 'password reset help',
      expected_intent: 'it_password_reset',
      case_type: 'positive',
      memo: 'happy path',
    },
  ]);

  expect(createElement).toHaveBeenCalledWith('a');
  expect(anchor.download).toBe('cases.csv');
  expect(createObjectURL).toHaveBeenCalledOnce();
  expect(click).toHaveBeenCalledOnce();
  expect(revokeObjectURL).toHaveBeenCalledWith('blob:test');

  createElement.mockRestore();
  vi.unstubAllGlobals();
});
