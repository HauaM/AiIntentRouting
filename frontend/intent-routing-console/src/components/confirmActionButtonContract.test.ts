import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'ConfirmActionButton.tsx'), 'utf8');

describe('ConfirmActionButton contract', () => {
  it('supports high-risk typed confirmation without breaking existing props', () => {
    const text = source();

    expect(text).toContain("riskLevel?: 'low' | 'high'");
    expect(text).toContain('requireTypedConfirmation?: boolean');
    expect(text).toContain('confirmText?: string');
    expect(text).toContain('Modal.confirm({');
    expect(text).toContain('cancelText:');
    expect(text).toContain('typed confirmation');
  });
});
