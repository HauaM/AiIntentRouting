# Test Runs Wizard Stepper UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Admin Console Test Runs page into a clear three-step wizard: Intent Catalog selection, test configuration with policy and CSV grid import/export, and result review.

**Architecture:** Keep this plan frontend-first and compatible with the current Admin API. The backend diagnostics plan in `docs/superpowers/plans/2026-07-20-test-run-diagnostics-ux.md` is intentionally developed in another session/branch and later merged into `main`; this UI plan must not implement that backend work or fake its API. The results step renders existing summary/results now, then wires deterministic diagnostics only after the backend diagnostics branch has merged.

**Tech Stack:** React 18, TypeScript, Umi 4 `request`, Ant Design 5, ProComponents, Vitest, existing FastAPI Admin API contracts.

## Global Constraints

- Continue from `main`; create an implementation branch from current `main` when execution starts. Do not execute this wizard plan from `codex/test-run-diagnostics` or any branch that already contains unmerged diagnostics backend commits.
- Treat `docs/superpowers/plans/2026-07-20-test-run-diagnostics-ux.md` as an external dependency developed in another session/branch and merged to `main` later.
- Verify diagnostics backend availability against `main`, not only against the current working tree. A local feature branch containing diagnostics is not enough to unlock Task 6.
- Do not implement `src/intent_routing/diagnostics/*`, repository diagnostic stats, or `GET /admin/v1/services/{service_id}/test-runs/{test_run_id}/diagnostics` in this UI plan.
- Do not render fake diagnostic issue codes, fake evidence, fake result export, fake pagination, fake live polling, React Query, axios, browser actor headers, or bearer tokens.
- Keep normal browser Admin API calls on Umi `request` and the server-issued `irt_admin_session` cookie.
- Use Ant Design `Steps` for the wizard, Ant Design `Modal` for CSV import, and table/grid presentation for applied CSV cases.
- UI/UX skill alignment:
  - Prefer the project `AdminShell`/Service scope shell already used by the page; do not introduce a second navigation/header structure.
  - Prefer ProComponents `StepsForm` for pure multi-step forms. This plan may keep manual Ant Design `Steps` only because step 3 is a result-review surface, not a form submission step; if implementation can model this cleanly with `StepsForm`, use `StepsForm`.
  - Do not nest Ant Design `Card` components. Use one page-level white panel such as `className="ds-page-card steps-form-page-card"` or an equivalent existing project container, and render summary/diagnostics/results as un-nested sections inside it.
  - Operation modals must use a fixed header/body/footer structure, `centered`, local modal tokens, and zero default Modal content padding through the installed Ant Design semantic slot (`styles.content` in Ant Design 5.29.3). If the installed version exposes a different slot, verify the type and use a scoped class fallback.
  - Keep grid/table cells one-line by default with `ellipsis` and `Tooltip`; do not use row background colors for business meaning.
  - Use Korean user-facing labels for commands and states on this Korean Admin workflow, while keeping technical identifiers such as `csv_text`, `test_run_id`, and `intent_catalog_version` monospace/code where displayed.
- CSV import/export covers the current input dataset only. It does not require Phase 2 backend export contracts because it exports the user's currently applied CSV cases from browser state.
- CSV header must remain exactly `case_id,query,expected_intent,case_type,memo`.
- CSV `case_type` values must match the backend parser: `positive`, `confusing`, `clarify`, `risk`, `off_topic`, `fallback`.
- `positive` and `confusing` rows require `expected_intent`; `clarify`, `risk`, `off_topic`, and `fallback` rows must leave `expected_intent` empty.
- Keep policy details inside `CustomTestPolicyModal`; the wizard settings step may show policy preset buttons and the selected `policy_version`, not a full threshold score summary.
- Gate Test Run creation on selected Catalog version, selected/created policy version, and at least one valid CSV row.
- Preserve masked-query behavior in results; never show raw test query text beyond existing `query_masked`.
- Before completion, run targeted Vitest tests, TypeScript, and prohibited-pattern search over changed frontend files.

## Execution Branch Preflight

Run this before Task 1 implementation begins:

```bash
git branch --show-current
git log --oneline main..HEAD --max-count=20
git grep -n "get_test_run_diagnostics\|diagnose_test_run\|CatalogVersionDiagnosticStats" HEAD -- src tests || true
git grep -n "get_test_run_diagnostics\|diagnose_test_run\|CatalogVersionDiagnosticStats" main -- src tests || true
```

Expected before Tasks 1-5:

- The implementation branch is `main` or a UI branch created from current `main`.
- If `HEAD` contains diagnostics symbols but `main` does not, stop and restart this wizard work from `main`; otherwise Task 6 can be accidentally coupled to the diagnostics branch.
- If `main` already contains diagnostics symbols, that means the backend diagnostics work has been merged and Task 6 may be considered after Tasks 1-5.

---

## File Structure

- Create `frontend/intent-routing-console/src/pages/TestRuns/CatalogVersionStep.tsx`
  - Catalog-only wizard step extracted from the catalog-selection portion of `ValidationVersionsPanel.tsx`. Loads latest active Catalog version by default and allows switching to other active/all historical versions.
- Create `frontend/intent-routing-console/src/pages/TestRuns/catalogVersionStepContract.test.ts`
  - Contract checks for auto latest load, non-manual version selection, and all-version lookup support.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/ValidationVersionsPanel.tsx`
  - Use as the source for the catalog-selection refactor; remove from `index.tsx` and delete only after confirming no imports remain.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunsCatalogVersionContract.test.ts`
  - Replace with the new catalog step contract or delete if superseded by `catalogVersionStepContract.test.ts`.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.ts`
  - Owns CSV column constants, case type constants, parser/validator, CSV building, and browser download helper.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.test.ts`
  - Adds parser/validation coverage for valid CSV, invalid headers, duplicated case IDs, expected-intent rules, quoted cells, empty CSV, and download filename shape.
- Create `frontend/intent-routing-console/src/pages/TestRuns/CsvImportModal.tsx`
  - Operation modal with textarea, detailed validation errors, and save-to-grid behavior.
- Create `frontend/intent-routing-console/src/pages/TestRuns/CsvCasesGrid.tsx`
  - Read-only grid for the currently applied CSV cases, with compact columns and status tags.
- Create `frontend/intent-routing-console/src/pages/TestRuns/csvImportModalContract.test.ts`
  - Source-level contract test for modal textarea containment and detailed validation copy.
- Create `frontend/intent-routing-console/src/pages/TestRuns/csvCasesGridContract.test.ts`
  - Source-level contract test for grid columns, import/export buttons, and no main-page CSV textarea.
- Create `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
  - Pre-merge shell that renders `FutureFeatureNotice` until backend diagnostics is merged, then becomes the diagnostics issue panel in Task 6.
- Create `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
  - Contract test that pre-merge implementation does not call or mention a live diagnostics endpoint.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
  - Replaces mixed cards with the three-step wizard, wires catalog/policy/CSV state, creates Test Runs from grid data, and shows summary/results in step 3.
- Modify `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`
  - Updates contracts from separated panels to wizard step order, CSV grid requirement, and diagnostics dependency notice.
- After diagnostics backend merges: modify `frontend/intent-routing-console/src/services/adminServices.ts`, `frontend/intent-routing-console/src/services/adminServices.test.ts`, `frontend/intent-routing-console/src/types/api.d.ts`, and `TestRunDiagnosticsPanel.tsx`
  - Adds diagnostics API types/service and replaces the dependency notice with real issue/evidence rendering.

---

### Task 1: Catalog Selection Wizard Step

