import { describe, expect, it } from 'vitest';
import {
  canAccessOrganizationDirectory,
  toDepartmentOptionSearchParams,
  toDepartmentCreateRequest,
  toOrganizationUserCreateRequest,
} from './directoryForms';

describe('directoryForms', () => {
  it('trims department form values', () => {
    expect(
      toDepartmentCreateRequest({ dept_number: ' 0969 ', name: ' IT지원부 ' }),
    ).toEqual({
      dept_number: '0969',
      name: 'IT지원부',
    });
  });

  it('trims organization user form values', () => {
    expect(
      toOrganizationUserCreateRequest({
        user_number: ' 21P0031 ',
        name: ' 홍길동 ',
        department_id: 'dept-1',
      }),
    ).toEqual({
      user_number: '21P0031',
      name: '홍길동',
      department_id: 'dept-1',
    });
  });

  it('allows organization directory access only for system admins', () => {
    expect(canAccessOrganizationDirectory([])).toBe(false);
    expect(canAccessOrganizationDirectory(['service_owner'])).toBe(false);
    expect(canAccessOrganizationDirectory(['service_owner', 'system_admin'])).toBe(true);
  });

  it('builds searchable department option params from the latest query', () => {
    expect(toDepartmentOptionSearchParams()).toEqual({ limit: 100 });
    expect(toDepartmentOptionSearchParams('   ')).toEqual({ limit: 100 });
    expect(toDepartmentOptionSearchParams(' 0969 IT지원부 ')).toEqual({
      query: '0969 IT지원부',
      limit: 100,
    });
  });
});
