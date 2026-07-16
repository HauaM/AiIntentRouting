import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const pagesDir = dirname(fileURLToPath(import.meta.url));
const readPage = (file: string) => readFileSync(join(pagesDir, file), 'utf8');

describe('Drawer and Modal Form ownership contract', () => {
  it('does not use deprecated destroyOnClose in Admin UI pages', () => {
    for (const file of [
      'ApiKeys/index.tsx',
      'Intents/index.tsx',
      'OrganizationDirectory/index.tsx',
      'PermissionManagement/index.tsx',
      'Releases/index.tsx',
      'Services/index.tsx',
      'TestRuns/index.tsx',
    ]) {
      expect(readPage(file)).not.toContain('destroyOnClose');
    }
  });

  it('keeps destroyed intent Drawer forms mount-owned', () => {
    const text = readPage('Intents/index.tsx');

    expect(text).not.toContain('Form.useForm<IntentFormValues>');
    expect(text).not.toContain('Form.useForm<ExampleFormValues>');
    expect(text).toContain('initialValues={intentFormInitialValues}');
    expect(text).toContain('initialValues={exampleFormInitialValues}');
  });

  it('does not reset Modal.confirm forms before they are mounted', () => {
    const text = readPage('PermissionManagement/index.tsx');

    expect(text).not.toContain('transferReasonForm.resetFields();');
    expect(text).not.toContain('rejectRequestForm.resetFields();');
    expect((text.match(/clearOnDestroy/g) ?? []).length).toBeGreaterThanOrEqual(2);
  });

  it('documents intentionally force-rendered imperative Modal forms', () => {
    const text = readPage('OrganizationDirectory/index.tsx');

    expect(text).toContain('forceRender');
    expect(text).toContain('keeps the imperative form instance connected');
  });
});
