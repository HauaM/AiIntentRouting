import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'IntentRouteMultiSelect.tsx'), 'utf8');

describe('IntentRouteMultiSelect layout contract', () => {
  it('does not force a 360px minimum width on mobile forms', () => {
    const text = source();

    expect(text).not.toContain('minWidth: 360');
    expect(text).toContain("style={{ width: '100%', maxWidth: '100%' }}");
  });

  it('keeps scope selection independent of page-specific disabled or loading state', () => {
    const text = source();

    expect(text).not.toContain('disabled?: boolean');
    expect(text).not.toContain('loading?: boolean');
    expect(text).not.toContain('disabled={disabled}');
    expect(text).not.toContain('loading={loading}');
  });
});
