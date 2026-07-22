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
    expect(grid).toContain('memo');
    expect(grid).not.toContain('case_type');
    expect(grid).toContain('CSV 가져오기');
    expect(grid).toContain('CSV 내보내기');
    expect(grid).toContain('ellipsis');
    expect(grid).toContain('<Tooltip');
  });

  it('localizes four-column case metadata and exposes every truncated value in a tooltip', () => {
    const grid = read('CsvCasesGrid.tsx');

    expect(grid).toContain("title: '케이스 ID'");
    expect(grid).toContain("title: '질의'");
    expect(grid).toContain("title: '기대 인텐트'");
    expect(grid).toContain("title: '메모'");
    expect((grid.match(/<Tooltip/g) ?? []).length).toBeGreaterThanOrEqual(4);
    expect((grid.match(/<Typography\.Text[^>]*ellipsis/g) ?? []).length).toBeGreaterThanOrEqual(4);
  });

  it('renders expected intent identifiers as code', () => {
    const grid = read('CsvCasesGrid.tsx');

    expect(grid).toContain('<Typography.Text code ellipsis>{value}</Typography.Text>');
    expect(grid).not.toContain('expectedIntentRequired');
    expect(grid).not.toContain('<Tag');
  });
});
