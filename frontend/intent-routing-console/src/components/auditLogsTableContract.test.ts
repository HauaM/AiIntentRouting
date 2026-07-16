import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const source = () =>
  readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'AuditLogsTable.tsx'), 'utf8');

describe('AuditLogsTable contract', () => {
  it('keeps audit logs read-only while using explicit warning-free table actions', () => {
    const text = source();

    expect(text).toContain('Audit logs are append-only');
    expect(text).toContain("import { AdminTableActions } from '@/components/AdminTableActions'");
    expect(text).toContain('options={false}');
    expect(text).toContain('actionRef.current?.reload()');
    expect(text).not.toContain('options={{ density: true');
    expect(text).not.toContain('ExportOutlined');
    expect(text).not.toContain('DeleteOutlined');
    expect(text).not.toContain('내보내기');
    expect(text).not.toContain('삭제');
  });
});
