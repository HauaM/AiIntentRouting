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

  it('localizes case metadata and exposes every truncated value in a tooltip', () => {
    const grid = read('CsvCasesGrid.tsx');

    expect(grid).toContain("title: '케이스 ID'");
    expect(grid).toContain("title: '질의'");
    expect(grid).toContain("title: '기대 인텐트'");
    expect(grid).toContain("title: '케이스 유형'");
    expect(grid).toContain("title: '메모'");
    expect(grid).toContain("positive: '정상'");
    expect(grid).toContain("confusing: '혼동'");
    expect((grid.match(/<Tooltip/g) ?? []).length).toBeGreaterThanOrEqual(4);
    expect((grid.match(/<Typography\.Text[^>]*ellipsis/g) ?? []).length).toBeGreaterThanOrEqual(4);
  });

  it('renders expected intent identifiers as code', () => {
    const grid = read('CsvCasesGrid.tsx');

    expect(grid).toContain('<Typography.Text code ellipsis>{value}</Typography.Text>');
  });
});
