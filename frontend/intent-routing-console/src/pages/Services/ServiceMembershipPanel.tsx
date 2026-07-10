import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TableProps } from 'antd';
import { Alert, Button, Card, Select, Space, Table, Tag, Typography, message } from 'antd';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import {
  grantServiceRole,
  listAdminUsers,
  listServiceMembers,
  revokeServiceRole,
} from '@/services/adminServices';
import {
  isCurrentServiceRequest,
  isCurrentServiceRow,
  memberRowsForTable,
  serviceRoleOptions,
  shouldClearMembershipState,
  toServiceRoleGrantRequest,
  type ServiceMemberTableRow,
} from './serviceMembers';

type ServiceMembershipPanelProps = {
  selectedService?: API.AccessibleService;
  canManage: boolean;
  onMembershipChanged: () => Promise<unknown> | unknown;
};

type UserSelectOption = {
  label: string;
  value: string;
  user: API.AdminUserLookup;
};

const isForbidden = (error: unknown) => (error as any)?.response?.status === 403;

const toUserOption = (user: API.AdminUserLookup): UserSelectOption => ({
  label: `${user.email} / ${user.display_name} / ${user.status}`,
  value: user.user_id,
  user,
});

export function ServiceMembershipPanel({
  selectedService,
  canManage,
  onMembershipChanged,
}: ServiceMembershipPanelProps) {
  const selectedServiceId = selectedService?.service_id ?? '';
  const serviceIdRef = useRef(selectedServiceId);
  const memberRequestSeqRef = useRef(0);
  const userSearchRequestSeqRef = useRef(0);
  const userSearchQueryRef = useRef('');
  const grantRequestSeqRef = useRef(0);
  const [members, setMembers] = useState<ServiceMemberTableRow[]>([]);
  const [userOptions, setUserOptions] = useState<UserSelectOption[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>();
  const [selectedRole, setSelectedRole] = useState<API.ServiceRole>();
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [searchingUsers, setSearchingUsers] = useState(false);
  const [granting, setGranting] = useState(false);
  const [membershipError, setMembershipError] = useState<string>();

  const clearMembershipState = useCallback(() => {
    memberRequestSeqRef.current += 1;
    userSearchRequestSeqRef.current += 1;
    userSearchQueryRef.current = '';
    grantRequestSeqRef.current += 1;
    setSelectedUserId(undefined);
    setSelectedRole(undefined);
    setUserOptions([]);
    setMembers([]);
    setMembershipError(undefined);
    setLoadingMembers(false);
    setSearchingUsers(false);
    setGranting(false);
  }, []);

  const loadMembers = useCallback(async (serviceId: string) => {
    const expectedServiceId = serviceId.trim();
    if (!expectedServiceId) return;
    const requestSeq = (memberRequestSeqRef.current += 1);
    const isCurrentRequest = () =>
      isCurrentServiceRequest({
        requestSeq,
        latestRequestSeq: memberRequestSeqRef.current,
        expectedServiceId,
        currentServiceId: serviceIdRef.current,
      });

    setLoadingMembers(true);
    setMembershipError(undefined);
    try {
      const rows = await listServiceMembers(expectedServiceId);
      if (!isCurrentRequest()) return;
      setMembers(memberRowsForTable(rows));
    } catch (error) {
      if (!isCurrentRequest()) return;
      setMembers([]);
      setMembershipError(
        isForbidden(error)
          ? 'Membership list access requires system_admin.'
          : 'Failed to load service members.',
      );
    } finally {
      if (isCurrentRequest()) setLoadingMembers(false);
    }
  }, []);

  useEffect(() => {
    const previousServiceId = serviceIdRef.current;
    serviceIdRef.current = selectedServiceId;
    if (shouldClearMembershipState(previousServiceId, selectedServiceId)) {
      clearMembershipState();
    }
    if (selectedServiceId) {
      loadMembers(selectedServiceId);
    }
  }, [clearMembershipState, loadMembers, selectedServiceId]);

  const handleUserSearch = useCallback(async (query: string) => {
    const expectedServiceId = selectedServiceId.trim();
    if (!canManage || !expectedServiceId) {
      userSearchRequestSeqRef.current += 1;
      userSearchQueryRef.current = query;
      setUserOptions([]);
      setSearchingUsers(false);
      return;
    }

    const requestSeq = (userSearchRequestSeqRef.current += 1);
    userSearchQueryRef.current = query;
    const isCurrentRequest = () =>
      isCurrentServiceRequest({
        requestSeq,
        latestRequestSeq: userSearchRequestSeqRef.current,
        expectedServiceId,
        currentServiceId: serviceIdRef.current,
        expectedQuery: query,
        currentQuery: userSearchQueryRef.current,
      });

    setSearchingUsers(true);
    try {
      const users = await listAdminUsers({ query, limit: 25 });
      if (!isCurrentRequest()) return;
      setUserOptions(users.map(toUserOption));
    } catch (error) {
      if (!isCurrentRequest()) return;
      setUserOptions([]);
      message.error(
        isForbidden(error)
          ? 'User search requires system_admin.'
          : 'Failed to search admin users.',
      );
    } finally {
      if (isCurrentRequest()) setSearchingUsers(false);
    }
  }, [canManage, selectedServiceId]);

  const handleGrant = useCallback(async () => {
    const expectedServiceId = selectedServiceId.trim();
    if (!expectedServiceId || !selectedUserId || !selectedRole) return;
    const grantRequest = toServiceRoleGrantRequest(selectedUserId, selectedRole);
    const requestSeq = (grantRequestSeqRef.current += 1);
    const isCurrentRequest = () =>
      isCurrentServiceRequest({
        requestSeq,
        latestRequestSeq: grantRequestSeqRef.current,
        expectedServiceId,
        currentServiceId: serviceIdRef.current,
      });

    setGranting(true);
    try {
      await grantServiceRole(expectedServiceId, grantRequest.userId, grantRequest.payload);
      if (!isCurrentRequest()) return;
      message.success('Service role granted.');
      setSelectedUserId(undefined);
      setSelectedRole(undefined);
      await loadMembers(expectedServiceId);
      if (isCurrentRequest()) await onMembershipChanged();
    } finally {
      if (isCurrentRequest()) setGranting(false);
    }
  }, [loadMembers, onMembershipChanged, selectedRole, selectedServiceId, selectedUserId]);

  const handleRevoke = useCallback(
    async (row: ServiceMemberTableRow) => {
      if (!isCurrentServiceRow(row.service_id, serviceIdRef.current)) {
        message.warning('Selected Service changed. Reopen revoke for the current Service.');
        throw new Error('Selected Service changed before revoke.');
      }

      const expectedServiceId = row.service_id.trim();
      await revokeServiceRole(expectedServiceId, row.user_id, row.role);
      if (!isCurrentServiceRow(expectedServiceId, serviceIdRef.current)) return;
      await loadMembers(expectedServiceId);
      if (isCurrentServiceRow(expectedServiceId, serviceIdRef.current)) {
        await onMembershipChanged();
      }
    },
    [loadMembers, onMembershipChanged],
  );

  const columns = useMemo<TableProps<ServiceMemberTableRow>['columns']>(
    () => [
      {
        title: 'User',
        dataIndex: 'display_name',
        render: (_, row) => (
          <Space direction="vertical" size={0}>
            <Typography.Text>{row.display_name}</Typography.Text>
            <Typography.Text type="secondary">{row.user_id}</Typography.Text>
          </Space>
        ),
      },
      {
        title: 'Email',
        dataIndex: 'email',
      },
      {
        title: 'Status',
        dataIndex: 'status',
        width: 112,
        render: (_, row) => (
          <Tag color={row.status === 'active' ? 'green' : 'default'}>{row.status}</Tag>
        ),
      },
      {
        title: 'Role',
        dataIndex: 'role',
        render: (_, row) => <Tag>{row.role}</Tag>,
      },
      {
        title: 'Assigned by',
        dataIndex: 'assigned_by',
      },
      {
        title: 'Assigned at',
        dataIndex: 'assigned_at',
      },
      {
        title: 'Action',
        width: 112,
        render: (_, row) => (
          <ConfirmActionButton
            danger
            type="link"
            size="small"
            title="Revoke service role?"
            okText="Revoke"
            content={`Revoke ${row.role} from ${row.email}.`}
            disabled={!canManage}
            onConfirm={() => handleRevoke(row)}
          >
            Revoke
          </ConfirmActionButton>
        ),
      },
    ],
    [canManage, handleRevoke],
  );

  return (
    <Card title="Service membership">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {!canManage ? (
          <Alert
            type="info"
            showIcon
            message="Membership management requires system_admin"
            description="You can inspect the selected Service membership when the API allows it, but grant and revoke controls are disabled."
          />
        ) : null}
        {membershipError ? <Alert type="warning" showIcon message={membershipError} /> : null}
        <Space wrap align="end" size={12}>
          <Space direction="vertical" size={4}>
            <Typography.Text>User</Typography.Text>
            <Select<string, UserSelectOption>
              showSearch
              allowClear
              disabled={!canManage}
              loading={searchingUsers}
              filterOption={false}
              placeholder="Search admin users"
              value={selectedUserId}
              options={userOptions}
              style={{ width: 320 }}
              onSearch={handleUserSearch}
              onChange={setSelectedUserId}
              optionRender={({ data }) => (
                <Space direction="vertical" size={0}>
                  <Typography.Text>{data.user.email}</Typography.Text>
                  <Typography.Text type="secondary">
                    {data.user.display_name} / {data.user.status}
                  </Typography.Text>
                </Space>
              )}
            />
          </Space>
          <Space direction="vertical" size={4}>
            <Typography.Text>Role</Typography.Text>
            <Select
              allowClear
              disabled={!canManage}
              placeholder="Select role"
              value={selectedRole}
              options={serviceRoleOptions}
              style={{ width: 220 }}
              onChange={setSelectedRole}
            />
          </Space>
          <Button
            type="primary"
            disabled={!canManage || !selectedUserId || !selectedRole}
            loading={granting}
            onClick={handleGrant}
          >
            Grant role
          </Button>
        </Space>
        <Table<ServiceMemberTableRow>
          rowKey="rowKey"
          size="small"
          loading={loadingMembers}
          pagination={false}
          columns={columns}
          dataSource={members}
        />
      </Space>
    </Card>
  );
}
