import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'StatusTag.tsx'), 'utf8');

describe('StatusTag contract', () => {
  it('keeps semantic status mapping centralized with compact text and risk icons', () => {
    const text = source();

    expect(text).toContain("active: { bg: '#EAF3EE'");
    expect(text).toContain("risk: { bg: '#FBE9E7'");
    expect(text).toContain("pending: { bg: '#FDF3E3'");
    expect(text).toContain("disabled: { bg: '#EEF0F3'");
    expect(text).toContain("test: { bg: '#EAF3FC'");
    expect(text).toContain("blocker: { bg: '#FBE7E5'");
    expect(text).toContain("recommendation: { bg: '#EAF3FC'");
    expect(text).toContain('ExclamationCircleOutlined');
    expect(text).toContain("size?: 'small' | 'middle'");
    expect(text).toContain('export function StatusTag');
  });
});
