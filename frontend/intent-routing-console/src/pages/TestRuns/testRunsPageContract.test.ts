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

it('separates new test execution and previous result loading with tabs in step one', () => {
  const page = read('index.tsx');

  expect(page).toContain("const [testRunMode, setTestRunMode] = useState<'new' | 'history'>('new');");
  expect(page).toContain('const testRunModeTabs = [');
  expect(page).toContain("key: 'new'");
  expect(page).toContain("label: '새 테스트 실행'");
  expect(page).toContain("key: 'history'");
  expect(page).toContain("label: '기존 결과 불러오기'");
  expect(page).toContain('<Tabs');
  expect(page).toContain('items={testRunModeTabs}');
  expect(page).toContain('<TestRunHistorySelect');
  expect(page).toContain('key={session.serviceId}');
  expect(page).toContain('onSelect={handleHistoryRunSelect}');
  expect(page).not.toContain('className="test-run-step-grid"');
  expect(page.indexOf('<TestRunHistorySelect')).toBeGreaterThan(
    page.indexOf('currentStep === 0'),
  );
  expect(page).not.toContain('<Form form={lookupForm}');
  expect(page).not.toContain('test_run_id를 입력하세요');
  expect(page).not.toContain('placeholder="tr_..."');
  expect(page).not.toContain('<Card');
});

it('keeps previous result selection on step one until the operator confirms result review', () => {
  const page = read('index.tsx');

  expect(page).toContain('const [selectedHistoryRun, setSelectedHistoryRun] = useState<API.TestRunListItem>();');
  expect(page).toContain('const handleHistoryRunSelect = (testRun: API.TestRunListItem) => {');
  expect(page).toContain('setSelectedHistoryRun(testRun);');
  expect(page).toContain('const handleHistoryResultOpen = async () => {');
  expect(page).toContain('if (!selectedHistoryRun) return;');
  expect(page).toContain('selectedHistoryRun.test_run_id');
  expect(page).toContain('결과 확인 → Step 3');
  expect(page).not.toContain('onSelect={handleHistorySelect}');
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
  expect(page).toContain('resultLabel[normalizedResult] ?? row.result');
  expect(page).toContain("message.success('테스트 실행 결과를 불러왔습니다.')");
  expect(page).toContain('<TestRunHistorySelect');
  expect(page).toContain('기존 테스트 실행 결과');
  expect(page).not.toContain('<Typography.Text code>test_run_id</Typography.Text>로 이전 실행 결과를 조회할 수 있습니다.');
  expect(page).not.toContain('Test Run 결과를 불러왔습니다.');
});

it('normalizes uppercase backend result values before rendering semantic StatusTag labels', () => {
  const page = read('index.tsx');

  expect(page).toContain('const normalizedResult = row.result.toLowerCase();');
  expect(page).toContain('status={normalizedResult}');
  expect(page).toContain('resultLabel[normalizedResult] ?? row.result');
});

it('localizes test run summary state and gate labels', () => {
  const page = read('index.tsx');

  expect(page).toContain("'Release 생성 전에 차단 사유를 해결해야 합니다.'");
  expect(page).toContain('label="검증 게이트"');
  expect(page).not.toContain('blocked 사유');
  expect(page).not.toContain('label="Gate"');
});

it('handles create and history request failures with clear messages', () => {
  const page = read('index.tsx');

  expect((page.match(/catch/g) ?? []).length).toBeGreaterThanOrEqual(2);
  expect(page).toContain("message.error('테스트 실행 생성에 실패했습니다.')");
  expect(page).toContain("message.error('테스트 실행은 생성되었지만 결과를 불러오지 못했습니다.')");
  expect(page).toContain("message.error('테스트 실행 결과를 불러오지 못했습니다.')");
});

it('keeps a successfully created run summary visible when its results request fails', () => {
  const page = read('index.tsx');

  expect(page).toContain(
    'setSummary(created);\n      setCurrentStep(2);\n      const nextResults = await fetchTestRunResults',
  );
});

it('clears prior run data and only allows the latest run request to update the results step', () => {
  const page = read('index.tsx');

  expect(page).toContain('const runRequestGenerationRef = useRef(0);');
  expect(page).toContain('const beginRunRequest = () => {');
  expect(page).toContain('setSummary(undefined);');
  expect(page).toContain('setResults([]);');
  expect(page).toContain('runRequestGenerationRef.current === requestGeneration');
  expect(page).toContain('const requestGeneration = beginRunRequest();');
  expect(page).toContain('if (!isCurrentRunRequest(requestGeneration, serviceId)) return false;');
  expect(page).toContain('if (!isCurrentRunRequest(requestGeneration, serviceId)) return;');
});

it('resets loading when a service change invalidates a pending run request', () => {
  const page = read('index.tsx');

  expect(page).toContain(
    'runRequestGenerationRef.current += 1;\n    setLoading(false);\n    setSummary(undefined);',
  );
});

it('wires diagnostics to the selected test run in the results step', () => {
  const page = read('index.tsx');

  expect(page).toContain('<TestRunDiagnosticsPanel');
  expect(page).toContain('testRunId={summary?.test_run_id}');
  expect(page).toContain('diagnostics={diagnostics}');
  expect(page).toContain('diagnosticsLoading={diagnosticsLoading}');
  expect(page).toContain('diagnosticsError={diagnosticsError}');
  expect(page).toContain('results={results}');
});

it('loads and resets diagnostics in page state for the selected test run', () => {
  const page = read('index.tsx');

  expect(page).toContain('fetchTestRunDiagnostics');
  expect(page).toContain('const [diagnostics, setDiagnostics] = useState<API.TestRunDiagnostics | null>(null);');
  expect(page).toContain('const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);');
  expect(page).toContain('const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);');
  expect(page).toContain("setDiagnosticsError('진단 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');");
});

it('renders catalog and vector status after the detailed results table', () => {
  const source = read('index.tsx');

  const diagnosticsIndex = source.indexOf('<TestRunDiagnosticsPanel');
  const tableIndex = source.indexOf('<ProTable<API.TestRunResult>');
  const catalogStatusIndex = source.indexOf('<TestRunCatalogStatusPanel');

  expect(diagnosticsIndex).toBeGreaterThan(-1);
  expect(tableIndex).toBeGreaterThan(diagnosticsIndex);
  expect(catalogStatusIndex).toBeGreaterThan(tableIndex);
});
