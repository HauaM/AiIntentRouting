import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'), 'utf8');

describe('Releases page UX contract', () => {
  it('shows operational evidence and uses the shared release status', () => {
    expect(source).toContain("import { StatusTag } from '@/components/StatusTag'");
    expect(source).toContain('release-candidate-evidence');
    expect(source).toContain('선택한 Release 근거');
    expect(source).toContain('현재 active Release');
    expect(source).toContain('변경 후 active Release');
  });

  it('uses scoped Korean list copy without a free-text environment filter', () => {
    expect(source).toContain('Release 목록');
    expect(source).toContain('등록된 Release가 없습니다.');
    expect(source).toContain('scroll={{ x: 1120 }}');
    expect(source).not.toContain('Filter environment');
    expect(source).not.toContain('No releases');
  });

  it('describes Phase 2 as frontend-not-wired', () => {
    expect(source).toContain('frontend route, role gate, and UX tests');
    expect(source).not.toContain('backend contracts are required');
  });
});
