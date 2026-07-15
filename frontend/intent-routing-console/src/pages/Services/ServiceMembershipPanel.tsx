import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TableProps } from 'antd';
import { Alert, Card, Select, Space, Table, Tag, Tooltip, Typography, message } from 'antd';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import { StatusTag } from '@/components/StatusTag';
import {
  grantServiceRole,
  listServiceMembers,
  revokeServiceRole,
  searchAdminUsers,
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
      const users = await searchAdminUsers({ query, limit: 25 });
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

  const selectedUser = userOptions.find((option) => option.value === selectedUserId)?.user;

  const columns = useMemo<TableProps<ServiceMemberTableRow>['columns']>(
    () => [
      {
        title: 'User',
        dataIndex: 'display_name',
        width: 180,
        className: 'admin-nowrap-cell',
        render: (_, row) => (
          <Tooltip title={row.display_name}>
            <Typography.Text ellipsis style={{ maxWidth: 180 }}>
              {row.display_name}
            </Typography.Text>
          </Tooltip>
        ),
      },
      {
        title: 'User ID',
        dataIndex: 'user_id',
        width: 180,
        className: 'admin-nowrap-cell',
        render: (_, row) => (
          <Typography.Text code copyable ellipsis className="admin-ellipsis-cell">
            {row.user_id}
          </Typography.Text>
        ),
      },
      {
        title: 'Email',
        dataIndex: 'email',
        width: 220,
        className: 'admin-nowrap-cell',
        render: (_, row) => (
          <Tooltip title={row.email}>
            <Typography.Text ellipsis style={{ maxWidth: 200 }}>
              {row.email}
            </Typography.Text>
          </Tooltip>
        ),
      },
      {
        title: 'Status',
        dataIndex: 'status',
        width: 112,
        className: 'admin-nowrap-cell',
        render: (_, row) => <StatusTag status={row.status} />,
      },
      {
        title: 'Role',
        dataIndex: 'role',
        width: 160,
        className: 'admin-nowrap-cell',
        render: (_, row) => <Tag>{row.role}</Tag>,
      },
      {
        title: 'Assigned by',
        dataIndex: 'assigned_by',
        width: 180,
        className: 'admin-nowrap-cell',
        render: (_, row) => (
          <Tooltip title={row.assigned_by}>
            <Typography.Text ellipsis style={{ maxWidth: 160 }}>
              {row.assigned_by}
            </Typography.Text>
          </Tooltip>
        ),
      },
      {
        title: 'Assigned at',
        dataIndex: 'assigned_at',
        width: 180,
        className: 'admin-nowrap-cell',
        render: (_, row) => (
          <Typography.Text ellipsis style={{ maxWidth: 160 }}>
            {row.assigned_at}
          </Typography.Text>
        ),
      },
      {
        title: 'Action',
        width: 112,
        className: 'admin-nowrap-cell',
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
          <div style={{ display: 'grid', gap: 4 }}>
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
                <div style={{ display: 'grid', gap: 2 }}>
                  <Typography.Text>{data.user.email}</Typography.Text>
                  <Typography.Text type="secondary">
                    {data.user.display_name} / {data.user.status}
                  </Typography.Text>
                </div>
              )}
            />
          </div>
          <div style={{ display: 'grid', gap: 4 }}>
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
          </div>
          <ConfirmActionButton
            type="primary"
            title="Grant service role?"
            okText="Grant role"
            disabled={!canManage || !selectedUserId || !selectedRole || granting}
            onConfirm={handleGrant}
            content={
              <Space direction="vertical" size={4}>
                <Typography.Text>
                  {selectedServiceId} 서비스에 {selectedRole ?? '-'} 권한을 부여합니다.
                </Typography.Text>
                <Typography.Text type="secondary">
                  대상: {selectedUser?.email ?? selectedUserId ?? '-'}
                </Typography.Text>
              </Space>
            }
          >
            Grant role
          </ConfirmActionButton>
        </Space>
        <Table<ServiceMemberTableRow>
          className="admin-scroll-table"
          rowKey="rowKey"
          size="small"
          loading={loadingMembers}
          pagination={false}
          columns={columns}
          dataSource={members}
          scroll={{ x: 760, y: 320 }}
          tableLayout="fixed"
        />
      </Space>
    </Card>
  );
}
