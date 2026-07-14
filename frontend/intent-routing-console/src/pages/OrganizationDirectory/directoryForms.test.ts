import { describe, expect, it } from 'vitest';
import {
  canAccessOrganizationDirectory,
  formatDepartmentNumber,
  formatOrganizationUserNumber,
  toDepartmentOption,
  toDepartmentOptionSearchParams,
  toDepartmentCreateRequest,
  toDepartmentUseYnPatchRequest,
  toOrganizationUserCreateRequest,
  toOrganizationUserUseYnPatchRequest,
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
    expect(toDepartmentOptionSearchParams()).toEqual({ use_yn: 'Y', limit: 100 });
    expect(toDepartmentOptionSearchParams('   ')).toEqual({ use_yn: 'Y', limit: 100 });
    expect(toDepartmentOptionSearchParams(' 0969 IT지원부 ')).toEqual({
      query: '0969 IT지원부',
      use_yn: 'Y',
      limit: 100,
    });
  });

  it('uses only the department name for department option labels', () => {
    expect(
      toDepartmentOption({
        id: 'dept-1',
        dept_number: '0969',
        name: 'IT지원부',
        use_yn: 'Y',
        created_by: 'system_admin',
        updated_by: 'system_admin',
        created_at: '2026-07-14T12:43:24Z',
        updated_at: '2026-07-14T12:43:24Z',
      }),
    ).toEqual({
      label: 'IT지원부',
      value: 'dept-1',
    });
  });

  it('formats department numbers without local uniqueness suffixes for table display', () => {
    expect(formatDepartmentNumber('0969-06c88b23')).toBe('0969');
    expect(formatDepartmentNumber('0969')).toBe('0969');
    expect(formatDepartmentNumber('')).toBe('');
  });

  it('formats organization user numbers without local uniqueness suffixes for table display', () => {
    expect(formatOrganizationUserNumber('21P0031-089ba09e')).toBe('21P0031');
    expect(formatOrganizationUserNumber('21P0031')).toBe('21P0031');
    expect(formatOrganizationUserNumber('')).toBe('');
  });

  it('builds a department use flag patch request', () => {
    expect(toDepartmentUseYnPatchRequest('N')).toEqual({ use_yn: 'N' });
    expect(toDepartmentUseYnPatchRequest('Y')).toEqual({ use_yn: 'Y' });
  });

  it('builds an organization user use flag patch request', () => {
    expect(toOrganizationUserUseYnPatchRequest('N')).toEqual({ use_yn: 'N' });
    expect(toOrganizationUserUseYnPatchRequest('Y')).toEqual({ use_yn: 'Y' });
  });
});