**Files:**
- Create: `frontend/intent-routing-console/src/pages/TestRuns/CatalogVersionStep.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/catalogVersionStepContract.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- Modify or delete after replacement: `frontend/intent-routing-console/src/pages/TestRuns/testRunsCatalogVersionContract.test.ts`

**Interfaces:**
- Consumes: `listCatalogVersions(serviceId, { limit, status })` from `frontend/intent-routing-console/src/services/adminServices.ts`.
- Produces: `CatalogVersionStep` component with props:

```ts
type CatalogVersionStepProps = {
  serviceId: string;
  value?: API.CatalogVersionListItem;
  onChange: (value?: API.CatalogVersionListItem) => void;
};
```

- Later tasks consume the selected Catalog via `selectedCatalogVersion?.intent_catalog_version`.

- [ ] **Step 1: Write the failing catalog step contract**

Create `frontend/intent-routing-console/src/pages/TestRuns/catalogVersionStepContract.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('CatalogVersionStep contract', () => {
  it('auto-loads the latest active catalog version by default', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('listCatalogVersions(serviceId');
    expect(source).toContain("versionMode === 'active' ? 'active' : undefined");
    expect(source).toContain('onChange(nextVersions[0])');
    expect(source).toContain('최신 Catalog 버전');
  });

  it('allows loading older catalog versions without manual ID typing', () => {
    const source = read('CatalogVersionStep.tsx');

    expect(source).toContain('전체 버전 불러오기');
    expect(source).toContain('setVersionMode');
    expect(source).toContain('status: versionMode ===');
    expect(source).toContain('reproducibility_status');
    expect(source).toContain('선택한 Catalog 버전 상태를 확인하세요');
    expect(source).toContain('<Select');
    expect(source).toContain('optionRender');
    expect(source).not.toContain('intent_catalog_version"');
  });

  it('uses the catalog-only step in the Test Runs wizard', () => {
    const page = read('index.tsx');

    expect(page).toContain('<Steps');
    expect(page).toContain('<CatalogVersionStep');
    expect(page).not.toContain('<ValidationVersionsPanel');
  });
});
```

- [ ] **Step 2: Run the contract test to verify failure**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/catalogVersionStepContract.test.ts
```

Expected: FAIL because `CatalogVersionStep.tsx` does not exist and `index.tsx` still imports `ValidationVersionsPanel`.

- [ ] **Step 3: Extract catalog selection into `CatalogVersionStep.tsx`**

Create `frontend/intent-routing-console/src/pages/TestRuns/CatalogVersionStep.tsx` by moving the catalog-only logic from `ValidationVersionsPanel.tsx`. Preserve the proven `Select`/`optionRender`/`VersionChip` pattern, search-label construction, and status tag behavior unless a change is explicitly called out below. The old joint latest button loaded policy and catalog together; this wizard intentionally separates those concerns, so policy creation remains in Step 2 through `TestPolicyPanel`.

```tsx
import { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Select, Space, Tag, Typography } from 'antd';
import { VersionChip } from '@/components/VersionChip';
import { listCatalogVersions } from '@/services/adminServices';

type CatalogVersionStepProps = {
  serviceId: string;
  value?: API.CatalogVersionListItem;
  onChange: (value?: API.CatalogVersionListItem) => void;
};

const CATALOG_VERSION_LIMIT = 100;

const catalogVersionStatusColor: Record<API.CatalogVersionStatus, string> = {
  active: 'green',
  inactive: 'default',
};

const catalogVersionSearchLabel = (version: API.CatalogVersionListItem) =>
  [
    version.display_version,
    version.description,
    version.intent_catalog_version,
    version.status,
    version.model_version,
    version.vector_index_version,
  ]
    .filter(Boolean)
    .join(' ');

export function CatalogVersionStep({
  serviceId,
  value,
  onChange,
}: CatalogVersionStepProps) {
  const [loading, setLoading] = useState(false);
  const [versionMode, setVersionMode] = useState<'active' | 'all'>('active');
  const [versions, setVersions] = useState<API.CatalogVersionListItem[]>([]);

  const selectedValue = value?.intent_catalog_version;
  const selectedVersion = useMemo(
    () =>
      versions.find(
        (version) => version.intent_catalog_version === selectedValue,
      ) ?? value,
    [selectedValue, value, versions],
  );
  const selectedCatalogVersionWarning = selectedVersion
    ? selectedVersion.status !== 'active' ||
      selectedVersion.reproducibility_status !== 'complete'
    : false;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    listCatalogVersions(serviceId, {
      limit: CATALOG_VERSION_LIMIT,
      status: versionMode === 'active' ? 'active' : undefined,
    })
      .then((nextVersions) => {
        if (!alive) return;
        setVersions(nextVersions);
        if (!value && versionMode === 'active') {
          onChange(nextVersions[0]);
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [onChange, serviceId, value, versionMode]);

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space direction="vertical" size={4}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          Intent Catalog 선택
        </Typography.Title>
        <Typography.Text type="secondary">
          기본값은 최신 Catalog 버전입니다. 과거 검증이 필요하면 전체 버전을 불러와 선택하세요.
        </Typography.Text>
      </Space>
      <Alert
        type="info"
        showIcon
        message="테스트는 선택한 Catalog 버전 스냅샷 기준으로 실행됩니다."
        description="테스트 결과와 Release 후보는 이 단계에서 선택한 intent_catalog_version을 계속 참조합니다."
      />
      {selectedCatalogVersionWarning && selectedVersion ? (
        <Alert
          type="warning"
          showIcon
          message="선택한 Catalog 버전 상태를 확인하세요"
          description={`status=${selectedVersion.status}, reproducibility=${selectedVersion.reproducibility_status}`}
        />
      ) : null}
      <Space wrap>
        <Button
          loading={loading && versionMode === 'active'}
          onClick={() => setVersionMode('active')}
        >
          최신 Catalog 버전
        </Button>
        <Button
          loading={loading && versionMode === 'all'}
          onClick={() => setVersionMode('all')}
        >
          전체 버전 불러오기
        </Button>
      </Space>
      <Select
        showSearch
        allowClear
        value={selectedValue}
        loading={loading}
        placeholder="Catalog 버전을 선택하세요"
        optionFilterProp="label"
        style={{ width: '100%', maxWidth: 560 }}
        options={versions.map((version) => ({
          value: version.intent_catalog_version,
          label: catalogVersionSearchLabel(version),
          catalogVersion: version,
        }))}
        onChange={(nextVersionId) => {
          onChange(
            versions.find(
              (version) => version.intent_catalog_version === nextVersionId,
            ),
          );
        }}
        optionRender={({ data }) => {
          const version = data.catalogVersion as API.CatalogVersionListItem;
          return (
            <Space direction="vertical" size={2}>
              <Space wrap size={6}>
                <Typography.Text strong>{version.display_version}</Typography.Text>
                <Tag color={catalogVersionStatusColor[version.status]}>
                  {version.status}
                </Tag>
                <Tag>{version.released ? `released ${version.release_count}` : 'unreleased'}</Tag>
                <Tag>{version.embedding_count} embeddings</Tag>
              </Space>
              <Typography.Text type="secondary" ellipsis>
                {version.description || version.intent_catalog_version}
              </Typography.Text>
              <Typography.Text type="secondary">
                model {version.model_version || 'none'} / vector {version.vector_index_version || 'none'}
              </Typography.Text>
            </Space>
          );
        }}
      />
      <Space wrap>
        <VersionChip label="Catalog" value={selectedVersion?.intent_catalog_version} />
        {selectedVersion ? (
          <>
            <Tag color={catalogVersionStatusColor[selectedVersion.status]}>
              {selectedVersion.status}
            </Tag>
            <Tag>{selectedVersion.display_version}</Tag>
          </>
        ) : null}
      </Space>
    </Space>
  );
}
```

