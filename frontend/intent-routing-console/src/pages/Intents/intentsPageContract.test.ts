import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () => readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'), 'utf8');

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
    expect(text).toContain('scroll={{ x: true }}');
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
    expect(text).not.toContain('name="example_type"');
  });
});
