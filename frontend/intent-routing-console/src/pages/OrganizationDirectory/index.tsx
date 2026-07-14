import { useCallback, useEffect, useRef, useState } from 'react';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { history, useModel } from '@umijs/max';
import {
  Alert,
  Button,
  Descriptions,
  Flex,
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
import { AdminSessionRequired } from '@/components/AdminSessionRequired';
import { ConfirmActionButton } from '@/components/ConfirmActionButton';
import {
  createManagedAdminUser,
  createDepartment,
  createOrganizationUser,
  listManagedAdminUsers,
  listDepartments,
  listOrganizationUsers,
  patchManagedAdminUser,
  patchDepartment,
  patchOrganizationUser,
} from '@/services/adminServices';
import {
  hasSystemAdminRole,
  canAccessOrganizationDirectory,
  formatDepartmentNumber,
  formatOrganizationUserNumber,
  toAdminUserCreateRequest,
  toAdminUserStatusPatchRequest,
  permissionManagementAdminUserUrl,
  toDepartmentOption,
  toDepartmentOptionSearchParams,
  toSystemAdminRolesPatchRequest,
  toDepartmentCreateRequest,
  toDepartmentUseYnPatchRequest,
  toOrganizationUserCreateRequest,
  toOrganizationUserUseYnPatchRequest,
  type AdminAccessCreateFormValues,
  type DepartmentFormValues,
  type DepartmentOption,
  type OrganizationUserFormValues,
} from './directoryForms';

type DepartmentFormMode = 'create' | 'edit';
type UserFormMode = 'create' | 'edit';

const useYnValueEnum = {
  Y: { text: 'Y' },
  N: { text: 'N' },
} as const;

const UseYnTag = ({ value }: { value: API.UseYn }) => (
  <Tag color={value === 'Y' ? 'green' : 'default'}>{value}</Tag>
);

export default function OrganizationDirectoryPage() {
  const { session, restoreSession } = useModel('adminSession');
  const [departmentForm] = Form.useForm<DepartmentFormValues>();
  const [userForm] = Form.useForm<OrganizationUserFormValues>();
  const [departmentModalOpen, setDepartmentModalOpen] = useState(false);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [departmentFormMode, setDepartmentFormMode] = useState<DepartmentFormMode>('create');
  const [userFormMode, setUserFormMode] = useState<UserFormMode>('create');
  const [editingDepartment, setEditingDepartment] = useState<API.Department>();
  const [editingUser, setEditingUser] = useState<API.OrganizationUser>();
  const [departmentSaving, setDepartmentSaving] = useState(false);
  const [userSaving, setUserSaving] = useState(false);
  const [adminAccessSaving, setAdminAccessSaving] = useState(false);
  const [adminAccessLoading, setAdminAccessLoading] = useState(false);
  const [managedAdminUser, setManagedAdminUser] = useState<API.ManagedAdminUser>();
  const [adminAccessDraft, setAdminAccessDraft] = useState<AdminAccessCreateFormValues>({
    email: '',
    display_name: '',
  });
  const [departmentFilterOptions, setDepartmentFilterOptions] = useState<DepartmentOption[]>([]);
  const [departmentSelectOptions, setDepartmentSelectOptions] = useState<DepartmentOption[]>([]);
  const [loadingDepartmentFilterOptions, setLoadingDepartmentFilterOptions] = useState(false);
  const [loadingDepartmentSelectOptions, setLoadingDepartmentSelectOptions] = useState(false);
  const departmentActionRef = useRef<ActionType>();
  const userActionRef = useRef<ActionType>();
  const departmentFilterRequestSeqRef = useRef(0);
  const departmentSelectRequestSeqRef = useRef(0);
  const adminAccessRequestSeqRef = useRef(0);
  const ready = Boolean(session.authenticated && session.user);
  const canManage = canAccessOrganizationDirectory(session.globalRoles);

  const clearDepartmentOptions = useCallback(() => {
    departmentFilterRequestSeqRef.current += 1;
    departmentSelectRequestSeqRef.current += 1;
    setDepartmentFilterOptions([]);
    setDepartmentSelectOptions([]);
    setLoadingDepartmentFilterOptions(false);
    setLoadingDepartmentSelectOptions(false);
  }, []);

  const loadDepartmentOptions = useCallback(
    async (query: string | undefined, target: 'filter' | 'form') => {
      const requestSeqRef =
        target === 'filter' ? departmentFilterRequestSeqRef : departmentSelectRequestSeqRef;
      const setOptions =
        target === 'filter' ? setDepartmentFilterOptions : setDepartmentSelectOptions;
      const setLoading =
        target === 'filter' ? setLoadingDepartmentFilterOptions : setLoadingDepartmentSelectOptions;
      const requestSeq = (requestSeqRef.current += 1);

      setLoading(true);
      try {
        const rows = await listDepartments(toDepartmentOptionSearchParams(query));
        if (requestSeq !== requestSeqRef.current) return;
        setOptions(rows.map(toDepartmentOption));
      } catch {
        if (requestSeq !== requestSeqRef.current) return;
        setOptions([]);
        message.error('Failed to load department options.');
      } finally {
        if (requestSeq === requestSeqRef.current) {
          setLoading(false);
        }
      }
    },
    [],
  );

  const primeDepartmentOptions = useCallback(async () => {
    const filterRequestSeq = (departmentFilterRequestSeqRef.current += 1);
    const selectRequestSeq = (departmentSelectRequestSeqRef.current += 1);

    setLoadingDepartmentFilterOptions(true);
    setLoadingDepartmentSelectOptions(true);
    try {
      const rows = await listDepartments(toDepartmentOptionSearchParams());
      const options = rows.map(toDepartmentOption);
      if (
        filterRequestSeq !== departmentFilterRequestSeqRef.current ||
        selectRequestSeq !== departmentSelectRequestSeqRef.current
      ) {
        return;
      }
      setDepartmentFilterOptions(options);
      setDepartmentSelectOptions(options);
    } catch {
      if (
        filterRequestSeq !== departmentFilterRequestSeqRef.current ||
        selectRequestSeq !== departmentSelectRequestSeqRef.current
      ) {
        return;
      }
      setDepartmentFilterOptions([]);
      setDepartmentSelectOptions([]);
      message.error('Failed to load department options.');
    } finally {
      if (filterRequestSeq === departmentFilterRequestSeqRef.current) {
        setLoadingDepartmentFilterOptions(false);
      }
      if (selectRequestSeq === departmentSelectRequestSeqRef.current) {
        setLoadingDepartmentSelectOptions(false);
      }
    }
  }, []);

  useEffect(() => {
    if (!ready || !canManage) {
      clearDepartmentOptions();
      return;
    }
    void primeDepartmentOptions();
  }, [canManage, clearDepartmentOptions, primeDepartmentOptions, ready]);

  const reloadDepartmentViews = useCallback(() => {
    departmentActionRef.current?.reload();
    userActionRef.current?.reload();
    void primeDepartmentOptions();
  }, [primeDepartmentOptions]);

  const reloadUserTable = useCallback(() => {
    userActionRef.current?.reload();
  }, []);

  const resetAdminAccessState = useCallback(() => {
    adminAccessRequestSeqRef.current += 1;
    setManagedAdminUser(undefined);
    setAdminAccessLoading(false);
    setAdminAccessSaving(false);
    setAdminAccessDraft({ email: '', display_name: '' });
  }, []);

  const loadAdminAccess = useCallback(async (organizationUser: API.OrganizationUser) => {
    const requestSeq = (adminAccessRequestSeqRef.current += 1);
    setAdminAccessLoading(true);
    setManagedAdminUser(undefined);
    setAdminAccessDraft({ email: '', display_name: organizationUser.name });
    try {
      const rows = await listManagedAdminUsers({
        organization_user_id: organizationUser.id,
        limit: 1,
      });
      if (requestSeq !== adminAccessRequestSeqRef.current) return;
      setManagedAdminUser(rows[0]);
    } catch {
      if (requestSeq !== adminAccessRequestSeqRef.current) return;
      message.error('Failed to load Admin access.');
    } finally {
      if (requestSeq === adminAccessRequestSeqRef.current) {
        setAdminAccessLoading(false);
      }
    }
  }, []);

  const closeDepartmentModal = () => {
    setDepartmentModalOpen(false);
    setEditingDepartment(undefined);
    departmentForm.resetFields();
  };

  const closeUserModal = () => {
    setUserModalOpen(false);
    setEditingUser(undefined);
    resetAdminAccessState();
    userForm.resetFields();
  };

  const openCreateDepartmentModal = () => {
    setDepartmentFormMode('create');
    setEditingDepartment(undefined);
    departmentForm.resetFields();
    setDepartmentModalOpen(true);
  };

  const openEditDepartmentModal = (department: API.Department) => {
    setDepartmentFormMode('edit');
    setEditingDepartment(department);
    departmentForm.resetFields();
    departmentForm.setFieldsValue({
      dept_number: department.dept_number,
      name: department.name,
    });
    setDepartmentModalOpen(true);
  };

  const openCreateUserModal = () => {
    setUserFormMode('create');
    setEditingUser(undefined);
    resetAdminAccessState();
    userForm.resetFields();
    void loadDepartmentOptions(undefined, 'form');
    setUserModalOpen(true);
  };

  const openEditUserModal = (user: API.OrganizationUser) => {
    setUserFormMode('edit');
    setEditingUser(user);
    setDepartmentSelectOptions((current) =>
      current.some((option) => option.value === user.department_id)
        ? current
        : [toDepartmentOption(user.department), ...current],
    );
    userForm.resetFields();
    userForm.setFieldsValue({
      user_number: user.user_number,
      name: user.name,
      department_id: user.department_id,
    });
    void loadAdminAccess(user);
    setUserModalOpen(true);
  };

  const handleDepartmentSubmit = async (values: DepartmentFormValues) => {
    setDepartmentSaving(true);
    try {
      const payload = toDepartmentCreateRequest(values);
      if (departmentFormMode === 'create') {
        await createDepartment(payload);
        message.success('Department created.');
      } else if (editingDepartment) {
        await patchDepartment(editingDepartment.id, payload);
        message.success('Department updated.');
      }
      closeDepartmentModal();
      reloadDepartmentViews();
    } finally {
      setDepartmentSaving(false);
    }
  };

  const handleDepartmentUseYnChange = async (useYn: API.UseYn) => {
    if (!editingDepartment || editingDepartment.use_yn === useYn) return;

    setDepartmentSaving(true);
    try {
      const updatedDepartment = await patchDepartment(
        editingDepartment.id,
        toDepartmentUseYnPatchRequest(useYn),
      );
      setEditingDepartment(updatedDepartment);
      reloadDepartmentViews();
    } finally {
      setDepartmentSaving(false);
    }
  };

  const handleUserSubmit = async (values: OrganizationUserFormValues) => {
    setUserSaving(true);
    try {
      const payload = toOrganizationUserCreateRequest(values);
      if (userFormMode === 'create') {
        await createOrganizationUser(payload);
        message.success('User created.');
      } else if (editingUser) {
        await patchOrganizationUser(editingUser.id, payload);
        message.success('User updated.');
      }
      closeUserModal();
      reloadUserTable();
    } finally {
      setUserSaving(false);
    }
  };

  const handleOrganizationUserUseYnChange = async (useYn: API.UseYn) => {
    if (!editingUser || editingUser.use_yn === useYn) return;

    setUserSaving(true);
    try {
      const updatedUser = await patchOrganizationUser(
        editingUser.id,
        toOrganizationUserUseYnPatchRequest(useYn),
      );
      setEditingUser(updatedUser);
      reloadUserTable();
    } finally {
      setUserSaving(false);
    }
  };

  const handleCreateManagedAdminUser = async () => {
    if (!editingUser) return;
    if (editingUser.use_yn !== 'Y') {
      message.warning('비활성 조직 사용자에게는 active Admin 계정을 부여할 수 없습니다.');
      return;
    }
    if (!adminAccessDraft.email.trim() || !adminAccessDraft.display_name.trim()) {
      message.warning('Admin email and display name are required.');
      return;
    }

    setAdminAccessSaving(true);
    try {
      const adminUser = await createManagedAdminUser(
        toAdminUserCreateRequest(adminAccessDraft, editingUser),
      );
      setManagedAdminUser(adminUser);
      reloadUserTable();
    } finally {
      setAdminAccessSaving(false);
    }
  };

  const handleManagedAdminStatusChange = async (
    adminUser: API.ManagedAdminUser,
    statusValue: API.ManagedAdminUserStatus,
  ) => {
    if (!editingUser || adminUser.status === statusValue) return;
    if (statusValue === 'active' && editingUser.use_yn !== 'Y') {
      message.warning('비활성 조직 사용자에게는 active Admin 계정을 부여할 수 없습니다.');
      return;
    }

    setAdminAccessSaving(true);
    try {
      const updatedAdminUser = await patchManagedAdminUser(
        adminUser.user_id,
        toAdminUserStatusPatchRequest(statusValue),
      );
      setManagedAdminUser(updatedAdminUser);
      if (updatedAdminUser.user_id === session.user?.user_id) {
        void restoreSession();
      }
    } finally {
      setAdminAccessSaving(false);
    }
  };

  const handleSystemAdminRoleChange = async (
    adminUser: API.ManagedAdminUser,
    grant: boolean,
  ) => {
    setAdminAccessSaving(true);
    try {
      const updatedAdminUser = await patchManagedAdminUser(
        adminUser.user_id,
        toSystemAdminRolesPatchRequest(adminUser, grant),
      );
      setManagedAdminUser(updatedAdminUser);
      if (updatedAdminUser.user_id === session.user?.user_id) {
        void restoreSession();
      }
    } finally {
      setAdminAccessSaving(false);
    }
  };

  const renderAdminAccessSection = () => {
    if (userFormMode !== 'edit' || !editingUser) return null;

    const inactiveOrganizationUser = editingUser.use_yn === 'N';
    const isSelfLastSystemAdmin = Boolean(
      managedAdminUser &&
        managedAdminUser.user_id === session.user?.user_id &&
        managedAdminUser.is_last_active_system_admin,
    );
    const hasSystemAdmin = managedAdminUser
      ? hasSystemAdminRole(managedAdminUser)
      : false;

    return (
      <Form.Item label="Admin Access">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {adminAccessLoading ? (
            <Typography.Text type="secondary">Loading Admin access...</Typography.Text>
          ) : managedAdminUser ? (
            <>
              <Descriptions
                bordered
                column={1}
                size="small"
                items={[
                  {
                    key: 'user_id',
                    label: 'admin user_id',
                    children: <Typography.Text code>{managedAdminUser.user_id}</Typography.Text>,
                  },
                  {
                    key: 'email',
                    label: 'email',
                    children: managedAdminUser.email,
                  },
                  {
                    key: 'display_name',
                    label: 'display_name',
                    children: managedAdminUser.display_name,
                  },
                  {
                    key: 'status',
                    label: 'status',
                    children: (
                      <Tag color={managedAdminUser.status === 'active' ? 'green' : 'default'}>
                        {managedAdminUser.status}
                      </Tag>
                    ),
                  },
                  {
                    key: 'global_roles',
                    label: 'global_roles',
                    children: managedAdminUser.global_roles.length ? (
                      <Space size={4} wrap>
                        {managedAdminUser.global_roles.map((role) => (
                          <Tag key={role} color={role === 'system_admin' ? 'blue' : 'default'}>
                            {role}
                          </Tag>
                        ))}
                      </Space>
                    ) : (
                      <Typography.Text type="secondary">없음</Typography.Text>
                    ),
                  },
                ]}
              />
              <Button
                size="small"
                type="link"
                onClick={() =>
                  history.push(permissionManagementAdminUserUrl(managedAdminUser.user_id))
                }
              >
                권한관리에서 보기
              </Button>
              {inactiveOrganizationUser ? (
                <Alert
                  type="warning"
                  showIcon
                  message="비활성 조직 사용자에게는 active Admin 계정을 부여할 수 없습니다."
                />
              ) : null}
              {isSelfLastSystemAdmin ? (
                <Alert
                  type="warning"
                  showIcon
                  message="마지막 system_admin인 자신의 계정은 비활성화하거나 권한을 해제할 수 없습니다."
                />
              ) : null}
              <Flex gap={8} wrap="wrap">
                <ConfirmActionButton
                  disabled={
                    adminAccessSaving ||
                    inactiveOrganizationUser ||
                    managedAdminUser.status === 'active'
                  }
                  style={{ boxShadow: 'none' }}
                  type="primary"
                  title="Activate Admin account?"
                  okText="활성화"
                  content={`${managedAdminUser.email} Admin 계정을 활성화합니다.`}
                  onConfirm={() => handleManagedAdminStatusChange(managedAdminUser, 'active')}
                >
                  활성화
                </ConfirmActionButton>
                <ConfirmActionButton
                  danger
                  disabled={
                    adminAccessSaving ||
                    managedAdminUser.status === 'disabled' ||
                    isSelfLastSystemAdmin
                  }
                  style={{ boxShadow: 'none' }}
                  title="Disable Admin account?"
                  okText="비활성화"
                  content={`${managedAdminUser.email} Admin 계정을 비활성화합니다.`}
                  onConfirm={() => handleManagedAdminStatusChange(managedAdminUser, 'disabled')}
                >
                  비활성화
                </ConfirmActionButton>
              </Flex>
              <Flex gap={8} wrap="wrap">
                <ConfirmActionButton
                  disabled={adminAccessSaving || hasSystemAdmin}
                  style={{ boxShadow: 'none' }}
                  title="Grant system_admin?"
                  okText="system_admin 부여"
                  content={`${managedAdminUser.email} 계정에 system_admin 전역 권한을 부여합니다.`}
                  onConfirm={() => handleSystemAdminRoleChange(managedAdminUser, true)}
                >
                  system_admin 부여
                </ConfirmActionButton>
                <ConfirmActionButton
                  danger
                  disabled={adminAccessSaving || !hasSystemAdmin || isSelfLastSystemAdmin}
                  style={{ boxShadow: 'none' }}
                  title="Revoke system_admin?"
                  okText="system_admin 해제"
                  content={`${managedAdminUser.email} 계정의 system_admin 전역 권한을 해제합니다.`}
                  onConfirm={() => handleSystemAdminRoleChange(managedAdminUser, false)}
                >
                  system_admin 해제
                </ConfirmActionButton>
              </Flex>
            </>
          ) : (
            <>
              <Alert
                type={inactiveOrganizationUser ? 'warning' : 'info'}
                showIcon
                message={
                  inactiveOrganizationUser
                    ? '비활성 조직 사용자에게는 active Admin 계정을 부여할 수 없습니다.'
                    : '관리자 권한 없음'
                }
                description={
                  inactiveOrganizationUser
                    ? undefined
                    : '초기 비밀번호 발급 흐름이 없어 생성 시 disabled 상태로 시작합니다.'
                }
              />
              <Flex gap={8} wrap="wrap" align="end">
                <Input
                  disabled={adminAccessSaving || inactiveOrganizationUser}
                  placeholder="admin@example.com"
                  style={{ flex: '1 1 220px' }}
                  value={adminAccessDraft.email}
                  onChange={(event) =>
                    setAdminAccessDraft((current) => ({
                      ...current,
                      email: event.target.value,
                    }))
                  }
                />
                <Input
                  disabled={adminAccessSaving || inactiveOrganizationUser}
                  placeholder="Display name"
                  style={{ flex: '1 1 180px' }}
                  value={adminAccessDraft.display_name}
                  onChange={(event) =>
                    setAdminAccessDraft((current) => ({
                      ...current,
                      display_name: event.target.value,
                    }))
                  }
                />
                <ConfirmActionButton
                  disabled={
                    adminAccessSaving ||
                    inactiveOrganizationUser ||
                    !adminAccessDraft.email.trim() ||
                    !adminAccessDraft.display_name.trim()
                  }
                  style={{ boxShadow: 'none' }}
                  type="primary"
                  title="Create Admin account?"
                  okText="관리자 계정 생성"
                  content={`${editingUser.user_number} ${editingUser.name} 사용자와 연결된 disabled Admin 계정을 생성합니다.`}
                  onConfirm={handleCreateManagedAdminUser}
                >
                  관리자 계정 생성
                </ConfirmActionButton>
              </Flex>
            </>
          )}
        </Space>
      </Form.Item>
    );
  };

  const departmentColumns: ProColumns<API.Department>[] = [
    {
      title: 'Search',
      dataIndex: 'keyword',
      hideInTable: true,
    },
    {
      title: 'Dept_Number',
      dataIndex: 'dept_number',
      search: false,
      render: (_, row) => (
        <Typography.Text code>{formatDepartmentNumber(row.dept_number)}</Typography.Text>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      search: false,
    },
    {
      title: 'Use',
      dataIndex: 'use_yn',
      valueType: 'select',
      valueEnum: useYnValueEnum,
      render: (_, row) => <UseYnTag value={row.use_yn} />,
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '',
      valueType: 'option',
      width: 80,
      render: (_, row) => {
        if (!canManage) return [];
        return [
          <Button
            key="edit"
            type="link"
            size="small"
            onClick={() => openEditDepartmentModal(row)}
          >
            편집
          </Button>,
        ].filter(Boolean);
      },
    },
  ];

  const userColumns: ProColumns<API.OrganizationUser>[] = [
    {
      title: 'Search',
      dataIndex: 'keyword',
      hideInTable: true,
    },
    {
      title: 'Department',
      dataIndex: 'department_id',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        options: departmentFilterOptions,
        showSearch: true,
        filterOption: false,
        loading: loadingDepartmentFilterOptions,
        onSearch: (value: string) => {
          void loadDepartmentOptions(value, 'filter');
        },
      },
    },
    {
      title: 'User #',
      dataIndex: 'user_number',
      search: false,
      render: (_, row) => (
        <Typography.Text code>{formatOrganizationUserNumber(row.user_number)}</Typography.Text>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      search: false,
    },
    {
      title: 'Department',
      dataIndex: ['department', 'name'],
      search: false,
      render: (_, row) => row.department.name,
    },
    {
      title: 'Use',
      dataIndex: 'use_yn',
      valueType: 'select',
      valueEnum: useYnValueEnum,
      render: (_, row) => <UseYnTag value={row.use_yn} />,
    },
    {
      title: 'Updated',
      dataIndex: 'updated_at',
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '',
      valueType: 'option',
      width: 80,
      render: (_, row) => {
        if (!canManage) return [];
        return [
          <Button key="edit" type="link" size="small" onClick={() => openEditUserModal(row)}>
            편집
          </Button>,
        ].filter(Boolean);
      },
    },
  ];

  return (
    <AdminShell title="Users & Departments">
      {ready ? (
        !canManage ? (
          <Alert
            type="info"
            showIcon
            message="Organization directory access requires system_admin."
          />
        ) : (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Tabs
              destroyInactiveTabPane
              items={[
                {
                  key: 'departments',
                  label: 'Departments',
                  children: (
                    <ProTable<API.Department>
                      rowKey="id"
                      actionRef={departmentActionRef}
                      columns={departmentColumns}
                      request={async (params) => {
                        const rows = await listDepartments({
                          query: typeof params.keyword === 'string' ? params.keyword : undefined,
                          use_yn: params.use_yn as API.UseYn | undefined,
                          limit: 100,
                        });
                        return { data: rows, total: rows.length, success: true };
                      }}
                      pagination={false}
                      search={{ labelWidth: 88 }}
                      toolbar={{
                        title: canManage ? (
                          <Button type="primary" onClick={openCreateDepartmentModal}>
                            Department 추가
                          </Button>
                        ) : undefined,
                      }}
                      options={{ density: true, fullScreen: false, reload: true, setting: true }}
                    />
                  ),
                },
                {
                  key: 'users',
                  label: 'Users',
                  children: (
                    <ProTable<API.OrganizationUser>
                      rowKey="id"
                      actionRef={userActionRef}
                      columns={userColumns}
                      request={async (params) => {
                        const rows = await listOrganizationUsers({
                          query: typeof params.keyword === 'string' ? params.keyword : undefined,
                          department_id:
                            typeof params.department_id === 'string'
                              ? params.department_id
                              : undefined,
                          use_yn: params.use_yn as API.UseYn | undefined,
                          limit: 100,
                        });
                        return { data: rows, total: rows.length, success: true };
                      }}
                      pagination={false}
                      search={{ labelWidth: 88 }}
                      toolbar={{
                        title: canManage ? (
                          <Button type="primary" onClick={openCreateUserModal}>
                            User 추가
                          </Button>
                        ) : undefined,
                      }}
                      options={{ density: true, fullScreen: false, reload: true, setting: true }}
                    />
                  ),
                },
              ]}
            />
            <Modal
              destroyOnClose
              open={departmentModalOpen}
              title={departmentFormMode === 'create' ? 'Create Department' : 'Edit Department'}
              okText={departmentFormMode === 'create' ? 'Create' : 'Save'}
              cancelText="취소"
              confirmLoading={departmentSaving}
              onCancel={closeDepartmentModal}
              onOk={() => departmentForm.submit()}
            >
              <Form<DepartmentFormValues>
                form={departmentForm}
                layout="vertical"
                requiredMark={false}
                onFinish={handleDepartmentSubmit}
              >
                {departmentFormMode === 'edit' && editingDepartment ? (
                  <Form.Item label="ID">
                    <Input value={editingDepartment.id} disabled readOnly />
                  </Form.Item>
                ) : null}
                <Form.Item
                  name="dept_number"
                  label="Dept_Number"
                  rules={[
                    { required: true, whitespace: true, message: 'Dept_Number is required.' },
                  ]}
                >
                  <Input placeholder="0969" />
                </Form.Item>
                <Form.Item
                  name="name"
                  label="Name"
                  rules={[{ required: true, whitespace: true, message: 'Name is required.' }]}
                >
                  <Input placeholder="IT지원부" />
                </Form.Item>
                {departmentFormMode === 'edit' && editingDepartment ? (
                  <Form.Item label="Use">
                    <Space direction="vertical" size={10}>
                      <UseYnTag value={editingDepartment.use_yn} />
                      <div
                        style={{
                          display: 'grid',
                          gap: 12,
                          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
                          maxWidth: '100%',
                          width: 260,
                        }}
                      >
                        <ConfirmActionButton
                          disabled={departmentSaving || editingDepartment.use_yn === 'Y'}
                          style={{ boxShadow: 'none' }}
                          type="primary"
                          title="Activate department?"
                          okText="Activate"
                          content={`${editingDepartment.dept_number} ${editingDepartment.name} 부서를 활성화합니다.`}
                          onConfirm={() => handleDepartmentUseYnChange('Y')}
                        >
                          활성화
                        </ConfirmActionButton>
                        <ConfirmActionButton
                          danger
                          disabled={departmentSaving || editingDepartment.use_yn === 'N'}
                          style={{ boxShadow: 'none' }}
                          title="Deactivate department?"
                          okText="Deactivate"
                          content={`${editingDepartment.dept_number} ${editingDepartment.name} 부서를 비활성화합니다.`}
                          onConfirm={() => handleDepartmentUseYnChange('N')}
                        >
                          비활성화
                        </ConfirmActionButton>
                      </div>
                    </Space>
                  </Form.Item>
                ) : null}
              </Form>
            </Modal>
            <Modal
              destroyOnClose
              open={userModalOpen}
              title={userFormMode === 'create' ? 'Create User' : 'Edit User'}
              okText={userFormMode === 'create' ? 'Create' : 'Save'}
              cancelText="취소"
              confirmLoading={userSaving}
              onCancel={closeUserModal}
              onOk={() => userForm.submit()}
            >
              <Form<OrganizationUserFormValues>
                form={userForm}
                layout="vertical"
                requiredMark={false}
                onFinish={handleUserSubmit}
              >
                {userFormMode === 'edit' && editingUser ? (
                  <Form.Item label="ID">
                    <Input value={editingUser.id} disabled readOnly />
                  </Form.Item>
                ) : null}
                <Form.Item
                  name="user_number"
                  label="User number"
                  rules={[
                    { required: true, whitespace: true, message: 'User number is required.' },
                  ]}
                >
                  <Input placeholder="21P0031" />
                </Form.Item>
                <Form.Item
                  name="name"
                  label="Name"
                  rules={[{ required: true, whitespace: true, message: 'Name is required.' }]}
                >
                  <Input placeholder="홍길동" />
                </Form.Item>
                <Form.Item
                  name="department_id"
                  label="Department"
                  rules={[{ required: true, message: 'Department is required.' }]}
                >
                  <Select
                    loading={loadingDepartmentSelectOptions}
                    options={departmentSelectOptions}
                    placeholder="부서를 선택하세요."
                    showSearch
                    filterOption={false}
                    onSearch={(value) => {
                      void loadDepartmentOptions(value, 'form');
                    }}
                  />
                </Form.Item>
                {userFormMode === 'edit' && editingUser ? (
                  <Form.Item label="Use">
                    <Space direction="vertical" size={10}>
                      <UseYnTag value={editingUser.use_yn} />
                      <div
                        style={{
                          display: 'grid',
                          gap: 12,
                          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
                          maxWidth: '100%',
                          width: 260,
                        }}
                      >
                        <ConfirmActionButton
                          disabled={userSaving || editingUser.use_yn === 'Y'}
                          style={{ boxShadow: 'none' }}
                          type="primary"
                          title="Activate user?"
                          okText="Activate"
                          content={`${editingUser.user_number} ${editingUser.name} 사용자를 활성화합니다.`}
                          onConfirm={() => handleOrganizationUserUseYnChange('Y')}
                        >
                          활성화
                        </ConfirmActionButton>
                        <ConfirmActionButton
                          danger
                          disabled={userSaving || editingUser.use_yn === 'N'}
                          style={{ boxShadow: 'none' }}
                          title="Deactivate user?"
                          okText="Deactivate"
                          content={`${editingUser.user_number} ${editingUser.name} 사용자를 비활성화합니다.`}
                          onConfirm={() => handleOrganizationUserUseYnChange('N')}
                        >
                          비활성화
                        </ConfirmActionButton>
                      </div>
                    </Space>
                  </Form.Item>
                ) : null}
                {renderAdminAccessSection()}
              </Form>
            </Modal>
          </Space>
        )
      ) : (
        <AdminSessionRequired />
      )}
    </AdminShell>
  );
}
