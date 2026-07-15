import { useEffect, useMemo, useRef, useState } from 'react';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { history, useLocation, useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { AdminShell } from '@/components/AdminShell';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import {
  approveAdminAccessRequest,
  grantServiceRole,
  listAdminAccessRequests,
  listPermissionAdminUsers,
  listPermissionAuditLogs,
  listPermissionRiskFindings,
  listPermissionServiceRoles,
  patchManagedAdminUser,
  rejectAdminAccessRequest,
  revokeServiceRole,
  searchAdminUsers,
  transferSystemAdmin,
} from '@/services/adminServices';
import {
  buildSystemAdminTransferRequest,
  canAccessPermissionManagement,
  countActiveLoginEligibleSystemAdmins,
  filterSystemAdminRows,
  isLastActiveSystemAdminProtected,
  permissionAdminUserRowKey,
  permissionAuditLogRowKey,
  permissionRoleLabel,
  permissionServiceRoleOptions,
  permissionServiceRoleRowKey,
  permissionTabs,
  riskFindingRowKey,
  riskSeverityColor,
  summarizeRiskEvidence,
  toPermissionAdminGlobalRolesPatchRequest,
  toPermissionAdminStatusPatchRequest,
  toPermissionAdminUsersQueryParams,
  toPermissionAuditLogsQueryParams,
  toPermissionServiceRoleGrantRequest,
  toPermissionServiceRolesQueryParams,
  type PermissionManagementTabKey,
} from './permissionManagement';

type UserSelectOption = {
  label: string;
  value: string;
  user: API.AdminUserLookup;
};

const statusValueEnum = {
  active: { text: 'active' },
  disabled: { text: 'disabled' },
} as const;

const globalRoleValueEnum = {
  system_admin: { text: 'system_admin' },
} as const;

const organizationLinkValueEnum = {
  linked: { text: 'linked' },
  unlinked: { text: 'unlinked' },
} as const;

const useYnValueEnum = {
  Y: { text: 'Y' },
  N: { text: 'N' },
} as const;

const serviceRoleValueEnum = {
  service_owner: { text: 'service_owner' },
  service_developer: { text: 'service_developer' },
  service_operator: { text: 'service_operator' },
  auditor: { text: 'auditor' },
} as const;

const auditEventGroupValueEnum = {
  all: { text: 'all' },
  admin_user: { text: 'admin_user' },
  service_membership: { text: 'service_membership' },
} as const;

const statusTag = (status: API.ManagedAdminUserStatus | string) => (
  <Tag color={status === 'active' ? 'green' : 'default'}>{status}</Tag>
);

const useYnTag = (value?: API.UseYn) =>
  value ? <Tag color={value === 'Y' ? 'green' : 'default'}>{value}</Tag> : '-';

const roleTags = (roles: readonly string[]) =>
  roles.length ? (
    <Space size={4} wrap>
      {roles.map((role) => (
        <Tag key={role} color={role === 'system_admin' ? 'blue' : 'default'}>
          {permissionRoleLabel(role)}
        </Tag>
      ))}
    </Space>
  ) : (
    <Typography.Text type="secondary">없음</Typography.Text>
  );

const toUserOption = (user: API.AdminUserLookup): UserSelectOption => ({
  label: `${user.email} / ${user.display_name} / ${user.status}`,
  value: user.user_id,
  user,
});

export default function PermissionManagementPage() {
  const location = useLocation();
  const { session, restoreSession } = useModel('adminSession');
  const [rejectRequestForm] = Form.useForm<{ decision_reason: string }>();
  const adminActionRef = useRef<ActionType>();
  const accessRequestActionRef = useRef<ActionType>();
  const globalRoleActionRef = useRef<ActionType>();
  const serviceRoleActionRef = useRef<ActionType>();
  const auditActionRef = useRef<ActionType>();
  const riskActionRef = useRef<ActionType>();
  const [activeTab, setActiveTab] =
    useState<PermissionManagementTabKey>('admin-users');
  const [activeSystemAdminCount, setActiveSystemAdminCount] = useState<number>();
  const [mutatingAdminUserId, setMutatingAdminUserId] = useState<string>();
  const [mutatingAccessRequestId, setMutatingAccessRequestId] = useState<string>();
  const [grantServiceId, setGrantServiceId] = useState('');
  const [grantUserId, setGrantUserId] = useState<string>();
  const [grantRole, setGrantRole] = useState<API.ServiceRole>();
  const [userOptions, setUserOptions] = useState<UserSelectOption[]>([]);
  const [searchingUsers, setSearchingUsers] = useState(false);
  const [grantingServiceRole, setGrantingServiceRole] = useState(false);
  const canManage = canAccessPermissionManagement(session.globalRoles);

  const focusedAdminUserId = useMemo(
    () => new URLSearchParams(location.search).get('admin_user_id')?.trim() || undefined,
    [location.search],
  );

  useEffect(() => {
    if (!grantServiceId && session.serviceId) {
      setGrantServiceId(session.serviceId);
    }
  }, [grantServiceId, session.serviceId]);

  const reloadAdminRelatedTables = () => {
    adminActionRef.current?.reload();
    accessRequestActionRef.current?.reload();
    globalRoleActionRef.current?.reload();
    auditActionRef.current?.reload();
    riskActionRef.current?.reload();
  };

  const reloadServiceRelatedTables = () => {
    serviceRoleActionRef.current?.reload();
    auditActionRef.current?.reload();
    riskActionRef.current?.reload();
  };

  const handleAdminStatusChange = async (
    row: API.PermissionAdminUserSummary,
    status: API.ManagedAdminUserStatus,
  ) => {
    setMutatingAdminUserId(row.user_id);
    try {
      await patchManagedAdminUser(row.user_id, toPermissionAdminStatusPatchRequest(status));
      if (row.user_id === session.user?.user_id) {
        await restoreSession();
      }
      reloadAdminRelatedTables();
    } finally {
      setMutatingAdminUserId(undefined);
    }
  };

  const handleApplicationAdminRoleChange = async (
    row: API.PermissionAdminUserSummary,
    grant: boolean,
  ) => {
    setMutatingAdminUserId(row.user_id);
    try {
      await patchManagedAdminUser(
        row.user_id,
        toPermissionAdminGlobalRolesPatchRequest(row, grant),
      );
      if (row.user_id === session.user?.user_id) {
        await restoreSession();
      }
      reloadAdminRelatedTables();
    } finally {
      setMutatingAdminUserId(undefined);
    }
  };

  const handleSystemAdminTransfer = async (
    row: API.PermissionAdminUserSummary,
    reason: string,
  ) => {
    if (!session.user) return;

    setMutatingAdminUserId(row.user_id);
    try {
      await transferSystemAdmin(
        buildSystemAdminTransferRequest(session.user.user_id, row.user_id, reason),
      );
      await restoreSession();
      reloadAdminRelatedTables();
    } finally {
      setMutatingAdminUserId(undefined);
    }
  };

  const handleApproveAccessRequest = async (applicant: API.AdminAccessRequest) => {
    setMutatingAccessRequestId(applicant.request_id);
    try {
      await approveAdminAccessRequest(applicant.request_id, {
        decision_reason: `Approved for ${applicant.email}`,
      });
      reloadAdminRelatedTables();
    } finally {
      setMutatingAccessRequestId(undefined);
    }
  };

  const openRejectAccessRequestModal = (applicant: API.AdminAccessRequest) => {
    rejectRequestForm.resetFields();

    Modal.confirm({
      title: '접근 신청을 반려하시겠습니까?',
      okText: '반려',
      okButtonProps: { danger: true },
      cancelText: '취소',
      content: (
        <Form form={rejectRequestForm} layout="vertical" requiredMark={false}>
          <Typography.Paragraph style={{ marginBottom: 12 }}>
            {applicant.name} ({applicant.email}) 신청을 반려합니다.
          </Typography.Paragraph>
          <Form.Item
            name="decision_reason"
            label="반려 사유"
            rules={[
              { required: true, whitespace: true, message: '반려 사유를 입력하세요.' },
            ]}
          >
            <Input.TextArea rows={4} placeholder="반려 사유를 입력하세요." />
          </Form.Item>
        </Form>
      ),
      async onOk() {
        const values = await rejectRequestForm.validateFields();
        setMutatingAccessRequestId(applicant.request_id);
        try {
          await rejectAdminAccessRequest(applicant.request_id, {
            decision_reason: values.decision_reason.trim(),
          });
          reloadAdminRelatedTables();
          message.success('처리되었습니다.');
        } finally {
          setMutatingAccessRequestId(undefined);
        }
      },
    });
  };

  const handleUserSearch = async (query: string) => {
    setSearchingUsers(true);
    try {
      const users = await searchAdminUsers({ query, limit: 25 });
      setUserOptions(users.map(toUserOption));
    } catch {
      setUserOptions([]);
      message.error('Failed to search admin users.');
    } finally {
      setSearchingUsers(false);
    }
  };

  const handleGrantServiceRole = async () => {
    const grantRequest = toPermissionServiceRoleGrantRequest(
      grantServiceId,
      grantUserId ?? '',
      grantRole ?? '',
    );
    setGrantingServiceRole(true);
    try {
      await grantServiceRole(
        grantRequest.serviceId,
        grantRequest.userId,
        grantRequest.payload,
      );
      setGrantUserId(undefined);
      setGrantRole(undefined);
      if (grantRequest.userId === session.user?.user_id) {
        await restoreSession();
      }
      reloadServiceRelatedTables();
    } finally {
      setGrantingServiceRole(false);
    }
  };

  const handleRevokeServiceRole = async (row: API.PermissionServiceRoleSummary) => {
    await revokeServiceRole(row.service_id, row.user.user_id, row.role);
    if (row.user.user_id === session.user?.user_id) {
      await restoreSession();
    }
    reloadServiceRelatedTables();
  };

  const adminUserColumns: ProColumns<API.PermissionAdminUserSummary>[] = [
    { title: 'Search', dataIndex: 'keyword', hideInTable: true },
    {
      title: 'Status',
      dataIndex: 'status',
      valueType: 'select',
      valueEnum: statusValueEnum,
      render: (_, row) => statusTag(row.status),
      width: 104,
    },
    {
      title: 'Global role',
      dataIndex: 'global_role',
      valueType: 'select',
      valueEnum: globalRoleValueEnum,
      hideInTable: true,
    },
    {
      title: 'Org link',
      dataIndex: 'organization_link',
      valueType: 'select',
      valueEnum: organizationLinkValueEnum,
      hideInTable: true,
    },
    {
      title: 'Org use',
      dataIndex: 'organization_use_yn',
      valueType: 'select',
      valueEnum: useYnValueEnum,
      hideInTable: true,
    },
    {
      title: 'Admin user',
      dataIndex: 'user_id',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text code copyable>
            {row.user_id}
          </Typography.Text>
          <Typography.Text type="secondary">{row.email}</Typography.Text>
          <Typography.Text>{row.display_name}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Organization user',
      search: false,
      render: (_, row) =>
        row.organization_user ? (
          <Space direction="vertical" size={0}>
            <Typography.Text code>{row.organization_user.user_number}</Typography.Text>
            <Typography.Text>{row.organization_user.name}</Typography.Text>
          </Space>
        ) : (
          <Typography.Text type="secondary">unlinked</Typography.Text>
        ),
    },
    {
      title: 'Department',
      search: false,
      render: (_, row) => row.organization_user?.department?.name ?? '-',
    },
    {
      title: 'Org use',
      search: false,
      width: 88,
      render: (_, row) => useYnTag(row.organization_user?.use_yn),
    },
    {
      title: 'Global roles',
      dataIndex: 'global_roles',
      search: false,
      render: (_, row) => roleTags(row.global_roles),
    },
    {
      title: 'Service roles',
      search: false,
      width: 112,
      render: (_, row) => <Tag>{row.service_roles.length}</Tag>,
    },
    {
      title: 'Last login',
      dataIndex: 'last_login_at',
      valueType: 'dateTime',
      search: false,
      width: 168,
    },
    {
      title: '',
      valueType: 'option',
      width: 240,
      render: (_, row) => {
        const protectedLastAdmin = isLastActiveSystemAdminProtected(row);
        const inactiveOrgUser = row.organization_user?.use_yn === 'N';
        const hasSystemAdmin = row.global_roles.includes('system_admin');
        const hasApplicationAdmin = row.global_roles.includes('application_admin');
        const mutating = mutatingAdminUserId === row.user_id;

        return [
          <ConfirmActionButton
            key="activate"
            type="link"
            size="small"
            title="Activate Admin account?"
            okText="활성화"
            content={`${row.email} Admin 계정을 활성화합니다.`}
            disabled={mutating || inactiveOrgUser || row.status === 'active'}
            onConfirm={() => handleAdminStatusChange(row, 'active')}
          >
            활성화
          </ConfirmActionButton>,
          <ConfirmActionButton
            key="disable"
            danger
            type="link"
            size="small"
            title="Disable Admin account?"
            okText="비활성화"
            content={`${row.email} Admin 계정을 비활성화합니다.`}
            disabled={mutating || row.status === 'disabled' || protectedLastAdmin}
            onConfirm={() => handleAdminStatusChange(row, 'disabled')}
          >
            비활성화
          </ConfirmActionButton>,
          <ConfirmActionButton
            key="grant-application-admin"
            type="link"
            size="small"
            title="Grant application_admin?"
            okText="application_admin 부여"
            content={`${row.email} 계정에 application_admin 전역 권한을 부여합니다.`}
            disabled={mutating || hasApplicationAdmin}
            onConfirm={() => handleApplicationAdminRoleChange(row, true)}
          >
            application_admin 부여
          </ConfirmActionButton>,
          <ConfirmActionButton
            key="revoke-application-admin"
            danger
            type="link"
            size="small"
            title="Revoke application_admin?"
            okText="application_admin 해제"
            content={`${row.email} 계정의 application_admin 전역 권한을 해제합니다.`}
            disabled={mutating || !hasApplicationAdmin || hasSystemAdmin}
            onConfirm={() => handleApplicationAdminRoleChange(row, false)}
          >
            application_admin 해제
          </ConfirmActionButton>,
          <ConfirmActionButton
            key="transfer-system-admin"
            danger
            type="link"
            size="small"
            title="Transfer system_admin?"
            okText="system_admin 이관"
            content={`${row.display_name} (${row.email}) 계정으로 system_admin 소유권을 이관합니다.`}
            disabled={
              mutating ||
              !session.user ||
              row.user_id === session.user.user_id ||
              hasSystemAdmin ||
              !hasApplicationAdmin ||
              row.status !== 'active' ||
              inactiveOrgUser
            }
            onConfirm={() =>
              handleSystemAdminTransfer(
                row,
                `Transfer system_admin ownership to ${row.user_id} from Permission Management.`,
              )
            }
          >
            system_admin 이관
          </ConfirmActionButton>,
        ];
      },
    },
  ];

  const globalRoleColumns: ProColumns<API.PermissionAdminUserSummary>[] = [
    {
      title: 'Admin user',
      dataIndex: 'user_id',
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text code copyable>
            {row.user_id}
          </Typography.Text>
          <Typography.Text type="secondary">{row.email}</Typography.Text>
          <Typography.Text>{row.display_name}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 104,
      render: (_, row) => statusTag(row.status),
    },
    {
      title: 'Organization use',
      width: 136,
      render: (_, row) => useYnTag(row.organization_user?.use_yn),
    },
    {
      title: 'Department',
      render: (_, row) => row.organization_user?.department?.name ?? '-',
    },
    {
      title: 'Last login',
      dataIndex: 'last_login_at',
      valueType: 'dateTime',
      width: 168,
    },
    {
      title: 'Protection',
      width: 132,
      render: (_, row) =>
        isLastActiveSystemAdminProtected(row) ? (
          <Tag color="orange">last active</Tag>
        ) : (
          <Tag color="default">normal</Tag>
        ),
    },
  ];

  const accessRequestColumns: ProColumns<API.AdminAccessRequest>[] = [
    {
      title: 'Requested',
      dataIndex: 'requested_at',
      valueType: 'dateTime',
      width: 168,
    },
    {
      title: 'User #',
      dataIndex: 'user_number',
      search: false,
      render: (_, applicant) => <Typography.Text code>{applicant.user_number}</Typography.Text>,
      width: 120,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      search: false,
      width: 120,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      search: false,
      ellipsis: true,
    },
    {
      title: 'Department',
      search: false,
      render: (_, applicant) => applicant.department?.name ?? applicant.department_id,
    },
    {
      title: 'Access reason',
      dataIndex: 'access_reason',
      search: false,
      ellipsis: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 112,
      render: (_, applicant) => (
        <Tag color={applicant.status === 'pending' ? 'orange' : 'default'}>
          {applicant.status}
        </Tag>
      ),
    },
    {
      title: 'Decided by',
      dataIndex: 'decided_by',
      search: false,
      render: (_, applicant) => applicant.decided_by ?? '-',
    },
    {
      title: 'Decision reason',
      dataIndex: 'decision_reason',
      search: false,
      ellipsis: true,
      render: (_, applicant) => applicant.decision_reason ?? '-',
    },
    {
      title: '',
      valueType: 'option',
      width: 120,
      render: (_, applicant) => {
        const mutating = mutatingAccessRequestId === applicant.request_id;
        const pending = applicant.status === 'pending';

        return [
          <ConfirmActionButton
            key="approve"
            type="link"
            size="small"
            title="접근 신청을 승인하시겠습니까?"
            okText="승인"
            content={
              <Space direction="vertical" size={4}>
                <Typography.Text>{applicant.name}</Typography.Text>
                <Typography.Text type="secondary">{applicant.email}</Typography.Text>
                <Typography.Text>{applicant.access_reason}</Typography.Text>
              </Space>
            }
            disabled={mutating || !pending}
            onConfirm={() => handleApproveAccessRequest(applicant)}
          >
            승인
          </ConfirmActionButton>,
          <Button
            key="reject"
            danger
            type="link"
            size="small"
            disabled={mutating || !pending}
            onClick={() => openRejectAccessRequestModal(applicant)}
          >
            반려
          </Button>,
        ];
      },
    },
  ];

  const serviceRoleColumns: ProColumns<API.PermissionServiceRoleSummary>[] = [
    { title: 'Service ID', dataIndex: 'service_id', hideInTable: true },
    { title: 'Search user', dataIndex: 'keyword', hideInTable: true },
    {
      title: 'Role',
      dataIndex: 'role',
      valueType: 'select',
      valueEnum: serviceRoleValueEnum,
      render: (_, row) => <Tag>{row.role}</Tag>,
      width: 144,
    },
    {
      title: 'Service',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text code>{row.service_id}</Typography.Text>
          <Typography.Text type="secondary">{row.service_display_name}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'User',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>{row.user.display_name}</Typography.Text>
          <Typography.Text type="secondary">{row.user.email}</Typography.Text>
          <Typography.Text code>{row.user.user_id}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      search: false,
      width: 104,
      render: (_, row) => statusTag(row.user.status),
    },
    {
      title: 'Organization',
      search: false,
      render: (_, row) =>
        row.organization_user ? (
          <Space direction="vertical" size={0}>
            <Typography.Text code>{row.organization_user.user_number}</Typography.Text>
            <Typography.Text>{row.organization_user.name}</Typography.Text>
            <Typography.Text type="secondary">
              {row.organization_user.department_name ?? '-'}
            </Typography.Text>
          </Space>
        ) : (
          <Typography.Text type="secondary">unlinked</Typography.Text>
        ),
    },
    {
      title: 'Assigned',
      search: false,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>{row.assigned_by}</Typography.Text>
          <Typography.Text type="secondary">{row.assigned_at}</Typography.Text>
        </Space>
      ),
    },
    {
      title: '',
      valueType: 'option',
      width: 88,
      render: (_, row) => [
        <ConfirmActionButton
          key="revoke"
          danger
          type="link"
          size="small"
          title="Revoke Service role?"
          okText="Revoke"
          content={`${row.service_id}에서 ${row.user.email} 계정의 ${row.role} 권한을 해제합니다.`}
          onConfirm={() => handleRevokeServiceRole(row)}
        >
          해제
        </ConfirmActionButton>,
      ],
    },
  ];

  const auditColumns: ProColumns<API.AuditLog>[] = [
    {
      title: 'Event group',
      dataIndex: 'event_group',
      valueType: 'select',
      valueEnum: auditEventGroupValueEnum,
      hideInTable: true,
    },
    {
      title: 'Event type',
      dataIndex: 'event_type',
      render: (_, row) => <Tag>{row.event_type}</Tag>,
    },
    {
      title: 'Actor',
      dataIndex: 'actor_id',
      render: (_, row) => <Typography.Text code>{row.actor_id}</Typography.Text>,
    },
    {
      title: 'Target',
      dataIndex: 'target_id',
      render: (_, row) => `${row.target_type} / ${row.target_id}`,
    },
    {
      title: 'Service ID',
      dataIndex: 'service_id',
      render: (_, row) =>
        row.service_id ? <Typography.Text code>{row.service_id}</Typography.Text> : '-',
    },
    {
      title: 'Trace',
      dataIndex: 'trace_id',
      ellipsis: true,
      render: (_, row) => row.trace_id ?? '-',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      search: false,
      width: 168,
    },
  ];

  const riskColumns: ProColumns<API.PermissionRiskFinding>[] = [
    {
      title: 'Severity',
      dataIndex: 'severity',
      width: 112,
      render: (_, row) => <Tag color={riskSeverityColor(row.severity)}>{row.severity}</Tag>,
    },
    { title: 'Category', dataIndex: 'category', width: 160 },
    {
      title: 'Finding',
      dataIndex: 'title',
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.title}</Typography.Text>
          <Typography.Text type="secondary">{row.recommended_action}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Target',
      width: 220,
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          {row.admin_user_id ? (
            <Typography.Text code>admin {row.admin_user_id}</Typography.Text>
          ) : null}
          {row.service_id ? (
            <Typography.Text code>service {row.service_id}</Typography.Text>
          ) : null}
          {!row.admin_user_id && !row.service_id ? '-' : null}
        </Space>
      ),
    },
    {
      title: 'Evidence',
      dataIndex: 'evidence',
      render: (_, row) => {
        const evidence = summarizeRiskEvidence(row.evidence);
        return evidence.length ? (
          <Space size={4} wrap>
            {evidence.map((item) => (
              <Tag key={item}>{item}</Tag>
            ))}
          </Space>
        ) : (
          '-'
        );
      },
    },
  ];

  return (
    <AdminShell title="권한관리">
      {canManage ? (
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {focusedAdminUserId ? (
            <Alert
              type="info"
              showIcon
              message="Admin 계정 필터가 적용되어 있습니다."
              description={<Typography.Text code>{focusedAdminUserId}</Typography.Text>}
              action={
                <Button size="small" onClick={() => history.push('/permission-management')}>
                  전체 보기
                </Button>
              }
            />
          ) : null}
          <Tabs
            activeKey={activeTab}
            onChange={(key) => setActiveTab(key as PermissionManagementTabKey)}
            items={permissionTabs.map((tab) => {
              if (tab.key === 'admin-users') {
                return {
                  key: tab.key,
                  label: tab.label,
                  children: (
                    <ProTable<API.PermissionAdminUserSummary>
                      rowKey={permissionAdminUserRowKey}
                      actionRef={adminActionRef}
                      columns={adminUserColumns}
                      request={async (params) => {
                        const rows = await listPermissionAdminUsers(
                          toPermissionAdminUsersQueryParams(params, focusedAdminUserId),
                        );
                        return { data: rows, total: rows.length, success: true };
                      }}
                      pagination={false}
                      search={{ labelWidth: 104 }}
                      options={{ density: true, fullScreen: false, reload: true, setting: true }}
                    />
                  ),
                };
              }

              if (tab.key === 'access-requests') {
                return {
                  key: tab.key,
                  label: tab.label,
                  children: (
                    <ProTable<API.AdminAccessRequest>
                      rowKey="request_id"
                      actionRef={accessRequestActionRef}
                      columns={accessRequestColumns}
                      request={async () => {
                        const rows = await listAdminAccessRequests({ limit: 100 });
                        return { data: rows, total: rows.length, success: true };
                      }}
                      pagination={false}
                      search={false}
                      options={{ density: true, fullScreen: false, reload: true, setting: true }}
                    />
                  ),
                };
              }

              if (tab.key === 'global-roles') {
                return {
                  key: tab.key,
                  label: tab.label,
                  children: (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      {activeSystemAdminCount === 1 ? (
                        <Alert
                          type="warning"
                          showIcon
                          message="active login-eligible system_admin이 1명뿐입니다."
                          description="마지막 system_admin 보호 상태인 계정은 비활성화와 권한 해제가 비활성화됩니다."
                        />
                      ) : null}
                      <ProTable<API.PermissionAdminUserSummary>
                        rowKey={permissionAdminUserRowKey}
                        actionRef={globalRoleActionRef}
                        columns={globalRoleColumns}
                        request={async () => {
                          const rows = await listPermissionAdminUsers({
                            global_role: 'system_admin',
                            limit: 100,
                          });
                          const systemAdminRows = filterSystemAdminRows(rows);
                          setActiveSystemAdminCount(
                            countActiveLoginEligibleSystemAdmins(systemAdminRows),
                          );
                          return {
                            data: systemAdminRows,
                            total: systemAdminRows.length,
                            success: true,
                          };
                        }}
                        pagination={false}
                        search={false}
                        options={{ density: true, fullScreen: false, reload: true, setting: true }}
                      />
                    </Space>
                  ),
                };
              }

              if (tab.key === 'service-roles') {
                return {
                  key: tab.key,
                  label: tab.label,
                  children: (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      <Card title="Service role grant">
                        <Space wrap align="end" size={12}>
                          <Space direction="vertical" size={4}>
                            <Typography.Text>Service ID</Typography.Text>
                            <Input
                              placeholder="service-id"
                              value={grantServiceId}
                              onChange={(event) => setGrantServiceId(event.target.value)}
                              style={{ width: 240 }}
                            />
                          </Space>
                          <Space direction="vertical" size={4}>
                            <Typography.Text>User</Typography.Text>
                            <Select<string, UserSelectOption>
                              showSearch
                              allowClear
                              loading={searchingUsers}
                              filterOption={false}
                              placeholder="Search admin users"
                              value={grantUserId}
                              options={userOptions}
                              style={{ width: 340 }}
                              onSearch={handleUserSearch}
                              onChange={setGrantUserId}
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
                            <Select<API.ServiceRole>
                              allowClear
                              placeholder="Select role"
                              value={grantRole}
                              options={permissionServiceRoleOptions}
                              style={{ width: 220 }}
                              onChange={setGrantRole}
                            />
                          </Space>
                          <ConfirmActionButton
                            type="primary"
                            title="Grant Service role?"
                            okText="Grant role"
                            content={`${grantServiceId.trim()}에서 선택한 Admin 계정에 ${grantRole ?? '-'} 권한을 부여합니다.`}
                            disabled={
                              grantingServiceRole ||
                              !grantServiceId.trim() ||
                              !grantUserId ||
                              !grantRole
                            }
                            onConfirm={handleGrantServiceRole}
                          >
                            Grant role
                          </ConfirmActionButton>
                        </Space>
                      </Card>
                      <ProTable<API.PermissionServiceRoleSummary>
                        rowKey={permissionServiceRoleRowKey}
                        actionRef={serviceRoleActionRef}
                        columns={serviceRoleColumns}
                        request={async (params) => {
                          const rows = await listPermissionServiceRoles(
                            toPermissionServiceRolesQueryParams(params),
                          );
                          return { data: rows, total: rows.length, success: true };
                        }}
                        pagination={false}
                        search={{ labelWidth: 104 }}
                        options={{ density: true, fullScreen: false, reload: true, setting: true }}
                      />
                    </Space>
                  ),
                };
              }

              if (tab.key === 'audit-logs') {
                return {
                  key: tab.key,
                  label: tab.label,
                  children: (
                    <ProTable<API.AuditLog>
                      rowKey={permissionAuditLogRowKey}
                      actionRef={auditActionRef}
                      columns={auditColumns}
                      request={async (params) => {
                        const rows = await listPermissionAuditLogs(
                          toPermissionAuditLogsQueryParams(params),
                        );
                        return { data: rows, total: rows.length, success: true };
                      }}
                      pagination={false}
                      search={{ labelWidth: 104 }}
                      options={{ density: true, fullScreen: false, reload: true, setting: true }}
                    />
                  ),
                };
              }

              return {
                key: tab.key,
                label: tab.label,
                children: (
                  <ProTable<API.PermissionRiskFinding>
                    rowKey={riskFindingRowKey}
                    actionRef={riskActionRef}
                    columns={riskColumns}
                    request={async () => {
                      const rows = await listPermissionRiskFindings();
                      return { data: rows, total: rows.length, success: true };
                    }}
                    pagination={false}
                    search={false}
                    options={{ density: true, fullScreen: false, reload: true, setting: true }}
                  />
                ),
              };
            })}
          />
        </Space>
      ) : (
        <Alert
          type="warning"
          showIcon
          message="권한관리 접근에는 system_admin 권한이 필요합니다."
          description="이 페이지는 서버에서 파생한 현재 세션의 globalRoles에 system_admin이 있을 때만 사용할 수 있습니다."
        />
      )}
    </AdminShell>
  );
}
