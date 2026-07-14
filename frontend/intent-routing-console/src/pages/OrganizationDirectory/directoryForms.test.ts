import { describe, expect, it } from 'vitest';
import {
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
});
