import {
  buildCsvText,
  downloadCsvFile,
  parseCsvText,
  type CsvCaseDraft,
} from './csvCaseBuilder';

const validCsv = [
  'case_id,query,expected_intent,memo',
  'P001,인터넷뱅킹 오류가 발생해요,program_supported_question,정상 문의',
  'P002,업무 밖 상담으로 보내줘,off_topic_other_subject,업무밖 intent도 정상 intent로 테스트',
].join('\n');

it('parses normal four-column CSV into case drafts', () => {
  expect(parseCsvText(validCsv)).toEqual({
    ok: true,
    cases: [
      {
        case_id: 'P001',
        query: '인터넷뱅킹 오류가 발생해요',
        expected_intent: 'program_supported_question',
        memo: '정상 문의',
      },
      {
        case_id: 'P002',
        query: '업무 밖 상담으로 보내줘',
        expected_intent: 'off_topic_other_subject',
        memo: '업무밖 intent도 정상 intent로 테스트',
      },
    ],
  });
});

it('builds backend-compatible CSV from case drafts', () => {
  const drafts: CsvCaseDraft[] = [
    {
      case_id: 'tc-001',
      query: 'password reset help',
      expected_intent: 'it_password_reset',
      memo: 'happy path',
    },
    {
      case_id: 'tc-002',
      query: 'show me payroll',
      expected_intent: 'off_topic_other_subject',
      memo: 'out of scope',
    },
  ];

  expect(buildCsvText(drafts)).toBe(
    [
      'case_id,query,expected_intent,memo',
      'tc-001,password reset help,it_password_reset,happy path',
      'tc-002,show me payroll,off_topic_other_subject,out of scope',
    ].join('\n'),
  );
});

it('handles quoted CSV cells containing commas, quotes, and newlines', () => {
  const csv = [
    'case_id,query,expected_intent,memo',
    'tc-003,"reset password, please","it_password_reset","contains ""quote"""',
    'tc-004,"line one',
    'line two",it_password_reset,"multi-line query"',
  ].join('\n');

  const result = parseCsvText(csv);

  expect(result.ok).toBe(true);
  if (result.ok) {
    expect(result.cases[0].query).toBe('reset password, please');
    expect(result.cases[0].memo).toBe('contains "quote"');
    expect(result.cases[1].query).toBe('line one\nline two');
  }
});

it('requires expected intent for every normal CSV row', () => {
  expect(
    parseCsvText('case_id,query,expected_intent,memo\nP001,문의,,memo'),
  ).toEqual({
    ok: false,
    errors: ['row 2: expected_intent is required'],
  });
});

it('rejects empty CSV and incorrect headers', () => {
  const emptyResult = parseCsvText('case_id,query,expected_intent,memo');
  const badHeaderResult = parseCsvText('case_id,query\nTC001,hello');

  expect(emptyResult.ok).toBe(false);
  expect(badHeaderResult.ok).toBe(false);
  if (!emptyResult.ok) {
    expect(emptyResult.errors).toContain('CSV must include at least one test case');
  }
  if (!badHeaderResult.ok) {
    expect(badHeaderResult.errors[0]).toContain(
      'CSV columns must be exactly: case_id, query, expected_intent, memo',
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
