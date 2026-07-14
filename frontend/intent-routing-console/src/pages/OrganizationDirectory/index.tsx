import { useCallback, useEffect, useRef, useState } from 'react';
import { ProTable, type ActionType, type ProColumns } from '@ant-design/pro-components';
import { useModel } from '@umijs/max';
import {
  Alert,
  Button,
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
  createDepartment,
  createOrganizationUser,
  listDepartments,
  listOrganizationUsers,
  patchDepartment,
  patchOrganizationUser,
} from '@/services/adminServices';
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
  const { session } = useModel('adminSession');
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
  const [departmentFilterOptions, setDepartmentFilterOptions] = useState<DepartmentOption[]>([]);
  const [departmentSelectOptions, setDepartmentSelectOptions] = useState<DepartmentOption[]>([]);
  const [loadingDepartmentFilterOptions, setLoadingDepartmentFilterOptions] = useState(false);
  const [loadingDepartmentSelectOptions, setLoadingDepartmentSelectOptions] = useState(false);
  const departmentActionRef = useRef<ActionType>();
  const userActionRef = useRef<ActionType>();
  const departmentFilterRequestSeqRef = useRef(0);
  const departmentSelectRequestSeqRef = useRef(0);
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

  const closeDepartmentModal = () => {
    setDepartmentModalOpen(false);
    setEditingDepartment(undefined);
    departmentForm.resetFields();
  };

  const closeUserModal = () => {
    setUserModalOpen(false);
    setEditingUser(undefined);
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
