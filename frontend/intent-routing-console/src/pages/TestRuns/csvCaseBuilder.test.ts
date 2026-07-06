import { buildCsvText, type CsvCaseDraft } from './csvCaseBuilder';

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

it('quotes CSV cells containing commas', () => {
  expect(
    buildCsvText([
      {
        case_id: 'tc-003',
        query: 'reset password, please',
        expected_intent: 'it_password_reset',
        case_type: 'positive',
        memo: 'contains comma',
      },
    ]),
  ).toContain('"reset password, please"');
});
