import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TableProps } from 'antd';
import {
  Alert,
  Card,
  Empty,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
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
          ? '멤버 목록을 보려면 system_admin 권한이 필요합니다.'
          : 'Service 멤버 목록을 불러오지 못했습니다.',
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
          ? '관리자 계정 검색에는 system_admin 권한이 필요합니다.'
          : '관리자 계정을 검색하지 못했습니다.',
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
      message.success('Service 역할을 부여했습니다.');
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
        message.warning('선택한 Service가 변경되었습니다. 현재 Service에서 다시 회수하세요.');
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
        title: '사용자',
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
        title: '이메일',
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
        title: '상태',
        dataIndex: 'status',
        width: 112,
        className: 'admin-nowrap-cell',
        render: (_, row) => <StatusTag status={row.status} />,
      },
      {
        title: '역할',
        dataIndex: 'role',
        width: 160,
        className: 'admin-nowrap-cell',
        render: (_, row) => <Tag>{row.role}</Tag>,
      },
      {
        title: '부여자',
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
        title: '부여 시각',
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
        title: '작업',
        width: 112,
        className: 'admin-nowrap-cell',
        render: (_, row) => (
          <ConfirmActionButton
            danger
            type="link"
            size="small"
            title="Service 역할을 회수할까요?"
            okText="회수"
            content={`${row.email}에서 ${row.role} 역할을 회수합니다.`}
            disabled={!canManage}
            onConfirm={() => handleRevoke(row)}
          >
            회수
          </ConfirmActionButton>
        ),
      },
    ],
    [canManage, handleRevoke],
  );

  return (
    <Card title="Service 멤버십">
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {!canManage ? (
          <Alert
            type="info"
            showIcon
            message="멤버십 관리는 system_admin 권한이 필요합니다"
            description="선택한 Service의 멤버십을 조회할 수 있지만 역할 부여와 회수는 사용할 수 없습니다."
          />
        ) : null}
        {membershipError ? <Alert type="warning" showIcon message={membershipError} /> : null}
        <Space wrap align="end" size={12}>
          <div style={{ display: 'grid', gap: 4 }}>
            <Typography.Text>사용자</Typography.Text>
            <Select<string, UserSelectOption>
              showSearch
              allowClear
              disabled={!canManage}
              loading={searchingUsers}
              filterOption={false}
              placeholder="관리자 계정 검색"
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
            <Typography.Text>역할</Typography.Text>
            <Select
              allowClear
              disabled={!canManage}
              placeholder="역할 선택"
              value={selectedRole}
              options={serviceRoleOptions}
              style={{ width: 220 }}
              onChange={setSelectedRole}
            />
          </div>
          <ConfirmActionButton
            type="primary"
            title="Service 역할을 부여할까요?"
            okText="역할 부여"
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
            역할 부여
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
          scroll={{ x: 760 }}
          tableLayout="fixed"
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="멤버가 없습니다."
              />
            ),
          }}
        />
      </Space>
    </Card>
  );
}
