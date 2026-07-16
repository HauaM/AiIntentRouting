import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'IntentCatalogTable.tsx'), 'utf8');

describe('IntentCatalogTable contract', () => {
  it('uses compact honest filters and explicit catalog semantics', () => {
    const text = source();

    expect(text).toContain("import { StatusTag } from '@/components/StatusTag'");
    expect(text).toContain('Intent ID 또는 이름 검색');
    expect(text).toContain('전체 상태');
    expect(text).toContain('포함 ${');
    expect(text).toContain('제외 ${');
    expect(text).toContain('className="text-mono admin-ellipsis-cell"');
    expect(text).toContain('copyable: true');
    expect(text).toContain('search={false}');
    expect(text).toContain('scroll={{ x:');
    expect(text).not.toContain('const statusColor');
  });
});
