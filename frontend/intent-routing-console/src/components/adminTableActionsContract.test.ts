import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'AdminTableActions.tsx'), 'utf8');

describe('AdminTableActions contract', () => {
  it('uses visible accessible actions without tooltip-based icon controls', () => {
    const text = source();

    expect(text).toContain('export function AdminTableActions');
    expect(text).toContain('ReloadOutlined');
    expect(text).toContain('새로고침');
    expect(text).not.toContain('Tooltip');
    expect(text).not.toContain('ResizeObserver');
  });
});
