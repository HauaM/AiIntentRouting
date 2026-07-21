import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'), 'utf8');

describe('Runtime Logs page environment filter contract', () => {
  it('offers all, dev, qa, and prod without sending an environment for all', () => {
    expect(source).toContain("value: 'dev'");
    expect(source).toContain("value: 'qa'");
    expect(source).toContain("value: 'prod'");
    expect(source).toContain('environment={selectedEnvironment || undefined}');
  });
});