- [ ] **Step 4: Wire the component into the page shell minimally**

In `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`, replace the `ValidationVersionsPanel` import with:

```ts
import { CatalogVersionStep } from './CatalogVersionStep';
```

Add this state near existing `catalogVersion` state:

```ts
const [selectedCatalogVersion, setSelectedCatalogVersion] =
  useState<API.CatalogVersionListItem>();
```

Update `handleVersionsChange` callers in later tasks; for this task only, add a temporary render below hidden form fields so the contract can find the component:

```tsx
<CatalogVersionStep
  serviceId={session.serviceId}
  value={selectedCatalogVersion}
  onChange={(nextCatalogVersion) => {
    setSelectedCatalogVersion(nextCatalogVersion);
    setCatalogVersion(nextCatalogVersion?.intent_catalog_version);
    createForm.setFieldsValue({
      intent_catalog_version: nextCatalogVersion?.intent_catalog_version,
    });
  }}
/>
```

This temporary render will be moved into the wizard in Task 4.

- [ ] **Step 5: Run the catalog step contract**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/catalogVersionStepContract.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/CatalogVersionStep.tsx frontend/intent-routing-console/src/pages/TestRuns/catalogVersionStepContract.test.ts frontend/intent-routing-console/src/pages/TestRuns/index.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunsCatalogVersionContract.test.ts
git commit -m "feat: add catalog selection step"
```

---

### Task 2: CSV Parser, Validation, Builder, And Download Helpers

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.test.ts`

**Interfaces:**
- Consumes: Backend CSV contract from `src/intent_routing/testing/csv_runner.py`.
- Produces:

```ts
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

export const CSV_COLUMNS: Array<keyof CsvCaseDraft>;
export const CSV_CASE_TYPES: CsvCaseType[];
export function parseCsvText(csvText: string): CsvParseResult;
export function buildCsvText(drafts: CsvCaseDraft[]): string;
export function downloadCsvFile(filename: string, drafts: CsvCaseDraft[]): void;
```

- [ ] **Step 1: Write failing parser and validation tests**

Replace `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.test.ts` with:

```ts
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
```

- [ ] **Step 2: Run tests to verify failure**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/csvCaseBuilder.test.ts
```

Expected: FAIL because `parseCsvText`, `CSV_CASE_TYPES`, and `downloadCsvFile` do not exist.

- [ ] **Step 3: Implement CSV parsing and validation**

Replace `frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.ts` with:

```ts
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
```

- [ ] **Step 4: Run CSV utility tests**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/csvCaseBuilder.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.ts frontend/intent-routing-console/src/pages/TestRuns/csvCaseBuilder.test.ts
git commit -m "feat: validate test run csv cases"
```

---

### Task 3: CSV Import Modal And Applied Cases Grid

**Files:**
- Create: `frontend/intent-routing-console/src/pages/TestRuns/CsvImportModal.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/CsvCasesGrid.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/csvImportModalContract.test.ts`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/csvCasesGridContract.test.ts`

**Interfaces:**
- Consumes: `CsvCaseDraft`, `CSV_CASE_TYPES`, `parseCsvText`, `downloadCsvFile`.
- Produces:

```ts
type CsvImportModalProps = {
  open: boolean;
  initialCsvText: string;
  onCancel: () => void;
  onSave: (cases: CsvCaseDraft[], csvText: string) => void;
};

type CsvCasesGridProps = {
  cases: CsvCaseDraft[];
  sourceFilename: string;
  onImport: () => void;
  onExport: () => void;
};
```

- Later tasks use `CsvCasesGrid` in wizard step 2 and `CsvImportModal` as the only textarea surface for CSV.

- [ ] **Step 1: Write source contract tests**

Create `frontend/intent-routing-console/src/pages/TestRuns/csvImportModalContract.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('CsvImportModal contract', () => {
  it('keeps CSV textarea inside the import modal only', () => {
    const modal = read('CsvImportModal.tsx');

    expect(modal).toContain('<Modal');
    expect(modal).toContain('centered');
    expect(modal).toContain('content:');
    expect(modal).toContain('Input.TextArea');
    expect(modal).toContain('parseCsvText');
    expect(modal).toContain('onSave(result.cases');
  });

  it('renders detailed validation errors before saving', () => {
    const modal = read('CsvImportModal.tsx');

    expect(modal).toContain('validationErrors');
    expect(modal).toContain('CSV 검증 오류');
    expect(modal).toContain('validationErrors.map');
    expect(modal).toContain('저장');
  });
});
```

Create `frontend/intent-routing-console/src/pages/TestRuns/csvCasesGridContract.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('CsvCasesGrid contract', () => {
  it('shows applied CSV cases as a grid with import and export actions', () => {
    const grid = read('CsvCasesGrid.tsx');

    expect(grid).toContain('<Table');
    expect(grid).toContain('case_id');
    expect(grid).toContain('query');
    expect(grid).toContain('expected_intent');
    expect(grid).toContain('case_type');
    expect(grid).toContain('memo');
    expect(grid).toContain('CSV 가져오기');
    expect(grid).toContain('CSV 내보내기');
    expect(grid).toContain('ellipsis');
    expect(grid).toContain('<Tooltip');
  });
});
```

- [ ] **Step 2: Run contract tests to verify failure**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/csvImportModalContract.test.ts src/pages/TestRuns/csvCasesGridContract.test.ts
```

Expected: FAIL because the new components do not exist.

- [ ] **Step 3: Create `CsvImportModal.tsx`**

Create `frontend/intent-routing-console/src/pages/TestRuns/CsvImportModal.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { Alert, Input, Modal, Space, Typography } from 'antd';
import { parseCsvText, type CsvCaseDraft } from './csvCaseBuilder';

type CsvImportModalProps = {
  open: boolean;
  initialCsvText: string;
  onCancel: () => void;
  onSave: (cases: CsvCaseDraft[], csvText: string) => void;
};

const MODAL_TOKENS = {
  contentPadding: 24,
  headerHeight: 56,
  footerHeight: 56,
  viewportGap: 48,
  bodyReservedHeight: 180,
  separator: '1px solid var(--ant-color-border-secondary)',
} as const;

export function CsvImportModal({
  open,
  initialCsvText,
  onCancel,
  onSave,
}: CsvImportModalProps) {
  const [csvText, setCsvText] = useState(initialCsvText);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  useEffect(() => {
    if (open) {
      setCsvText(initialCsvText);
      setValidationErrors([]);
    }
  }, [initialCsvText, open]);

  const save = () => {
    const result = parseCsvText(csvText);
    if (!result.ok) {
      setValidationErrors(result.errors);
      return;
    }
    onSave(result.cases, csvText);
  };

  return (
    <Modal
      title="CSV 가져오기"
      open={open}
      centered
      width={800}
      okText="저장"
      cancelText="취소"
      onCancel={onCancel}
      onOk={save}
      style={{ maxWidth: `calc(100vw - ${MODAL_TOKENS.viewportGap}px)` }}
      styles={{
        header: {
          height: MODAL_TOKENS.headerHeight,
          padding: `0 ${MODAL_TOKENS.contentPadding}px`,
          display: 'flex',
          alignItems: 'center',
          borderBottom: MODAL_TOKENS.separator,
          marginBottom: 0,
        },
        body: {
          padding: MODAL_TOKENS.contentPadding,
          maxHeight: `calc(100dvh - ${MODAL_TOKENS.bodyReservedHeight}px)`,
          overflow: 'auto',
        },
        footer: {
          height: MODAL_TOKENS.footerHeight,
          padding: `12px ${MODAL_TOKENS.contentPadding}px`,
          borderTop: MODAL_TOKENS.separator,
          marginTop: 0,
        },
        content: {
          padding: 0,
          overflow: 'hidden',
        },
      }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Typography.Text type="secondary">
          헤더는 반드시 case_id, query, expected_intent, case_type, memo 순서여야 합니다.
        </Typography.Text>
        {validationErrors.length ? (
          <Alert
            type="error"
            showIcon
            message="CSV 검증 오류"
            description={
              <Space direction="vertical" size={2}>
                {validationErrors.map((error) => (
                  <Typography.Text key={error} type="danger">
                    {error}
                  </Typography.Text>
                ))}
              </Space>
            }
          />
        ) : null}
        <Input.TextArea
          rows={12}
          value={csvText}
          onChange={(event) => setCsvText(event.target.value)}
          placeholder={[
            'case_id,query,expected_intent,case_type,memo',
            'tc-001,password reset help,it_password_reset,positive,known happy path',
          ].join('\n')}
        />
      </Space>
    </Modal>
  );
}
```

