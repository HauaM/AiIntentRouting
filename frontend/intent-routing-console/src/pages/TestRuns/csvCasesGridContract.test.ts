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
