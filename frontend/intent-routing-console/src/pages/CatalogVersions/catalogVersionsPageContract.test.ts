import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const configSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../../../config/config.ts'),
  'utf8',
);
const navigationSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../../components/adminShellNavigation.ts'),
  'utf8',
);

describe('CatalogVersions page contract', () => {
  it('redirects legacy bookmarks to the consolidated Intents screen', () => {
    expect(configSource).toContain("path: '/catalog-versions'");
    expect(configSource).toContain("redirect: '/intents'");
    expect(configSource).not.toContain("component: './CatalogVersions'");
    expect(navigationSource).not.toContain("name: 'Catalog 버전관리'");
    expect(navigationSource).not.toContain("path: '/catalog-versions'");
  });
});
