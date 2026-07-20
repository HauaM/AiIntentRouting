import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const read = (file: string) =>
  readFileSync(resolve(process.cwd(), `src/pages/TestRuns/${file}`), 'utf8');

it('separates test policy selection from validation versions', () => {
  const page = read('index.tsx');

  expect(page).toContain('<TestPolicyPanel');
  expect(page).toContain('<ValidationVersionsPanel');
  expect(page).not.toContain('ValidationBundlePanel');
});

it('keeps detailed policy values inside the direct-settings modal', () => {
  const panel = read('TestPolicyPanel.tsx');
  const modal = read('CustomTestPolicyModal.tsx');
  const policy = read('testPolicy.ts');

  expect(policy).toContain('엄격 기준');
  expect(policy).toContain('기본 기준');
  expect(policy).toContain('탐색 기준');
  expect(policy).toContain('직접 설정');
  expect(panel).not.toContain('명확화 여유 점수');
  expect(modal).toContain('명확화 여유 점수');
  expect(modal).toContain('현재 선택된 정책을 초기값으로 보여줍니다.');
});

it('requires explicit policy version creation before a test run can use it', () => {
  const panel = read('TestPolicyPanel.tsx');

  expect(panel).toContain('새 정책 버전 만들기');
  expect(panel).toContain('createPolicyVersion(serviceId, toPolicyVersionPayload(draft))');
});
