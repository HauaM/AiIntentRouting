import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () => readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'), 'utf8');
const styleSource = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), '../../global.less'), 'utf8');

describe('Intents page contract', () => {
  it('uses neutral next-step copy and named detail sections', () => {
    const text = source();

    expect(text).toContain('다음 단계: Test Runs에서 검증');
    expect(text).not.toContain('Catalog work ready for validation');
    expect(text).toContain('기본 정보');
    expect(text).toContain('키워드');
    expect(text).toContain('포함 키워드');
    expect(text).toContain('제외 키워드');
    expect(text).toContain("selected.created_at ?? '없음'");
    expect(text).toContain("selected.updated_at ?? '없음'");
    expect(text).toContain('<StatusTag status={selected.status}');
    expect(text).toContain('className="intent-detail-examples-header"');
    expect(text).toContain('scroll={{ x: 512 }}');
    expect(text).not.toContain('scroll={{ x: true }}');
    expect(text).not.toContain('scroll={{ x: 720 }}');
    expect(text).not.toContain('scroll={{ x: 560 }}');
    expect(text).not.toContain('width={620}');
  });

  it('supports multiline positive and negative example entry', () => {
    const text = source();

    expect(text).toContain("positive_text_raw");
    expect(text).toContain("negative_text_raw");
    expect(text).toContain("buildExampleCreateRequests(values)");
    expect(text).toContain("Promise.all(");
    expect(text).toContain("positiveCount");
    expect(text).toContain("negativeCount");
    expect(text).toContain("exampleFormMode === 'create'");
    expect(text).toContain("exampleFormMode === 'edit'");
  });

  it('does not expose or submit a manual test case identifier for examples', () => {
    const text = source();

    expect(text).not.toContain('Test case ID');
    expect(text).not.toContain('testCaseId');
    expect(text).not.toContain('test_case_id');
  });

  it('loads catalog version history only when history exists and shows page state', () => {
    const text = source();

    expect(text).toContain('loadLatestCatalogVersionState');
    expect(text).toContain('listCatalogVersions(session.serviceId, { limit: 1 })');
    expect(text).toContain('setCatalogHistoryExists(Boolean(latestVersion))');
    expect(text).toContain('catalogHistoryExists ? (');
    expect(text).toContain('catalogPageState');
    expect(text).toContain("catalogPageState.mode === 'draft'");
    expect(text).toContain('Catalog version 불러오기');
    expect(text).toContain('버전 상태');
    expect(text).toContain('수정된 초안');
  });

  it('opens a compact all-history catalog version loader without status filtering', () => {
    const text = source();

    expect(text).toContain('openCatalogVersionLoadModal');
    expect(text).toContain('listCatalogVersions(session.serviceId, { limit: 100 })');
    expect(text).toContain('catalogVersionLoadOpen');
    expect(text).toContain('catalogVersionSelection');
    expect(text).toContain('loadCatalogVersionToDraft');
    expect(text).toContain('confirmLoadCatalogVersionToDraft');
    expect(text).toContain("setCatalogPageState({ mode: 'draft', sourceVersion: loaded })");
    expect(text).toContain('display_version');
    expect(text).toContain('created_at');
    expect(text).toContain('release_count');
    expect(text).toContain('status');
    expect(text).toContain('description');
  });

  it('marks catalog page state as draft after editable catalog mutations', () => {
    const text = source();

    expect(text).toContain('markCatalogPageDraft');
    expect(text).toContain('void loadLatestCatalogVersionState();');
    expect(text).toContain('setCatalogPageState((current) =>');
    expect(text).toContain('createIntent(serviceId');
    expect(text).toContain('patchIntent(serviceId');
    expect(text).toContain('deleteIntent(serviceId');
    expect(text).toContain('createExample(serviceId');
    expect(text).toContain('patchExample(serviceId');
    expect(text).toContain('approveExample(example.service_id');
    expect(text).toContain('deleteExample(example.service_id');
  });

  it('supports intent delete and example edit/delete actions', () => {
    const text = source();

    expect(text).toContain('deleteIntent');
    expect(text).toContain('deleteExample');
    expect(text).toContain('patchExample');
    expect(text).toContain('openEditExample');
    expect(text).toContain('handleDeleteIntent');
    expect(text).toContain('Example 편집');
    expect(text).toContain('삭제');
    expect(text).toContain('수정/삭제 시 승인된 Example의 embedding도 함께 갱신 또는 제거됩니다.');
    expect(text).not.toContain('현재 백엔드는 Example 추가와 승인만 제공합니다.');
    expect(text).not.toContain('편집/삭제/반려는 Phase 2 항목입니다.');
  });

  it('uses shadowless detail drawer action buttons', () => {
    const text = source();
    const styles = styleSource();

    expect(text).toContain('className="intent-detail-actions"');
    expect(styles).toContain('.intent-detail-actions .ant-btn');
    expect(styles).toContain('box-shadow: none;');
  });

  it('keeps example text readable without widening the detail drawer', () => {
    const text = source();
    const styles = styleSource();

    expect(text).toContain('Dropdown');
    expect(text).toContain('MoreOutlined');
    expect(text).toContain('className="intent-examples-table"');
    expect(text).toContain("className=\"intent-example-text\"");
    expect(text).toContain("width: 220");
    expect(text).toContain("scroll={{ x: 512 }}");
    expect(text).not.toContain("scroll={{ x: true }}");
    expect(text).not.toContain("scroll={{ x: 720 }}");
    expect(text).not.toContain("width: 136");
    expect(text).not.toContain("width: 176");
    expect(styles).toContain('.intent-examples-table');
    expect(styles).toContain('overflow-x: hidden;');
    expect(styles).toContain('.intent-example-text');
    expect(styles).toContain('word-break: keep-all;');
    expect(styles).toContain('overflow-wrap: anywhere;');
  });
});
