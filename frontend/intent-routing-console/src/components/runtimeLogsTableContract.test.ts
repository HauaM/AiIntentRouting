import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'RuntimeLogsTable.tsx'), 'utf8');

describe('RuntimeLogsTable contract', () => {
  it('renders masked query only and does not use business row backgrounds', () => {
    const text = source();

    expect(text).toContain("dataIndex: 'query_masked'");
    expect(text).toContain('Masked query');
    expect(text).not.toContain('rowClassName');
    expect(text).not.toContain('row-risk');
    expect(text).not.toContain('query_raw');
  });

  it('renders a null environment as 환경 미상', () => {
    const text = source();

    expect(text).toContain("dataIndex: 'environment'");
    expect(text).toContain('환경 미상');
  });
});