- [ ] **Step 4: Create `CsvCasesGrid.tsx`**

Create `frontend/intent-routing-console/src/pages/TestRuns/CsvCasesGrid.tsx`:

```tsx
import { Button, Empty, Space, Table, Tag, Tooltip, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { CsvCaseDraft } from './csvCaseBuilder';

type CsvCasesGridProps = {
  cases: CsvCaseDraft[];
  sourceFilename: string;
  onImport: () => void;
  onExport: () => void;
};

const expectedIntentRequired = new Set(['positive', 'confusing']);

const columns: ColumnsType<CsvCaseDraft> = [
  {
    title: 'Case',
    dataIndex: 'case_id',
    width: 140,
    ellipsis: true,
    render: (value: string) => <Typography.Text code>{value}</Typography.Text>,
  },
  {
    title: 'Query',
    dataIndex: 'query',
    ellipsis: true,
    render: (value: string) => (
      <Tooltip title={value}>
        <Typography.Text ellipsis>{value}</Typography.Text>
      </Tooltip>
    ),
  },
  {
    title: 'Expected intent',
    dataIndex: 'expected_intent',
    width: 180,
    ellipsis: true,
    render: (value: string, row) =>
      expectedIntentRequired.has(row.case_type) ? (
        <Typography.Text>{value}</Typography.Text>
      ) : (
        <Typography.Text type="secondary">없음</Typography.Text>
      ),
  },
  {
    title: 'Case type',
    dataIndex: 'case_type',
    width: 132,
    render: (value: string) => <Tag>{value}</Tag>,
  },
  {
    title: 'Memo',
    dataIndex: 'memo',
    width: 220,
    ellipsis: true,
  },
];

export function CsvCasesGrid({
  cases,
  sourceFilename,
  onImport,
  onExport,
}: CsvCasesGridProps) {
  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap style={{ justifyContent: 'space-between', width: '100%' }}>
        <Space direction="vertical" size={2}>
          <Typography.Title level={5} style={{ margin: 0 }}>
            테스트 CSV 데이터
          </Typography.Title>
          <Typography.Text type="secondary">
            {cases.length ? `${sourceFilename} · ${cases.length}건` : '적용된 CSV 데이터가 없습니다.'}
          </Typography.Text>
        </Space>
        <Space wrap>
          <Button onClick={onImport}>CSV 가져오기</Button>
          <Button onClick={onExport} disabled={!cases.length}>
            CSV 내보내기
          </Button>
        </Space>
      </Space>
      <Table<CsvCaseDraft>
        rowKey="case_id"
        size="small"
        columns={columns}
        dataSource={cases}
        pagination={false}
        scroll={{ x: 920 }}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="CSV 가져오기로 테스트 데이터를 등록하세요."
            />
          ),
        }}
      />
    </Space>
  );
}
```

- [ ] **Step 5: Run modal/grid contract tests**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/csvImportModalContract.test.ts src/pages/TestRuns/csvCasesGridContract.test.ts
```

Expected: PASS. The main-page textarea removal is verified by Task 4 page contracts.

- [ ] **Step 6: Commit the standalone components**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/CsvImportModal.tsx frontend/intent-routing-console/src/pages/TestRuns/CsvCasesGrid.tsx frontend/intent-routing-console/src/pages/TestRuns/csvImportModalContract.test.ts frontend/intent-routing-console/src/pages/TestRuns/csvCasesGridContract.test.ts
git commit -m "feat: add csv import grid components"
```

---

### Task 4: Refactor Test Runs Into A Three-Step Wizard

**Files:**
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/csvCasesGridContract.test.ts`
- Delete: `frontend/intent-routing-console/src/pages/TestRuns/ValidationVersionsPanel.tsx`
- Delete or replace: `frontend/intent-routing-console/src/pages/TestRuns/testRunsCatalogVersionContract.test.ts`

**Interfaces:**
- Consumes: `CatalogVersionStep`, `TestPolicyPanel`, `CsvCasesGrid`, `CsvImportModal`, `buildCsvText`, `downloadCsvFile`, existing `createTestRun`, `fetchTestRun`, `fetchTestRunResults`.
- Produces: Test Runs page wizard with step labels:
  - `Intent Catalog 선택`
  - `테스트 설정`
  - `테스트 결과 확인`

- [ ] **Step 1: Update the Test Runs page contract**

Replace `frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts` with:

```ts
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

it('does not wire backend diagnostics before the diagnostics plan is merged', () => {
  const page = read('index.tsx');

  expect(page).toContain('<TestRunDiagnosticsPanel');
  expect(page).not.toContain('fetchTestRunDiagnostics');
  expect(page).not.toContain('/diagnostics');
});
```

- [ ] **Step 2: Run page contracts to verify failure**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/testRunsPageContract.test.ts src/pages/TestRuns/csvCasesGridContract.test.ts
```

Expected: FAIL because the page still has mixed cards and a main-page textarea.

- [ ] **Step 3: Refactor page state and imports**

In `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`, update imports:

```ts
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ProTable, type ProColumns } from '@ant-design/pro-components';
import { history, useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  Space,
  Steps,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { WorkflowNextActionBar } from '@/components/WorkflowNextActionBar';
import { canEditCatalog, isAdminSessionReady } from '@/models/adminSession';
import {
  createTestRun,
  fetchTestRun,
  fetchTestRunResults,
} from '@/services/adminServices';
import { CatalogVersionStep } from './CatalogVersionStep';
import { CsvCasesGrid } from './CsvCasesGrid';
import { CsvImportModal } from './CsvImportModal';
import { TestRunDiagnosticsPanel } from './TestRunDiagnosticsPanel';
import { TestPolicyPanel } from './TestPolicyPanel';
import {
  buildCsvText,
  downloadCsvFile,
  type CsvCaseDraft,
} from './csvCaseBuilder';
```

Remove these imports from `index.tsx`:

```ts
import { FieldHelpLabel } from '@/components/FieldHelpLabel';
import { FutureFeatureNotice } from '@/components/FutureFeatureNotice';
import { ValidationVersionsPanel } from './ValidationVersionsPanel';
```

Remove `csvTemplate`, `testRunHelp`, and `helpLabel` constants from `index.tsx`. Add this template:

```ts
const csvTemplate = [
  'case_id,query,expected_intent,case_type,memo',
  'tc-001,password reset help,it_password_reset,positive,known happy path',
  'tc-002,maybe login maybe password,,clarify,should request clarification',
].join('\n');
```

Add wizard state inside `TestRunsPage`:

```ts
const [currentStep, setCurrentStep] = useState(0);
const [csvCases, setCsvCases] = useState<CsvCaseDraft[]>([]);
const [csvText, setCsvText] = useState(csvTemplate);
const [csvImportOpen, setCsvImportOpen] = useState(false);
const [selectedCatalogVersion, setSelectedCatalogVersion] =
  useState<API.CatalogVersionListItem>();
```

