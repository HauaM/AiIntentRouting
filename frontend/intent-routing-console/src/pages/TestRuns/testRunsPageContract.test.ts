import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const read = (file: string) =>
  readFileSync(resolve(process.cwd(), `src/pages/TestRuns/${file}`), 'utf8');

it('renders Test Runs as a three-step wizard in the required order', () => {
  const page = read('index.tsx');

  expect(page).toContain('<Steps');
  expect(page).toContain('ds-page-card steps-form-page-card');
  expect(page).toContain("title: 'Intent Catalog 선택'");
  expect(page).toContain("title: '테스트 설정'");
  expect(page).toContain("title: '테스트 결과 확인'");
  expect(page.indexOf("title: 'Intent Catalog 선택'")).toBeLessThan(
    page.indexOf("title: '테스트 설정'"),
  );
  expect(page.indexOf("title: '테스트 설정'")).toBeLessThan(
    page.indexOf("title: '테스트 결과 확인'"),
  );
  expect(page).not.toContain('type="inner"');
});

it('keeps result lookup inside the single wizard panel without nested Cards', () => {
  const page = read('index.tsx');

  expect(page).toContain('<Form form={lookupForm}');
  expect(page.indexOf('<Form form={lookupForm}')).toBeGreaterThan(
    page.indexOf('ds-page-card steps-form-page-card'),
  );
  expect(page).not.toContain('<Card');
});

it('keeps test policy selection in step two and detailed values in the modal', () => {
  const page = read('index.tsx');
  const panel = read('TestPolicyPanel.tsx');
  const modal = read('CustomTestPolicyModal.tsx');

  expect(page).toContain('<TestPolicyPanel');
  expect(page).toContain('<CsvCasesGrid');
  expect(panel).not.toContain('명확화 여유 점수');
  expect(modal).toContain('명확화 여유 점수');
});

it('creates test runs from applied CSV grid data instead of a main textarea', () => {
  const page = read('index.tsx');

  expect(page).toContain('buildCsvText(csvCases)');
  expect(page).toContain('setCsvCases');
  expect(page).toContain('<CsvImportModal');
  expect(page).not.toContain('Input.TextArea rows={8}');
  expect(page).not.toContain('name="csv_text"');
});

it('keeps CSV import, export, and create wired to the same applied cases state', () => {
  const page = read('index.tsx');

  expect(page).toContain('onSave={(nextCases, nextCsvText)');
  expect(page).toContain('setCsvCases(nextCases)');
  expect(page).toContain('setCsvText(nextCsvText)');
  expect(page).toContain('setCsvImportOpen(false)');
  expect(page).toContain('downloadCsvFile(');
  expect(page).toContain('csvCases,');
});

it('localizes result and lookup labels while preserving technical identifiers', () => {
  const page = read('index.tsx');

  expect(page).toContain("title: '케이스'");
  expect(page).toContain("title: '마스킹된 질의'");
  expect(page).toContain("title: '기대 결과'");
  expect(page).toContain("title: '실제 결과'");
  expect(page).toContain("pass: { text: '통과' }");
  expect(page).toContain("fail: { text: '실패' }");
  expect(page).toContain("review: { text: '검토' }");
  expect(page).toContain('{resultLabel[row.result] ?? row.result}');
  expect(page).toContain("message.success('테스트 실행 결과를 불러왔습니다.')");
  expect(page).toContain('<Typography.Text code>test_run_id</Typography.Text>');
  expect(page).toContain('기존 테스트 실행 결과 조회');
  expect(page).not.toContain('Test Run 결과를 불러왔습니다.');
});

it('localizes test run summary state and gate labels', () => {
  const page = read('index.tsx');

  expect(page).toContain("'Release 생성 전에 차단 사유를 해결해야 합니다.'");
  expect(page).toContain('label="검증 게이트"');
  expect(page).not.toContain('blocked 사유');
  expect(page).not.toContain('label="Gate"');
});

it('handles create and lookup request failures with clear messages', () => {
  const page = read('index.tsx');

  expect((page.match(/catch/g) ?? []).length).toBeGreaterThanOrEqual(2);
  expect(page).toContain("message.error('테스트 실행 생성에 실패했습니다.')");
  expect(page).toContain("message.error('테스트 실행은 생성되었지만 결과를 불러오지 못했습니다.')");
  expect(page).toContain("message.error('테스트 실행 결과를 불러오지 못했습니다.')");
});

it('shows the pre-merge diagnostics dependency shell without backend wiring', () => {
  const page = read('index.tsx');

  expect(page).toContain('<TestRunDiagnosticsPanel');
  expect(page).not.toContain('fetchTestRunDiagnostics');
  expect(page).not.toContain('/diagnostics');
});
