import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), 'ReleaseCandidateSelect.tsx'),
  'utf8',
);

describe('ReleaseCandidateSelect responsive contract', () => {
  it('fills its bounded container without forcing a desktop minimum width', () => {
    expect(source).toContain('className="release-candidate-select"');
    expect(source).toContain("style={{ width: '100%' }}");
    expect(source).not.toContain('minWidth: 420');
  });
});
