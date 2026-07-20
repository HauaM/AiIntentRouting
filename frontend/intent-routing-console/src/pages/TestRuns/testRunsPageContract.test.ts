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