Update the service-change effect to reset wizard state:

```ts
useEffect(() => {
  serviceIdRef.current = session.serviceId;
  setSummary(undefined);
  setResults([]);
  setPolicy(undefined);
  setCatalogVersion(undefined);
  setSelectedCatalogVersion(undefined);
  setCsvCases([]);
  setCsvText(csvTemplate);
  setCsvImportOpen(false);
  setCurrentStep(0);
  lookupForm.resetFields();
  createForm.resetFields();
}, [createForm, lookupForm, session.serviceId]);
```

- [ ] **Step 4: Replace create payload with grid-derived CSV**

Update `handleCreate`:

```ts
const handleCreate = async () => {
  const serviceId = session.serviceId;
  if (!policy?.policy_version || !catalogVersion) {
    message.error('테스트 정책과 Catalog 버전을 먼저 준비하세요.');
    return;
  }
  if (!csvCases.length) {
    message.error('테스트 CSV 데이터를 먼저 등록하세요.');
    return;
  }
  const sourceFilename =
    createForm.getFieldValue('source_filename')?.trim() || 'test-cases.csv';
  setLoading(true);
  try {
    const created = await createTestRun(serviceId, {
      policy_version: policy.policy_version,
      intent_catalog_version: catalogVersion,
      source_filename: sourceFilename,
      csv_text: buildCsvText(csvCases),
    });
    if (serviceIdRef.current !== serviceId) return;
    setSummary(created);
    lookupForm.setFieldsValue({ test_run_id: created.test_run_id });
    const nextResults = await fetchTestRunResults(serviceId, created.test_run_id);
    if (serviceIdRef.current !== serviceId) return;
    setResults(nextResults);
    setCurrentStep(2);
    message.success('Test Run을 생성했습니다.');
  } finally {
    setLoading(false);
  }
};
```

Update `loadRun` to send users to the result step:

```ts
const loadRun = async (testRunId: string, serviceId = session.serviceId) => {
  const nextSummary = await fetchTestRun(serviceId, testRunId);
  const nextResults = await fetchTestRunResults(serviceId, testRunId);
  if (serviceIdRef.current !== serviceId) return false;
  setSummary(nextSummary);
  setResults(nextResults);
  setCurrentStep(2);
  lookupForm.setFieldsValue({ test_run_id: testRunId });
  return true;
};
```

- [ ] **Step 5: Replace mixed card layout with wizard sections**

Inside `return`, replace the current `Space` body under `<AdminShell title="Test Runs">` with:

```tsx
<Space direction="vertical" size={16} style={{ width: '100%' }}>
  {ready ? (
    <>
      {canRun ? (
        <div className="ds-page-card steps-form-page-card">
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Steps
              current={currentStep}
              items={[
                { title: 'Intent Catalog 선택' },
                { title: '테스트 설정' },
                { title: '테스트 결과 확인' },
              ]}
            />
            {currentStep === 0 ? (
              <CatalogVersionStep
                serviceId={session.serviceId}
                value={selectedCatalogVersion}
                onChange={(nextCatalogVersion) => {
                  setSelectedCatalogVersion(nextCatalogVersion);
                  setCatalogVersion(nextCatalogVersion?.intent_catalog_version);
                  createForm.setFieldsValue({
                    intent_catalog_version: nextCatalogVersion?.intent_catalog_version,
                  });
                }}
              />
            ) : null}
            {currentStep === 1 ? (
              <Form
                form={createForm}
                layout="vertical"
                initialValues={{ source_filename: 'test-cases.csv' }}
              >
                <Form.Item name="policy_version" hidden>
                  <Input />
                </Form.Item>
                <Form.Item name="intent_catalog_version" hidden>
                  <Input />
                </Form.Item>
                <Form.Item
                  name="source_filename"
                  label="CSV 파일명"
                  rules={[{ required: true, whitespace: true, message: 'CSV 파일명을 입력하세요.' }]}
                >
                  <Input placeholder="test-cases.csv" style={{ width: 220 }} />
                </Form.Item>
                <TestPolicyPanel
                  serviceId={session.serviceId}
                  policy={policy}
                  onPolicyCreated={(nextPolicy) => {
                    setPolicy(nextPolicy);
                    createForm.setFieldsValue({
                      policy_version: nextPolicy.policy_version,
                    });
                  }}
                />
                <div style={{ marginTop: 16 }}>
                  <CsvCasesGrid
                    cases={csvCases}
                    sourceFilename={
                      createForm.getFieldValue('source_filename') || 'test-cases.csv'
                    }
                    onImport={() => setCsvImportOpen(true)}
                    onExport={() =>
                      downloadCsvFile(
                        createForm.getFieldValue('source_filename') || 'test-cases.csv',
                        csvCases,
                      )
                    }
                  />
                </div>
              </Form>
            ) : null}
            {currentStep === 2 ? (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                {summary ? (
                  <section>
                    <Typography.Title level={5} style={{ marginTop: 0 }}>
                      테스트 요약
                    </Typography.Title>
                    <Alert
                      type={summary.gate_passed ? 'success' : 'warning'}
                      showIcon
                      style={{ marginBottom: 12 }}
                      message={
                        summary.gate_passed
                          ? 'Release 생성에 사용할 test_run_id가 준비되었습니다.'
                          : 'Release 생성 전에 blocked 사유를 해결해야 합니다.'
                      }
                      description="Release에는 이 test_run_id와 테스트에 사용한 version 값을 그대로 입력합니다."
                    />
                    <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
                      <Descriptions.Item label="Test Run">
                        <Typography.Text code>{summary.test_run_id}</Typography.Text>
                      </Descriptions.Item>
                      <Descriptions.Item label="Dataset">
                        {summary.test_dataset_version}
                      </Descriptions.Item>
                      <Descriptions.Item label="정책 기준">
                        {summary.threshold_preset} / {summary.threshold_value}
                      </Descriptions.Item>
                      <Descriptions.Item label="Pass rate">
                        {formatRate(summary.pass_rate)}
                      </Descriptions.Item>
                      <Descriptions.Item label="Review rate">
                        {formatRate(summary.review_rate)}
                      </Descriptions.Item>
                      <Descriptions.Item label="Risk pass">
                        {formatRate(summary.risk_pass_rate)}
                      </Descriptions.Item>
                      <Descriptions.Item label="Gate">
                        <Tag color={summary.gate_passed ? 'success' : 'error'}>
                          {summary.gate_passed ? '통과' : '차단'}
                        </Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="차단 사유">
                        {summary.block_reasons.length ? summary.block_reasons.join(', ') : '없음'}
                      </Descriptions.Item>
                      <Descriptions.Item label="권장 조치">
                        {summary.recommendations.length ? summary.recommendations.join(', ') : '없음'}
                      </Descriptions.Item>
                    </Descriptions>
                    {summary.gate_passed && summary.risk_pass_rate === 1 ? (
                      <WorkflowNextActionBar
                        title="Release 후보 준비 완료"
                        description="이 test run으로 Release 화면에서 후보를 선택할 수 있습니다."
                        primaryLabel="Release 화면으로 이동"
                        onPrimary={() => history.push('/releases')}
                      />
                    ) : null}
                  </section>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 Test Run이 없습니다." />
                )}
                <TestRunDiagnosticsPanel />
                <ProTable<API.TestRunResult>
                  rowKey="case_id"
                  columns={columns}
                  dataSource={results}
                  search={false}
                  pagination={false}
                  options={{ density: true, fullScreen: false, reload: false, setting: true }}
                  locale={{
                    emptyText: (
                      <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 Test Run 결과가 없습니다." />
                    ),
                  }}
                />
              </Space>
            ) : null}
            <Space wrap>
              <Button
                disabled={currentStep === 0}
                onClick={() => setCurrentStep((step) => Math.max(step - 1, 0))}
              >
                이전
              </Button>
              {currentStep < 1 ? (
                <Button
                  type="primary"
                  disabled={!catalogVersion}
                  onClick={() => setCurrentStep(1)}
                >
                  다음
                </Button>
              ) : null}
              {currentStep === 1 ? (
                <Button
                  type="primary"
                  loading={loading}
                  disabled={!policy?.policy_version || !catalogVersion || !csvCases.length}
                  onClick={handleCreate}
                >
                  Test Run 생성
                </Button>
              ) : null}
            </Space>
          </Space>
        </div>
      ) : (
        <Alert
          type="info"
          showIcon
          message="Test Run 작업 권한이 필요합니다."
          description="선택한 서비스의 system_admin, service_owner, service_developer 역할만 Test Run 생성과 조회를 사용할 수 있습니다."
        />
      )}
      <Card title="Test Run 결과 조회">
        <Form form={lookupForm} layout="inline" onFinish={handleLookup}>
          <Form.Item
            name="test_run_id"
            rules={[{ required: true, whitespace: true, message: 'test_run_id를 입력하세요.' }]}
          >
            <Input placeholder="tr_..." style={{ width: 260 }} disabled={!canRun} />
          </Form.Item>
          <Button htmlType="submit" loading={loading} disabled={!canRun}>
            결과 조회
          </Button>
        </Form>
      </Card>
      <CsvImportModal
        open={csvImportOpen}
        initialCsvText={csvText}
        onCancel={() => setCsvImportOpen(false)}
        onSave={(nextCases, nextCsvText) => {
          setCsvCases(nextCases);
          setCsvText(nextCsvText);
          setCsvImportOpen(false);
          message.success('CSV 데이터를 적용했습니다.');
        }}
      />
    </>
  ) : (
    <AdminSessionRequired />
  )}
</Space>
```

