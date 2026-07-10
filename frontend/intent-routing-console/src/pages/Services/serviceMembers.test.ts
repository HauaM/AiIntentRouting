import { describe, expect, it } from 'vitest';
import {
  isCurrentServiceRequest,
  isCurrentServiceRow,
  memberRowsForTable,
  serviceRoleOptions,
  shouldClearMembershipState,
  toServiceRoleGrantRequest,
} from './serviceMembers';

describe('service membership helpers', () => {
  it('exposes the exact C-2 service role options for grant controls', () => {
    expect(serviceRoleOptions).toEqual([
      { label: 'service_owner', value: 'service_owner' },
      { label: 'service_developer', value: 'service_developer' },
      { label: 'service_operator', value: 'service_operator' },
      { label: 'auditor', value: 'auditor' },
    ]);
  });

  it('trims the user id and builds the service role grant request payload', () => {
    expect(toServiceRoleGrantRequest('  user-123  ', 'service_developer')).toEqual({
      userId: 'user-123',
      payload: { role: 'service_developer' },
    });
  });

  it('rejects blank user ids before creating a role grant request', () => {
    expect(() => toServiceRoleGrantRequest('   ', 'service_owner')).toThrow(
      'user_id is required',
    );
  });

  it('rejects blank or invalid roles before creating a role grant request', () => {
    expect(() => toServiceRoleGrantRequest('user-123', '   ')).toThrow(
      'role is invalid',
    );
    expect(() => toServiceRoleGrantRequest('user-123', 'system_admin')).toThrow(
      'role is invalid',
    );
  });

  it('flattens API service members into stable table rows by user id and role', () => {
    const members: API.ServiceMember[] = [
      {
        service_id: 'svc-a',
        user: {
          user_id: 'user-1',
          email: 'one@example.com',
          display_name: 'One User',
          status: 'active',
        },
        roles: [
          {
            role: 'service_developer',
            assigned_by: 'admin-1',
            assigned_at: '2026-07-10T00:00:00Z',
          },
          {
            role: 'auditor',
            assigned_by: 'admin-2',
            assigned_at: '2026-07-10T01:00:00Z',
          },
        ],
      },
      {
        service_id: 'svc-b',
        user: {
          user_id: 'user-2',
          email: 'two@example.com',
          display_name: 'Two User',
          status: 'inactive',
        },
        roles: [
          {
            role: 'service_operator',
            assigned_by: 'admin-1',
            assigned_at: '2026-07-10T02:00:00Z',
          },
        ],
      },
    ];

    expect(memberRowsForTable(members)).toEqual([
      {
        rowKey: 'user-1:service_developer',
        service_id: 'svc-a',
        user_id: 'user-1',
        email: 'one@example.com',
        display_name: 'One User',
        status: 'active',
        role: 'service_developer',
        assigned_by: 'admin-1',
        assigned_at: '2026-07-10T00:00:00Z',
      },
      {
        rowKey: 'user-1:auditor',
        service_id: 'svc-a',
        user_id: 'user-1',
        email: 'one@example.com',
        display_name: 'One User',
        status: 'active',
        role: 'auditor',
        assigned_by: 'admin-2',
        assigned_at: '2026-07-10T01:00:00Z',
      },
      {
        rowKey: 'user-2:service_operator',
        service_id: 'svc-b',
        user_id: 'user-2',
        email: 'two@example.com',
        display_name: 'Two User',
        status: 'inactive',
        role: 'service_operator',
        assigned_by: 'admin-1',
        assigned_at: '2026-07-10T02:00:00Z',
      },
    ]);
  });

  it('clears membership state only when the selected service changes after trim', () => {
    expect(shouldClearMembershipState(' svc-a ', 'svc-a')).toBe(false);
    expect(shouldClearMembershipState('svc-a', ' svc-b ')).toBe(true);
  });

  it('applies async state only for the latest request on the expected service', () => {
    expect(
      isCurrentServiceRequest({
        requestSeq: 2,
        latestRequestSeq: 2,
        expectedServiceId: ' svc-a ',
        currentServiceId: 'svc-a',
      }),
    ).toBe(true);
    expect(
      isCurrentServiceRequest({
        requestSeq: 1,
        latestRequestSeq: 2,
        expectedServiceId: 'svc-a',
        currentServiceId: 'svc-a',
      }),
    ).toBe(false);
    expect(
      isCurrentServiceRequest({
        requestSeq: 2,
        latestRequestSeq: 2,
        expectedServiceId: 'svc-a',
        currentServiceId: 'svc-b',
      }),
    ).toBe(false);
    expect(
      isCurrentServiceRequest({
        requestSeq: 2,
        latestRequestSeq: 2,
        expectedServiceId: 'svc-a',
        currentServiceId: 'svc-a',
        expectedQuery: 'lee',
        currentQuery: 'kim',
      }),
    ).toBe(false);
  });

  it('blocks row writes when the selected service has changed', () => {
    expect(isCurrentServiceRow(' svc-a ', 'svc-a')).toBe(true);
    expect(isCurrentServiceRow('svc-a', 'svc-b')).toBe(false);
    expect(isCurrentServiceRow('svc-a', '')).toBe(false);
  });
});
