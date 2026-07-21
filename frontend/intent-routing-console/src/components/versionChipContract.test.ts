import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(resolve(process.cwd(), 'src/components/VersionChip.tsx'), 'utf8');

describe('VersionChip contract', () => {
  it('can truncate the visible ID while keeping copyable text as the full value', () => {
    const text = source();

    expect(text).toContain('maxDisplayLength?: number');
    expect(text).toContain('displayValue');
    expect(text).toContain('value.slice(0, maxDisplayLength)');
    expect(text).toContain("`${value.slice(0, maxDisplayLength)}...`");
    expect(text).toContain('copyable={{ text: value }}');
  });

  it('does not force a duplicate inline label when the surrounding field already has one', () => {
    const text = source();

    expect(text).toContain('label?: string');
    expect(text).toContain('{label ?');
  });
});