- [ ] **Step 6: Delete superseded catalog bundle files**

If `ValidationVersionsPanel.tsx` has no remaining import:

```bash
git grep -n "ValidationVersionsPanel"
```

Expected: only deleted/stale test references appear.

Delete:

```bash
git rm frontend/intent-routing-console/src/pages/TestRuns/ValidationVersionsPanel.tsx
git rm frontend/intent-routing-console/src/pages/TestRuns/testRunsCatalogVersionContract.test.ts
```

If `git rm` is blocked by sandbox permissions, remove those two tracked files with `apply_patch` delete hunks and stage them later.

- [ ] **Step 7: Run page contracts**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/testRunsPageContract.test.ts src/pages/TestRuns/catalogVersionStepContract.test.ts src/pages/TestRuns/csvCasesGridContract.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/index.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts frontend/intent-routing-console/src/pages/TestRuns/csvCasesGridContract.test.ts
git add -u frontend/intent-routing-console/src/pages/TestRuns
git commit -m "feat: convert test runs to wizard"
```

---

### Task 5: Pre-Merge Diagnostics Result Shell

**Files:**
- Create: `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
- Create: `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`

**Interfaces:**
- Consumes: `FutureFeatureNotice`.
- Produces: `TestRunDiagnosticsPanel` with no props in pre-merge state.
- After diagnostics backend merges, Task 6 replaces this shell with a real diagnostics panel.

- [ ] **Step 1: Write the diagnostics shell contract**

Create `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('TestRunDiagnosticsPanel pre-merge contract', () => {
  it('renders a dependency notice instead of fake diagnostics before backend merge', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('FutureFeatureNotice');
    expect(source).toContain('backend diagnostics');
    expect(source).toContain('2026-07-20-test-run-diagnostics-ux.md');
    expect(source).not.toContain('fetchTestRunDiagnostics');
    expect(source).not.toContain('/diagnostics');
  });
});
```

- [ ] **Step 2: Run the shell test to verify failure**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts
```

Expected: FAIL because `TestRunDiagnosticsPanel.tsx` does not exist.

- [ ] **Step 3: Implement the pre-merge diagnostics panel**

Create `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`:

```tsx
import { FutureFeatureNotice } from '@/components/FutureFeatureNotice';

export function TestRunDiagnosticsPanel() {
  return (
    <FutureFeatureNotice
      compact
      title="Test run diagnostics"
      phase="Future"
      backendRequirement="backend diagnostics plan docs/superpowers/plans/2026-07-20-test-run-diagnostics-ux.md is being implemented in another session and will be wired after it merges to main."
    />
  );
}
```

- [ ] **Step 4: Run diagnostics shell tests**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts src/pages/TestRuns/testRunsPageContract.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts frontend/intent-routing-console/src/pages/TestRuns/index.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts
git commit -m "feat: add diagnostics dependency shell"
```

---

### Task 6: Post-Merge Diagnostics Wiring

**Precondition:** Run this task only after the separate backend diagnostics session has merged `docs/superpowers/plans/2026-07-20-test-run-diagnostics-ux.md` implementation into `main`. Verify against `main` first; do not rely on diagnostics symbols that only exist on the current feature branch:

```bash
git grep -n "get_test_run_diagnostics\|TestRunDiagnosticsResponse\|/test-runs/\\{test_run_id\\}/diagnostics" main -- src/intent_routing/api/admin.py
git grep -n "diagnose_test_run\|DiagnosticIssue\|CatalogVersionDiagnosticStats" main -- src tests
```

Expected: both commands print backend diagnostics implementation and tests from `main`.

If the commands pass on `HEAD` but fail on `main`, stop after Task 5. That means the wizard branch is stacked on, or accidentally running from, the diagnostics branch before the backend dependency has merged.

After `main` passes the check, verify the working branch contains the same merged backend:

```bash
rg -n "get_test_run_diagnostics|TestRunDiagnosticsResponse|/test-runs/\\{test_run_id\\}/diagnostics" src/intent_routing/api/admin.py
rg -n "diagnose_test_run|DiagnosticIssue|CatalogVersionDiagnosticStats" src/intent_routing/diagnostics tests/unit tests/integration
```

Expected: both commands print backend diagnostics implementation and tests. If they do not, stop after Task 5 and do not wire a fake API.

**Files:**
- Modify: `frontend/intent-routing-console/src/types/api.d.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.ts`
- Modify: `frontend/intent-routing-console/src/services/adminServices.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts`
- Modify: `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`

**Interfaces:**
- Consumes: backend endpoint `GET /admin/v1/services/{service_id}/test-runs/{test_run_id}/diagnostics`.
- Produces:

```ts
export async function fetchTestRunDiagnostics(
  serviceId: string,
  testRunId: string,
): Promise<API.TestRunDiagnostics>;
```

`TestRunDiagnosticsPanel` props after merge:

```ts
type TestRunDiagnosticsPanelProps = {
  serviceId: string;
  testRunId?: string;
};
```

- [ ] **Step 1: Replace diagnostics panel contract with live API contract**

Replace `frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts` with:

```ts
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const read = (file: string) =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), file), 'utf8');

describe('TestRunDiagnosticsPanel contract after backend merge', () => {
  it('loads backend diagnostics for the selected test run', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('fetchTestRunDiagnostics');
    expect(source).toContain('primary_issue');
    expect(source).toContain('catalog_version');
    expect(source).toContain('result_counts');
    expect(source).not.toContain('FutureFeatureNotice');
  });

  it('maps stable issue codes to Korean UI copy in the frontend', () => {
    const source = read('TestRunDiagnosticsPanel.tsx');

    expect(source).toContain('catalog_version_not_active');
    expect(source).toContain('catalog_version_not_reproducible');
    expect(source).toContain('fallback_failures_dominant');
    expect(source).toContain('intent_mismatch_exists');
  });
});
```

