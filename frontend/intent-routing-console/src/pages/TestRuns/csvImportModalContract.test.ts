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

  it('formats the displayed CSV header identifiers as code', () => {
    const modal = read('CsvImportModal.tsx');

    expect(modal).toContain('<Typography.Text code>case_id</Typography.Text>');
    expect(modal).toContain('<Typography.Text code>expected_intent</Typography.Text>');
    expect(modal).toContain('<Typography.Text code>case_type</Typography.Text>');
  });
});
