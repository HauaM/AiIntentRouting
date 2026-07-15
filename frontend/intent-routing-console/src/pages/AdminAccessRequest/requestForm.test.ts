import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { toAdminAccessRequestCreateRequest } from './requestForm';

const requestPageSource = () =>
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), 'index.tsx'),
    'utf8',
  );

const loginPageSource = () =>
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), '..', 'Login', 'index.tsx'),
    'utf8',
  );

const configSource = () =>
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', 'config', 'config.ts'),
    'utf8',
  );

describe('admin access request form helpers', () => {
  it('trims applicant-entered values before submission', () => {
    expect(
      toAdminAccessRequestCreateRequest({
        user_number: ' 21P0031 ',
        name: ' 홍길동 ',
        department_id: ' dept-001 ',
        email: ' Admin.User@Example.com ',
        password: 'secret-passphrase',
        access_reason: ' Need Admin UI access for onboarding ',
      }),
    ).toEqual({
      user_number: '21P0031',
      name: '홍길동',
      department_id: 'dept-001',
      email: 'Admin.User@Example.com',
      password: 'secret-passphrase',
      access_reason: 'Need Admin UI access for onboarding',
    });
  });

  it('exposes the public request route from config and login', () => {
    expect(configSource()).toContain("path: '/admin-access-request'");
    expect(loginPageSource()).toContain('/admin-access-request');
    expect(requestPageSource()).toContain('Back to sign in');
  });

  it('renders backend submission errors as a form-level alert', () => {
    const source = requestPageSource();

    expect(source).toContain('Alert');
    expect(source).not.toContain("validateStatus={error ? 'error' : undefined}");
    expect(source).not.toContain('help={error}');
  });
});