- [ ] **Step 2: Add frontend diagnostics API types**

Append these types near Test Run types in `frontend/intent-routing-console/src/types/api.d.ts`:

```ts
  type TestRunDiagnosticIssue = {
    code: string;
    severity: 'blocker' | 'warning' | 'recommendation' | string;
    evidence: Record<string, unknown>;
  };

  type TestRunCatalogVersionDiagnostics = {
    intent_catalog_version: string;
    display_version: string | null;
    status: string;
    reproducibility_status: string;
    intent_count: number;
    example_count: number;
    embedding_count: number;
    test_run_model_version: string | null;
    test_run_vector_index_version: string | null;
    ready_vector_index_version: string | null;
    ready_vector_index_model_version: string | null;
  };

  type TestRunDiagnostics = {
    primary_issue: TestRunDiagnosticIssue | null;
    issues: TestRunDiagnosticIssue[];
    catalog_version: TestRunCatalogVersionDiagnostics;
    result_counts: Record<string, number>;
    actual_decision_counts: Record<string, number>;
  };
```

- [ ] **Step 3: Add service function and service test**

Modify `frontend/intent-routing-console/src/services/adminServices.ts`:

```ts
export async function fetchTestRunDiagnostics(
  serviceId: string,
  testRunId: string,
) {
  return request<API.TestRunDiagnostics>(
    servicePath(
      serviceId,
      `/test-runs/${encodeURIComponent(testRunId)}/diagnostics`,
    ),
    { method: 'GET' },
  );
}
```

Add this to `frontend/intent-routing-console/src/services/adminServices.test.ts`:

```ts
it('fetches test run diagnostics', async () => {
  await fetchTestRunDiagnostics('svc/admin', 'run/a');

  expect(requestMock).toHaveBeenCalledWith(
    '/services/svc%2Fadmin/test-runs/run%2Fa/diagnostics',
    { method: 'GET' },
  );
});
```

Also add `fetchTestRunDiagnostics` to the service test import list.

- [ ] **Step 4: Implement diagnostics panel**

Replace `frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx` with:

```tsx
import { useEffect, useMemo, useState } from 'react';
import { Alert, Descriptions, Empty, Spin, Space, Tag, Typography } from 'antd';
import { fetchTestRunDiagnostics } from '@/services/adminServices';

type TestRunDiagnosticsPanelProps = {
  serviceId: string;
  testRunId?: string;
};

const severityColor: Record<string, string> = {
  blocker: 'error',
  warning: 'warning',
  recommendation: 'processing',
};

const issueCopy: Record<string, string> = {
  catalog_version_not_active: '선택한 Catalog 버전이 활성 상태가 아닙니다.',
  catalog_version_not_reproducible: '선택한 Catalog 버전의 재현성 상태가 완전하지 않습니다.',
  catalog_version_has_no_intents: '선택한 Catalog 버전에 Intent가 없습니다.',
  catalog_version_has_no_examples: '선택한 Catalog 버전에 예시 데이터가 없습니다.',
  catalog_version_has_no_ready_vector_index: '선택한 Catalog 버전에 준비된 vector index가 없습니다.',
  catalog_version_has_no_embeddings: '선택한 Catalog 버전에 활성 embedding이 없습니다.',
  test_run_vector_index_not_ready: 'Test Run이 사용한 vector index가 현재 준비 상태와 일치하지 않습니다.',
  risk_case_failed: 'Risk 테스트 케이스가 실패했습니다.',
  fallback_failures_dominant: '실패한 케이스 중 fallback 결과가 많습니다.',
  intent_mismatch_exists: 'Decision은 맞았지만 Intent가 다른 실패가 있습니다.',
  pass_rate_below_gate: 'Pass rate가 release gate 기준보다 낮습니다.',
  review_rate_above_guidance: 'Review 비율이 권장 기준보다 높습니다.',
};

export function TestRunDiagnosticsPanel({
  serviceId,
  testRunId,
}: TestRunDiagnosticsPanelProps) {
  const [loading, setLoading] = useState(false);
  const [diagnostics, setDiagnostics] = useState<API.TestRunDiagnostics>();

  useEffect(() => {
    if (!testRunId) {
      setDiagnostics(undefined);
      return;
    }
    let alive = true;
    setLoading(true);
    fetchTestRunDiagnostics(serviceId, testRunId)
      .then((nextDiagnostics) => {
        if (alive) setDiagnostics(nextDiagnostics);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [serviceId, testRunId]);

  const primaryIssue = diagnostics?.primary_issue;
  const catalog = diagnostics?.catalog_version;
  const primaryCopy = useMemo(
    () =>
      primaryIssue
        ? issueCopy[primaryIssue.code] ?? primaryIssue.code
        : '진단 가능한 주요 이슈가 없습니다.',
    [primaryIssue],
  );

  if (!testRunId) {
    return (
      <section>
        <Typography.Title level={5} style={{ marginTop: 0 }}>
          진단
        </Typography.Title>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 Test Run이 없습니다." />
      </section>
    );
  }

  return (
    <section>
      <Typography.Title level={5} style={{ marginTop: 0 }}>
        진단
      </Typography.Title>
      <Spin spinning={loading}>
        {diagnostics ? (
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Alert
            type={primaryIssue?.severity === 'blocker' ? 'error' : 'info'}
            showIcon
            message={primaryCopy}
            description={
              primaryIssue
                ? `issue code: ${primaryIssue.code}`
                : 'Backend diagnostics did not identify a blocker, warning, or recommendation.'
            }
          />
          {catalog ? (
            <Descriptions bordered size="small" column={{ xs: 1, md: 2, xl: 3 }}>
              <Descriptions.Item label="Catalog">
                <Typography.Text code>{catalog.intent_catalog_version}</Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label="Status">{catalog.status}</Descriptions.Item>
              <Descriptions.Item label="Reproducibility">
                {catalog.reproducibility_status}
              </Descriptions.Item>
              <Descriptions.Item label="Intents">{catalog.intent_count}</Descriptions.Item>
              <Descriptions.Item label="Examples">{catalog.example_count}</Descriptions.Item>
              <Descriptions.Item label="Embeddings">{catalog.embedding_count}</Descriptions.Item>
              <Descriptions.Item label="Ready vector">
                {catalog.ready_vector_index_version ?? 'none'}
              </Descriptions.Item>
              <Descriptions.Item label="Test run vector">
                {catalog.test_run_vector_index_version ?? 'none'}
              </Descriptions.Item>
            </Descriptions>
          ) : null}
          <Space wrap>
            {diagnostics.issues.map((issue) => (
              <Tag key={issue.code} color={severityColor[issue.severity] ?? 'default'}>
                {issue.severity}: {issue.code}
              </Tag>
            ))}
          </Space>
          <Descriptions bordered size="small" column={{ xs: 1, md: 2 }}>
            <Descriptions.Item label="Result counts">
              <Typography.Text code>
                {JSON.stringify(diagnostics.result_counts)}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="Actual decisions">
              <Typography.Text code>
                {JSON.stringify(diagnostics.actual_decision_counts)}
              </Typography.Text>
            </Descriptions.Item>
          </Descriptions>
        </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="조회된 진단 결과가 없습니다." />
        )}
      </Spin>
    </section>
  );
}
```

- [ ] **Step 5: Wire the panel from the results step**

In `frontend/intent-routing-console/src/pages/TestRuns/index.tsx`, replace:

```tsx
<TestRunDiagnosticsPanel />
```

with:

```tsx
<TestRunDiagnosticsPanel
  serviceId={session.serviceId}
  testRunId={summary?.test_run_id}
/>
```

- [ ] **Step 6: Run diagnostics tests**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/services/adminServices.test.ts src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts src/pages/TestRuns/testRunsPageContract.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/intent-routing-console/src/types/api.d.ts frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/services/adminServices.test.ts frontend/intent-routing-console/src/pages/TestRuns/TestRunDiagnosticsPanel.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts frontend/intent-routing-console/src/pages/TestRuns/index.tsx frontend/intent-routing-console/src/pages/TestRuns/testRunsPageContract.test.ts
git commit -m "feat: wire test run diagnostics panel"
```

---

### Task 7: Verification And UI Guardrails

**Files:**
- Modify only files touched by Tasks 1-6 if verification finds a focused defect.

**Interfaces:**
- Consumes: completed wizard implementation.
- Produces: verified frontend behavior and guardrail evidence.

- [ ] **Step 1: Run targeted Test Runs tests**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run \
  src/pages/TestRuns/csvCaseBuilder.test.ts \
  src/pages/TestRuns/catalogVersionStepContract.test.ts \
  src/pages/TestRuns/csvImportModalContract.test.ts \
  src/pages/TestRuns/csvCasesGridContract.test.ts \
  src/pages/TestRuns/testRunDiagnosticsPanelContract.test.ts \
  src/pages/TestRuns/testRunsPageContract.test.ts \
  src/pages/TestRuns/testPolicy.test.ts
```

Expected: PASS.

- [ ] **Step 2: Run service contract tests**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/vitest run src/services/adminServices.test.ts
```

Expected: PASS.

- [ ] **Step 3: Run TypeScript**

Run from `frontend/intent-routing-console`:

```bash
./node_modules/.bin/tsc --noEmit
```

Expected: exit code 0.

- [ ] **Step 4: Run prohibited-pattern search**

Run from repo root:

```bash
rg -n "React Query|@tanstack|useQuery|useMutation|queryClient|invalidateQueries|axios|Authorization: Bearer|X-Admin-Token|X-Actor-Id|X-Actor-Roles|X-Service-Scope|server pagination|live polling" frontend/intent-routing-console/src/pages/TestRuns frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/types/api.d.ts
```

Expected: no matches.

- [ ] **Step 5: Required browser smoke after implementation**

Run this before claiming the wizard implementation is complete. If the local app cannot run or no authenticated Admin test state is available, record that browser smoke is unverified and do not describe the UI as browser-verified.

When the local app is runnable and authenticated test state exists, run the Admin UI and verify:

1. Test Runs opens with step 1 active.
2. Latest active Catalog version auto-selects.
3. 전체 버전 불러오기 shows historical versions without manual ID typing.
4. Step 2 policy buttons remain compact and detailed threshold values are only inside `CustomTestPolicyModal`.
5. CSV textarea exists only in the CSV 가져오기 modal.
6. Invalid CSV save shows row-specific validation errors and keeps the modal open.
7. Valid CSV save closes the modal and shows rows in the grid.
8. Importing a second valid CSV replaces the previous grid rows instead of appending.
9. CSV 내보내기 downloads the applied input cases from browser state and matches the grid rows.
10. Test Run creation sends `csv_text` matching the grid/export data, advances to step 3, and renders summary plus masked result rows.
11. Switching `serviceId` resets the wizard and closes any open CSV import modal if service switching is possible while the page remains mounted.
12. Before backend diagnostics merges, diagnostics area shows the external dependency notice.
13. After backend diagnostics merges and Task 6 runs, diagnostics area renders primary issue, catalog readiness, issue tags, and result count evidence from the real endpoint.

- [ ] **Step 6: Commit verification fixes if needed**

If verification required code fixes:

```bash
git add frontend/intent-routing-console/src/pages/TestRuns frontend/intent-routing-console/src/services/adminServices.ts frontend/intent-routing-console/src/types/api.d.ts
git commit -m "fix: align test runs wizard verification"
```

If no code changes were needed, do not create an empty commit.

---

## Self-Review

- Spec coverage:
  - Wizard/stepper layout is covered by Task 4.
  - Step 1 Intent Catalog selection, latest default, and historical lookup are covered by Task 1.
  - Step 2 policy buttons are preserved by Task 4 through `TestPolicyPanel`.
  - CSV textarea moves into Import modal only, and applied data renders as a grid through Tasks 2-4.
  - CSV validation uses backend-compatible header, row, duplicate, case type, and expected-intent rules in Task 2.
  - CSV export for current input data is browser-local in Task 3/4 and does not depend on Phase 2 backend export.
  - Step 3 result review keeps existing summary/results behavior in Task 4.
  - Backend-only diagnostics plan is not implemented here; Task 5 records the dependency honestly, and Task 6 wires it only after the other session merges to `main`.
- Claude plan review disposition:
  - F-1 accepted: added execution branch preflight and changed Task 6 to verify diagnostics against `main`, not only `HEAD`.
  - F-2 partially accepted: confirmed `TestPolicyPanel` does not auto-load latest policy, but the wizard intentionally keeps policy creation/selection in Step 2 through the existing four policy buttons instead of preserving the old combined policy+catalog refresh button.
  - F-3 accepted: changed Task 1 to extract catalog-selection logic from `ValidationVersionsPanel.tsx` instead of parallel-rewriting it from scratch.
  - F-4 partially accepted: no shared modal token utility exists; `CsvImportModal` now follows the same local `MODAL_TOKENS` naming and values as `CustomTestPolicyModal.tsx`.
  - M-1 accepted: service changes reset wizard state and close the CSV import modal.
  - M-2 accepted as soft UX handling: inactive or non-complete historical Catalog versions show a warning but do not block progression, because historical version testing is an explicit requirement.
  - T-1 and T-2 accepted: browser smoke is required when runnable/authenticated state exists, and it must verify CSV grid/import/export/create payload consistency.
- UI/UX skill review disposition:
  - Accepted `ai-intent-routing-admin-ui` constraints: no React Query/axios/trusted browser headers, Umi `request`, cookie auth, `FutureFeatureNotice` for unwired diagnostics, and no fake Phase 2 behavior remain explicit global constraints.
  - Accepted `ai-intent-routing-ant-design-ui` component constraints: operation Modal now requires centered fixed header/body/footer slots and `styles.content` padding reset for Ant Design 5.29.3; CSV grid remains one-line/ellipsis/Tooltip-based; business meaning is expressed with cells/tags, not row backgrounds.
  - Adjusted wizard layout standard: the plan now forbids nested Ant Design `Card` components and uses a page-level `ds-page-card steps-form-page-card` panel with un-nested result sections.
  - Recorded the `StepsForm` decision: ProComponents `StepsForm` remains preferred for pure forms, while manual Ant Design `Steps` is allowed here only because step 3 is a result-review surface rather than a form submission step.
  - Adjusted user-facing labels toward Korean for this workflow while preserving technical identifiers such as `test_run_id`, `csv_text`, and `intent_catalog_version`.
- Placeholder scan:
  - No placeholder markers remain.
  - The only conditional section is Task 6, which has an explicit precondition and concrete stop condition.
- Type consistency:
  - `CatalogVersionStep` passes full `API.CatalogVersionListItem` to the page and the page derives `intent_catalog_version`.
  - `CsvCasesGrid` and `CsvImportModal` both use `CsvCaseDraft` from `csvCaseBuilder.ts`.
  - Test Run creation sends `csv_text: buildCsvText(csvCases)` and preserves the existing `API.TestRunCreateRequest` shape.
  - Pre-merge diagnostics panel has no props and no API call.
  - Post-merge diagnostics panel receives `serviceId` and `testRunId`, matching `fetchTestRunDiagnostics(serviceId, testRunId)`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-20-test-runs-wizard-stepper-ux.md`. Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
